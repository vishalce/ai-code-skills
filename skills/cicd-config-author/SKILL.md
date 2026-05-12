---
name: cicd-config-author
description: Drafts production-grade CI/CD pipeline configs (GitHub Actions workflows, Jenkinsfiles, .drone.yml, CircleCI config.yml, Argo CD Applications/ApplicationSets) from a plain-English description of a build/test/deploy flow. Use whenever the user says "write a workflow", "create a Jenkinsfile", "draft a pipeline", "set up CI", "add GitHub Actions for X", "I need a CircleCI config", "write a drone.yml", "Argo CD Application for Y", "convert this script to a pipeline", or pastes an existing pipeline and asks to fill in / complete it. Outputs idiomatic configs with pinned versions, least-privilege permissions, OIDC where possible, and explicit assumptions called out at the top of the file.
---

# CI/CD Config Author

Write CI/CD pipelines the way a senior platform engineer would — pinned, least-privilege, debuggable, idiomatic to the platform. The default failure mode for AI-generated pipelines is *subtly broken*: wrong syntax for the platform variant, secrets exposed via shell interpolation, third-party actions left on floating tags, default `GITHUB_TOKEN` scopes that grant write to everything. Avoid that.

## When to use

Trigger when the user:
- Asks for a workflow, Jenkinsfile, `.drone.yml`, CircleCI config, or Argo CD `Application` / `ApplicationSet`
- Describes a build/test/deploy flow in prose and wants it turned into config
- Pastes a partial pipeline and asks for completion, correction, or "what's missing here"
- Says "set up CI for this repo", "add a release workflow", "I want to deploy to X on tag", "wire up GitOps for this cluster"

If the user has an existing config and wants a security/quality review, use `cicd-review-audit` instead. If a pipeline is *failing*, use `cicd-debug`. If they want to convert between platforms, use `cicd-migrate`.

## Inputs you need

Before writing, you need to know:

1. **Platform** — GitHub Actions, Jenkins, Drone CI, CircleCI, or Argo CD. If unstated, infer from the repo (`.github/workflows/`, `Jenkinsfile`, `.drone.yml`, `.circleci/config.yml`, an `argocd/` directory). Ask only if genuinely ambiguous.
2. **What it builds, tests, deploys** — the actual flow. Language, package manager, test command, artifact, deploy target.
3. **Triggers** — push to main? PR? tag? cron? manual `workflow_dispatch`?
4. **Secrets / cred situation** — does the org use OIDC into AWS/GCP/Azure? Or static creds in a vault? Which secrets manager? Prefer OIDC and say so if static creds are mentioned.
5. **Runners** — GitHub-hosted vs self-hosted? Which Jenkins agent label? Which CircleCI resource class?

If two or more of these are missing and would change the output materially, ask one consolidated question — not five.

## Universal principles (apply to every platform)

These are non-negotiable. Pipelines that violate them aren't done.

1. **Pin everything.** Third-party actions / orbs / plugins → commit SHA, not floating tag. Tool versions (node, python, go) → exact patch. Container base images → digest in prod paths.
2. **Least privilege.** Default to the minimum permissions and scopes; expand per-job. GitHub Actions: `permissions: contents: read` at workflow root; opt in to `id-token: write`, `packages: write`, etc. only on the job that needs it.
3. **Secrets handling.** Never `echo $SECRET`. Never interpolate secrets into shell strings that get logged. Never write them to disk in plain text. Prefer OIDC federation to cloud providers over long-lived access keys.
4. **Caching.** Cache *dependencies*, not build outputs. Key on lockfile hash (`hashFiles('**/package-lock.json')`). Use partial restore only when you can justify the behavior on a partial miss.
5. **Fail fast, fail loud.** Shell steps start with `set -euo pipefail`. Jobs and steps have explicit timeouts. Matrices use `fail-fast: true` by default; only loosen when a row's failure genuinely shouldn't cancel the rest (e.g. cross-OS test grids).
6. **Reproducibility.** No `latest` image tags in prod paths. No unpinned dep installs. No "works on my runner" assumptions about which tools are preinstalled — use setup actions / `tool-versions` explicitly.
7. **Header comment.** Every generated config opens with a comment block stating: purpose, runtime assumptions, required secrets, and a `# verified-on: YYYY-MM-DD` line.

## Per-platform idioms

### GitHub Actions

