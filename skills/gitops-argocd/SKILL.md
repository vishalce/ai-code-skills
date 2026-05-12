---
name: gitops-argocd
description: Designs and reviews Argo CD GitOps setups — App-of-apps and ApplicationSet patterns, sync waves, progressive rollouts with Argo Rollouts, drift detection, and secret management (Sealed Secrets / External Secrets / SOPS). Use whenever the user mentions "Argo CD", "ArgoCD", "GitOps", "App of apps", "ApplicationSet", "sync wave", "Argo Rollouts", "canary deploy via Argo", "blue/green via Argo", "Argo App is OutOfSync", "drift detection", "sealed secrets", or asks how to structure their Kubernetes deploy repos. Outputs concrete manifests, repo-layout guidance, and the specific patterns that hold up in production vs. the ones that collapse at scale.
---

# Argo CD GitOps

GitOps with Argo CD looks deceptively simple at the small scale — one repo, a few `Application` manifests, auto-sync on. It stops scaling at three places: managing many apps across many clusters, secrets, and progressive rollouts. This skill is opinionated about how to set up Argo so those three things don't bite you in month six.

## When to use

Trigger when the user:
- Names Argo CD, ArgoCD, App-of-apps, ApplicationSet, sync waves, Argo Rollouts
- Talks about "GitOps repos", "deploy repos", "config repos", "the cluster's source of truth"
- Asks about Sealed Secrets, External Secrets Operator, SOPS, or how to put secrets in Git safely
- Has an Argo Application stuck `OutOfSync`, `Degraded`, `ComparisonError`, `SharedResourceWarning`, or a sync that won't finish
- Asks "how should I structure my Kubernetes manifests for Argo" / "should I use Kustomize or Helm" / "is App-of-apps right for us"

If the user has a CI pipeline (not a GitOps controller) and wants to deploy *from* CI, this is the wrong skill — they likely want `cicd-config-author`. Argo CD is **not** a CI tool; it's a pull-based reconciler.

## Inputs you need

1. **Cluster scope.** One cluster or many? Multi-tenant or single-tenant? This determines whether you want `ApplicationSet` with a cluster generator from day one or can start simpler.
2. **App count and growth.** Starting with 5 apps that won't grow much? Plain `Application` manifests are fine. Starting with 50+, or expecting growth? Plan for `ApplicationSet` and cluster bootstrap.
3. **Tooling.** Kustomize, Helm, plain YAML, Jsonnet? Argo supports them all, but the recommendations differ.
4. **Secret strategy.** Are secrets currently in a separate vault (Vault, AWS Secrets Manager)? Then External Secrets Operator. Are they in Git encrypted? Then Sealed Secrets or SOPS. If "not figured out yet", flag it as the most important thing to decide.
5. **Rollout requirements.** Plain `Deployment` rollouts with `RollingUpdate` strategy, or do you need canary / blue-green / progressive traffic shifting? The latter wants Argo Rollouts.

## Repo layout — pick one and stick with it

The repo structure decides everything else. The two canonical layouts:

### A) Monorepo for manifests, one repo for app code

```
infra-config/                          # Argo's source of truth
├── apps/                              # One subdirectory per app
│   ├── frontend/
│   │   ├── base/                      # Kustomize base
│   │   └── overlays/{dev,stage,prod}/ # Per-env overlays
│   └── api/
│       └── ...
├── argocd/                            # Argo's own Application manifests
│   ├── apps-dev.yaml                  # ApplicationSet for dev
│   ├── apps-stage.yaml
│   └── apps-prod.yaml
└── bootstrap/                         # App-of-apps root
    └── root.yaml
```

Pros: one PR can change app+infra together (if you allow that); easier to grep. Cons: blast radius of a bad change is wider.

### B) One repo per app, one central GitOps repo for top-level apps

Each app has its own repo with `manifests/` or `deploy/`. A central `gitops/` repo holds `Application` manifests that point at each app repo's `manifests/` path.

Pros: smaller blast radius; each team owns their repo. Cons: cross-cutting changes touch many repos; harder to do "show me all the resources in prod" without tooling.

**Pick based on team shape**, not aesthetic preference. Two-pizza team running ~10 services → layout A. Multi-team org with strong ownership boundaries → layout B.

## App-of-apps pattern

One parent `Application` whose source is a directory of child `Application` manifests. The parent syncs the children; the children sync the actual workloads.

**When it's right:** cluster bootstrap. One Application installs everything-else-Argo-manages, including the operators it depends on.

**When it stops being right:** more than ~20 child apps, or you want per-environment fan-out. At that point switch to `ApplicationSet`. App-of-apps is fine for bootstrap; `ApplicationSet` is better for managing app fleets.

**A working minimal App-of-apps root:**

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: root
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  source:
    repoURL: https://github.com/example/infra-config.git
    targetRevision: a1b2c3d4e5f6  # pin to commit SHA, not HEAD
    path: argocd/
  destination:
    server: https://kubernetes.default.svc
    namespace: argocd
  syncPolicy:
    automated:
      prune: false       # manual prune on the root until you trust it
      selfHeal: false
```

## ApplicationSet generators

`ApplicationSet` generates many `Application`s from a template. Generators:

- **List** — explicit list of values. Smallest-scale; use for "deploy this app to these named environments".
- **Cluster** — generates an Application per cluster registered with Argo. The right choice for "deploy app X to every prod cluster".
- **Git** (directories or files) — generates an Application per directory matching a glob, or per file matching a glob. The right choice for "every directory under `apps/` becomes an Application".
- **Matrix** — Cartesian product of two generators. "Every app × every cluster". Power tool, easy to misuse — verify the generated count before applying.
- **Merge** — overlays one generator on another for shared overrides.

**Common ApplicationSet anti-patterns:**
- `Matrix` of Git directories × clusters without a `selector` to filter — produces hundreds of Applications.
- `goTemplate: true` not enabled when using complex templating — gets you mysterious empty-string substitutions.
- `Application` template missing `spec.project` — falls through to `default`, which permits any source/destination.

## Sync waves and resource ordering

Annotate resources with `argocd.argoproj.io/sync-wave: "<int>"` to control order. Lower numbers sync first; default is `0`.

Typical waves:
- **-2**: Namespaces, CRDs (anything that must exist before workloads can reference them).
- **-1**: Operators, controllers, admission webhooks.
- **0**: Application workloads, ConfigMaps, Secrets, Services.
- **1**: Ingresses, Routes (depend on services and cert-manager).
- **2**: Network policies, scaling configs (depend on workloads being healthy first).

Sync waves are *per Application*, not global. Apps sync independently from each other — for cross-app ordering, use App-of-apps with sync waves on the child Applications.

**Sync wave gotcha:** sync waves only fire when there are changes to apply. If wave `-1` resources already exist and don't change, the Application proceeds directly to wave 0. Don't use sync waves as a substitute for resource readiness checks.

## Progressive rollouts with Argo Rollouts

Argo Rollouts is a separate controller that replaces `Deployment` with a `Rollout` resource supporting canary, blue/green, and analysis-driven promotion.

**When to use:**
- You need traffic-shifted canary (5% → 25% → 50% → 100% over time).
- You want automatic promotion gated by metrics (Prometheus, Datadog).
- Standard `RollingUpdate` strategy doesn't give you enough control or observability.

**When `Deployment` is fine:**
- Your service is stateless, fast-restarting, and tolerant of brief mixed-version traffic.
- You don't have a metrics provider Argo Rollouts can integrate with.
- Adding another CRD for two-replica services is overkill.

**Minimal canary `Rollout`:**

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: api
spec:
  replicas: 5
  selector:
    matchLabels: { app: api }
  template:
    metadata: { labels: { app: api } }
    spec:
      containers:
        - name: api
          image: ghcr.io/example/api:v1.4.2
          ports: [{ containerPort: 8080 }]
  strategy:
    canary:
      steps:
        - setWeight: 20
        - pause: { duration: 5m }
        - setWeight: 50
        - pause: { duration: 5m }
        - setWeight: 100
```

For metric-gated promotion add an `AnalysisTemplate` and reference it from the step. Don't skip the analysis if you have a metrics provider — manual pauses get long-deferred by humans.

## Secrets — never plaintext

The non-negotiable: encrypted Kubernetes `Secret` manifests do NOT belong in Git. The three legitimate options:

### Sealed Secrets
- Bitnami's controller. You encrypt with the cluster's public key; the controller decrypts in-cluster.
- Best for: small-to-medium setups with a single secrets workflow.
- Limitation: secrets are bound to a specific cluster's private key. Disaster recovery requires backing up the key.

### External Secrets Operator
- Reads from external vaults (AWS Secrets Manager, GCP Secret Manager, Vault, Azure Key Vault) and creates Kubernetes Secrets in-cluster.
- Best for: orgs already using a vault; multi-cluster setups.
- The Git repo holds `ExternalSecret` *references* (not secret values), pointing at vault paths.

### SOPS (with KSOPS or Helm-secrets plugin)
- Encrypt secrets in Git with age/PGP/KMS keys; decrypt at apply time via a Kustomize/Helm plugin.
- Best for: smaller teams comfortable with key management; works well with multiple clusters.
- Requires a SOPS plugin in the Argo CD controller, which is custom-config territory.

**Don't mix all three.** Pick one and standardize.

## Drift detection and self-heal

- `syncPolicy.automated.selfHeal: true`: Argo will revert any change in the cluster that diverges from Git. Good for steady-state production where Git is truly the source of truth.
- `selfHeal: false`: Argo will detect drift and mark the App `OutOfSync`, but won't act. Good for development clusters where engineers manually patch things.
- `prune: true`: Argo will delete resources removed from Git. **Critical risk on first sync**; safe afterward.