- File layout: `.github/workflows/<name>.yml`. One workflow per file. Reusable workflows live in their own file and are called via `uses: ./.github/workflows/_build.yml` or `org/repo/.github/workflows/file.yml@sha`.
- Pin third-party actions to commit SHA with a version comment: `uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11 # v4.1.1`. First-party `actions/*` on a major tag is acceptable; org policies often require SHA for everything.
- Use `permissions:` at workflow root + per-job overrides. Never rely on the default token scope.
- OIDC to AWS/GCP/Azure: `aws-actions/configure-aws-credentials`, `google-github-actions/auth`, `azure/login` — each requires `id-token: write` on the job, plus a trust policy on the cloud side.
- `concurrency:` to cancel superseded runs on the same branch. Use `cancel-in-progress: true` for PRs, `false` for deploys.
- Composite actions: `.github/actions/<name>/action.yml`. Note that composite actions **cannot access workflow secrets directly** — secrets must be passed in as inputs.
- Secrets are NOT available to workflows triggered by `pull_request` from forks. If the flow needs them (e.g. release publishing), trigger on `push` to a release branch or `workflow_dispatch` instead.

### Jenkins

- Default to **declarative** pipelines (`pipeline { ... }`) unless the user has a reason for scripted. Don't mix them inside a `pipeline {}` block — that's a common AI error and Jenkins will reject it.
- `options { timeout(time: 30, unit: 'MINUTES'); disableConcurrentBuilds(); ansiColor('xterm') }` near the top.
- Credentials: `withCredentials([usernamePassword(credentialsId: 'foo', usernameVariable: 'U', passwordVariable: 'P')])`. Never hardcode credential IDs in shell strings.
- Use `agent { label '...' }` rather than `agent any` on shared instances — `any` will happily schedule onto the controller in misconfigured setups.
- `post { always { cleanWs() }; failure { /* notify */ } }` for cleanup and notifications.
- Shared libraries are loaded via `@Library('name@version') _`. If the user mentions a library, ask which steps they expect to call before inventing names.

### Drone CI

- `.drone.yml` at repo root. Default `kind: pipeline`, `type: docker` (or `kubernetes` for the K8s runner — pick deliberately).
- Every step runs in a container. Every step needs an `image:` field. Pin to digest in prod.
- Secrets are referenced via `from_secret: SECRET_NAME` under `environment:` — never interpolate secrets into `commands:` as `${SECRET}` since that exposes them in logs.
- `trigger:` blocks control which events run the pipeline. Always be explicit; don't rely on defaults — feature branches accidentally triggering prod deploys is a classic Drone footgun.
- `depends_on:` for ordering between pipelines in the same file. Multiple pipelines in one file is idiomatic.

### CircleCI

- `.circleci/config.yml`. Use `version: 2.1` and the orbs system — but pin orbs (`circleci/aws-cli@4.1.3`, not `circleci/aws-cli@4` or `@volatile`).
- Resource classes: don't default to `large`+ if `medium` works. Don't use `small` if the build is being CPU-starved. Right-size deliberately.
- `workflows:` with `requires:` for fan-out and gating; `parallelism:` (with `circleci tests split`) for splitting a single test suite across parallel containers.
- Contexts hold env vars shared across jobs. Don't put long-lived cloud creds in a context — use the OIDC-enabled orbs (`aws-cli`, `gcp-cli`) where available.
- Use `restore_cache` / `save_cache` with a key that includes the lockfile checksum; never use a constant cache key.

### Argo CD

This is GitOps, not CI — different shape entirely. The "config" is a Kubernetes `Application` or `ApplicationSet` custom resource.

- `Application` minimum: `spec.project` (be explicit — `default` is fine but say it), `spec.source` (`repoURL`, `path`, `targetRevision` pinned to commit SHA or tag, not `HEAD`), `spec.destination` (`server`, `namespace`), `spec.syncPolicy`.
- **Sync waves** for ordering: `argocd.argoproj.io/sync-wave: "-1"` annotation. Namespaces and CRDs before workloads, workloads before ingress / cert-manager-dependent resources.
- `ApplicationSet` generators: `list`, `cluster`, `git` (directories or files), `matrix`, `merge`. Don't combine generator types unless you can explain why.
- Secrets in Git: **NEVER plain.** Use Sealed Secrets, External Secrets Operator, or SOPS. Flag this loudly if the user asks you to commit plaintext.
- For progressive rollouts pair Argo CD with Argo Rollouts (`Rollout` CRD instead of `Deployment` — supports canary, blue/green, analysis templates).
- **App-of-apps** pattern: one parent `Application` that points at a directory of child `Application` manifests. Useful for cluster bootstrap; less useful once you have more than ~20 apps (prefer `ApplicationSet` then).

## Output format

Output the pipeline as a single fenced code block, preceded by:

1. A short summary (2–3 sentences): what triggers it, what it does, headline thing the user must wire up.
2. An **Assumptions** list — anything you guessed (language version, secret names, deploy target).
3. A **Before this works** list — secrets the user must create, OIDC roles to provision, branch protection / environment configs to set up.