**The safe rollout pattern:**
1. First deploy: `automated: null` (manual sync), `prune: false`, `selfHeal: false`. Manually sync, watch reconcile.
2. After a clean cycle: enable `automated.prune: false, selfHeal: false`. Auto-sync on changes; no destructive ops.
3. After confidence: enable `prune: true, selfHeal: true`.

## Common failure modes

| Symptom | Likely cause | Diagnosis |
|---|---|---|
| `ComparisonError` | Manifest doesn't render — missing CRD, invalid YAML, Helm template error | Check Application `status.conditions`; run the Kustomize/Helm command locally. |
| Stuck `OutOfSync`, never converges | A controller is rewriting a field Argo manages | Use `ignoreDifferences` on the specific field, narrowest possible path. |
| `SharedResourceWarning` | Two Applications claim the same resource | Decide which app owns it; remove from the other. |
| Sync succeeded, app `Degraded` | Resource applied but workload is unhealthy | Look at pod logs, not Argo. |
| Sync wave skipped | Resources in that wave didn't change | Expected behavior; don't fight it. |
| `cluster-scoped resource not allowed` | Application project restricts cluster-scoped resources | Adjust the project's `clusterResourceWhitelist`. |

## Output format

When designing a setup:

```
## Recommended layout
[Which monorepo/multi-repo, which generators, which secrets approach. One sentence each.]

## Manifests
[Concrete `Application` / `ApplicationSet` / `Rollout` manifests in fenced blocks. Header comment with purpose + verified-on.]

## Bootstrap sequence
[Step-by-step: which manifest to apply first, what to wait for, how to verify.]

## Rollout plan (auto-sync)
[The 3-stage safe rollout: manual sync → auto-sync no-prune → auto-sync with prune+selfHeal.]

## Things I'm unsure about
[Specifics that need confirmation: cluster URLs, repo paths, secret names, project names. Marked `# CHECK:` in the YAML.]
```

When debugging an Argo issue, use the failure-mode table above and the `cicd-debug` skill's RCA output format.

## Anti-patterns to avoid

- **`spec.project: default` on a prod app** without explicit acknowledgment. `default` permits any source/destination — restrictive projects are how you scope blast radius.
- **`targetRevision: HEAD`** or a branch name on a prod app. Pin to commit SHA or signed tag. Branches are mutable; HEAD is whatever someone last pushed.
- **`syncPolicy.automated.prune: true, selfHeal: true` from day one.** Typos in Git can silently delete production. Use the staged rollout.
- **Plain `Secret` manifests in Git.** Always. No exceptions.
- **Using App-of-apps for app fleets.** It works up to a point and then becomes a maintenance burden — `ApplicationSet` is the right tool past ~20 apps.
- **`ignoreDifferences` paths that are too broad.** Ignoring `/spec` masks all drift. Ignore the specific field a controller writes (e.g., `/spec/replicas` when HPA is active).
- **Mixing secret-management approaches.** Sealed Secrets *and* External Secrets *and* SOPS in one repo creates ambiguity about which manifest to trust.
- **Cluster generators that match production clusters when they shouldn't.** ApplicationSet cluster generators use label selectors — be explicit about `matchLabels`, never rely on "every cluster". A new cluster gets every app by accident.

## Examples

**Example — Bootstrap App-of-apps for a 4-app cluster:**

> User: "I have 4 services, one cluster, want a clean Argo setup."
>
> Recommended: layout A (monorepo for manifests, App-of-apps for bootstrap). Plain Applications (not ApplicationSet) — 4 apps doesn't warrant the templating overhead.
>
> Bootstrap sequence:
> 1. Apply `bootstrap/root.yaml` (the App-of-apps root) by hand once.
> 2. Argo discovers `argocd/*.yaml` and creates one Application per file.
> 3. Each Application syncs its workload from `apps/<name>/overlays/prod/`.
> 4. Watch the first sync. Once clean, enable `automated: { prune: false, selfHeal: false }` on each.
>
> Secrets: 4 apps is small enough that Sealed Secrets is the simplest answer. Install the controller via an Argo Application in the `bootstrap` directory at sync wave `-1`.

**Example — Pushback on premature ApplicationSet:**

> User: "set up ApplicationSet with a matrix generator for our 6 apps across 2 clusters."
> Response: "We can, but for 12 generated Applications I'd start with 12 plain `Application` manifests instead — easier to read, easier to grep, easier to deviate from when one app needs a quirk the others don't. ApplicationSet pays off past ~20 apps or when the cluster set is genuinely dynamic. Do you expect this to grow soon, or is 12 the steady state? If steady state, I'd recommend plain manifests."

## Tone

GitOps is a discipline as much as a tool. You're helping the user set up something they'll be living with — favor patterns that hold up under scale and under partial knowledge from future engineers. When recommending Argo features, also say when *not* to use them: the worst Argo setups come from over-applying every feature on day one.