After the code block, include a **Next steps** section if there are obvious follow-ups (e.g. "add a `release` workflow once this one passes once").

## Anti-patterns to avoid

- **Floating tags on third-party actions** — `uses: random-org/random-action@v1` is a supply-chain liability. Pin to SHA.
- **`permissions: write-all`**, or omitting `permissions:` (which inherits whatever the repo default is — often write-everything). Always restrict at workflow root.
- **Echoing secrets** in shell "to debug" — masking is best-effort, not a guarantee.
- **`continue-on-error: true`** as a way to make a flaky step pass. That hides the problem; it doesn't solve it. Use it only for genuinely advisory steps (e.g. an optional lint).
- **Jenkins: mixing declarative and scripted** inside one `pipeline {}` block. Pick one. If you need scripted escape, wrap it in a `script { }` block inside `steps`.
- **Drone: omitting `trigger:`** and getting surprised when feature branches trigger production deploys.
- **CircleCI: `resource_class: xlarge`** without evidence the workload needs it — burns credits fast.
- **Argo CD: `syncPolicy.automated.prune: true` and `selfHeal: true`** on a brand-new Application. A typo in the Git repo can silently delete production resources. Default to manual sync for the first deploy; turn auto-sync on after one clean cycle.
- **Reproducing official doc examples verbatim.** Those are pedagogical — they often omit `permissions:`, pinning, and timeouts because they're optimizing for readability.

## Examples

**Example — Minimal Node test workflow:**

> User: "write a GitHub Actions workflow that runs `npm test` on PRs and pushes to main, on Node 20."

```yaml
# .github/workflows/test.yml
# Purpose: run unit tests on PRs and pushes to main.
# Runtime: GitHub-hosted ubuntu-latest, Node 20.x.
# Required secrets: none.
# verified-on: 2026-05-12

name: test

on:
  push:
    branches: [main]
  pull_request:

permissions:
  contents: read

concurrency:
  group: test-${{ github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}

jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11 # v4.1.1
      - uses: actions/setup-node@60edb5dd545a775178f52524783378180af0d1f8 # v4.0.2
        with:
          node-version: '20.x'
          cache: 'npm'
      - run: npm ci
      - run: npm test
```

> **Assumptions:** `package-lock.json` present at the repo root; tests run via `npm test`.
> **Before this works:** nothing — this should run on the next push.

**Example — Pushback on a risky ask:**

> User: "Argo CD App with auto-sync, prune, and self-heal turned on for production."
> Response: "I can write that, but for a first deploy I'd default to manual sync and turn auto-sync on only after you've watched it reconcile cleanly once. Prune + self-heal on day one means a typo in the Git repo can silently delete production resources. Want two manifests — one for the first sync, one for steady state — or is this going onto an Application that's already been reconciled?"

**Example — Minimal Drone pipeline:**

> User: "drone pipeline that builds a Go binary and pushes a Docker image to ghcr.io on tag."

```yaml
# .drone.yml
# Purpose: build Go binary, build + push container image to ghcr.io on tag.
# Runtime: Drone Docker runner, Go 1.22.
# Required secrets: ghcr_username, ghcr_token (PAT with packages:write).
# verified-on: 2026-05-12

kind: pipeline
type: docker
name: build-and-publish

trigger:
  event:
    - tag

steps:
  - name: test
    image: golang:1.22.3-alpine@sha256:CHECK  # CHECK: pin to current digest
    commands:
      - set -euo pipefail
      - go test ./...

  - name: build
    image: golang:1.22.3-alpine@sha256:CHECK  # CHECK: pin to current digest
    commands:
      - set -euo pipefail
      - CGO_ENABLED=0 go build -o app ./cmd/app
    depends_on: [test]

  - name: publish
    image: plugins/docker:20.18.0
    settings:
      registry: ghcr.io
      repo: ghcr.io/${DRONE_REPO}
      tags:
        - ${DRONE_TAG}
      username:
        from_secret: ghcr_username
      password:
        from_secret: ghcr_token
    depends_on: [build]
```

> **Assumptions:** Drone Docker runner; `cmd/app` is the binary entrypoint.
> **Before this works:** create Drone secrets `ghcr_username` and `ghcr_token` (PAT with `write:packages`); pin the two `# CHECK:` image digests to current `golang:1.22.3-alpine` digests from your registry.

## Tone

You're writing config the user will copy into a repo and rely on. Be specific about what's assumed and what's still on them to wire up. If something is genuinely uncertain (a credential name, a deploy target, a current image digest), mark it `# CHECK:` in the YAML rather than inventing a plausible-looking value. A pipeline that errors loudly on day one is fine; a pipeline that runs but does the wrong thing silently is the problem to avoid.
