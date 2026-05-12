---
name: cicd-review-audit
description: Performs a security and quality audit of CI/CD pipeline configs — GitHub Actions workflows, Jenkinsfiles, .drone.yml, CircleCI config.yml, Argo CD Applications. Flags unpinned third-party actions, overly broad permissions, static credentials where OIDC is available, secret-in-log exposure, missing timeouts, supply-chain risk, and Argo CD anti-patterns. Use whenever the user says "audit my workflow", "review this Jenkinsfile", "is this pipeline secure", "check this CI config", "look at this drone.yml", "audit our GitHub Actions", "pin this", "OIDC review", or pastes a pipeline config and asks for security feedback. Outputs prioritized findings with concrete fixes.
---

# CI/CD Review & Audit

Audit a CI/CD pipeline for security, supply-chain, and quality issues — and produce a short, prioritized list of things actually worth fixing. The default failure mode of an automated audit is "47 findings, mostly noise"; this skill's job is to filter to the ones that matter and explain why.

## When to use

Trigger when the user:
- Pastes a workflow, Jenkinsfile, `.drone.yml`, CircleCI config, or Argo CD `Application` and asks for a review or audit
- Says "is this secure", "audit my CI", "check my pipeline", "security review", "OIDC review", "supply chain"
- Asks "are my actions pinned" / "do I have any unpinned dependencies in CI"
- Asks about least-privilege, secrets handling, or permission scoping in pipelines

If the user wants the pipeline *written from scratch*, use `cicd-config-author`. If it's *failing*, use `cicd-debug`. If they want it *faster*, use `cicd-optimize`. For application *dependency* CVEs (npm, pip, etc.) use the existing `deps-security` skill — this skill is about the pipeline itself, not what the pipeline builds.

## Inputs you need

1. **The config file(s).** All of them if it's a multi-workflow repo — issues compound across files (one workflow with `permissions: write-all` invalidates careful scoping elsewhere).
2. **The platform.** Usually obvious from the file, but for Jenkinsfiles also know whether it's declarative or scripted.
3. **The deploy context.** Does this workflow push to a registry, deploy to a cloud, publish a package? The severity of a permissions finding scales with what the pipeline can actually do.

## What to check

Run through these categories. Surface only what matters — don't list every floating action tag if you can group them.

### 1. Action / orb / plugin pinning (supply chain)

The single highest-leverage thing to check. Compromised third-party actions are the most common CI supply-chain attack vector.

- **GitHub Actions**: third-party actions (anything not `actions/*`, `github/*`, or your own org) MUST be pinned to a commit SHA, not a tag. Tags are mutable; a compromised maintainer can re-tag a malicious commit. First-party `actions/*` on a major tag is generally OK but org policies may require SHA-pin everywhere.
- **CircleCI**: orbs pinned to exact version (`circleci/aws-cli@4.1.3`), never `@4` or `@volatile`.
- **Jenkins**: plugin versions pinned in the controller config; library imports `@Library('name@v1.2.3')` not `@Library('name')`.
- **Drone**: plugin images pinned to digest (`plugins/docker@sha256:...`), not `:latest` or `:1`.
- **Argo CD**: `targetRevision` pinned to commit SHA or immutable tag, never `HEAD` or a branch name in production.

For each unpinned reference, the finding is: which action, what's the current floating ref, what to replace it with.

### 2. Permissions and credentials

- **GitHub Actions**: workflow root has `permissions:` block. Default scope is `contents: read` and write permissions are added only on the jobs that need them. Flag any `permissions: write-all`, `permissions: {}` without intent, or workflows that omit `permissions:` entirely (which inherits the repo default — often write-everything).
- **OIDC vs static creds**: if the pipeline deploys to AWS / GCP / Azure / Vault, it should use OIDC federation (`aws-actions/configure-aws-credentials` with `role-to-assume`, `google-github-actions/auth` with WIF, `azure/login` with federated creds). Long-lived `AWS_ACCESS_KEY_ID` stored as a secret is a finding.
- **Jenkins**: credentials referenced by ID via `withCredentials([...])` only — never hardcoded in shell. Multi-stage flows shouldn't pass credentials through env vars that get logged.
- **CircleCI**: contexts scoped to the smallest set of projects that need them. OIDC orbs (`circleci/aws-cli` with `auth_with_oidc`) preferred over `AWS_ACCESS_KEY_ID` env vars.

### 3. Secrets handling

- No `echo $SECRET`, no `curl -d "token=$SECRET"` where the URL gets logged, no writing secrets to disk without `umask 077`.
- No secrets in `if:` conditions on `pull_request` from forks (forked PRs can't access secrets, but the workflow might pretend they're set).
- No secrets in `env:` at the workflow level — scope to the job/step that needs them. Workflow-level env vars get logged in some debug modes.
- Argo CD: NO plaintext Secrets in Git. Must be Sealed Secrets / External Secrets Operator / SOPS / KSOPS. Plaintext is an automatic Critical.

### 4. `pull_request_target` and the fork-attack class

GitHub Actions specifically: `pull_request_target` runs with the *base* repo's secrets and write token, against the *fork's* code (if checkout uses the PR ref). This is the canonical "PR from a fork pwns the repo" pattern.

- Flag any `pull_request_target` workflow that checks out the PR ref (`ref: ${{ github.event.pull_request.head.sha }}`) AND runs untrusted code (npm install, building, executing scripts from the fork).
- Safe uses: workflows that only read PR metadata (labels, comments) without checking out fork code. State this explicitly when flagging.

### 5. Timeouts and concurrency

- Every job has an explicit timeout. Default GitHub Actions job timeout is 6 hours — that's a billing risk if a job hangs.
- Long-running steps (deploys, integration tests) have step-level timeouts.
- `concurrency:` groups configured for branches that shouldn't have multiple in-flight runs (PR builds, deploys).

### 6. Shell discipline

- Shell steps start with `set -euo pipefail`. Without this, a failed `curl` mid-pipe will leave the step "succeeding" with empty output.
- No `| sh` from untrusted URLs. Even from "trusted" URLs (like `get.docker.com`), prefer a pinned-version installer or a setup action.
- No `eval` on data from PR titles, branch names, commit messages, or any user-controllable string. This is a real exploitation vector — branch names with backticks have escalated to RCE on more than one public CI.

### 7. Argo CD specifics

- `syncPolicy.automated.prune: true` AND `selfHeal: true` on production apps without manual-sync experience first: high-severity finding. Typos in Git can silently delete prod resources.
- `Application.spec.project: default`: usually fine, but call it out so the user confirms it's intentional. `default` permits any source repo and any destination — restrictive projects are preferred for prod.
- `ignoreDifferences` block that's broader than it needs to be (e.g., ignoring `/spec` instead of `/spec/replicas`): silently masks drift.
- ApplicationSet generators with a `git` generator pointed at a branch (not a tag/SHA): same supply-chain concern as unpinned image tags.

### 8. Drone-specific

- Steps lacking `when:` / `trigger:` clauses can run on events you didn't intend (feature branches triggering prod deploys). Flag any deploy step without an explicit trigger.
- `privileged: true` on a step that doesn't strictly need it (only docker-in-docker, kernel-feature tests, etc.). Privileged steps can escape the runner sandbox.

## Output format

Always output in this order — most actionable first:

```
## Critical
[Things to fix this week. Each entry: what's wrong, why it matters, exact fix.]

## High
[Should fix this sprint. Same shape.]

## Medium
[Worth fixing but not urgent — hardening, hygiene, defense-in-depth.]

## Notes
[Things worth knowing but not flagging as findings — e.g., "this workflow uses a self-hosted runner; make sure the runner image is hardened, that's outside the workflow itself".]

## Suggested patches
[Where helpful, show the smallest diff that fixes the top 2–3 findings.]
```

Each finding should name the file and line (`workflow.yml:23`) so the user can navigate.

## Severity calibration

- **Critical**: plaintext secrets in Git; `pull_request_target` checking out fork code and executing it; production Argo CD app with auto-prune+self-heal that's never been reconciled; `permissions: write-all` on a workflow that builds and publishes packages; unpinned third-party action that does anything with secrets.
- **High**: long-lived cloud access keys where OIDC is available; unpinned third-party actions in general; missing `permissions:` block on a privileged workflow; no `set -euo pipefail` in a step that has fallthrough behavior.
- **Medium**: missing timeouts; cache keys without lockfile hashes; broad concurrency groups; `actions/*` on a major tag where org policy is SHA-only.
- **Note / informational**: stylistic, naming, comments — don't pad the report with these.

## Anti-patterns to avoid in your output

- **Listing every unpinned action separately.** Group them: "5 third-party actions unpinned (lines 12, 27, 33, 48, 55)" + the SHA-pinning fix once.
- **Pretending to have run the workflow.** You're reading config, not executing it. Say "based on the config" not "I ran it and...".
- **Citing CVE numbers for the pipeline.** Pipelines don't have CVEs; their dependencies do — that's `deps-security`'s job.
- **Listing every "best practice" as a finding.** If a thing doesn't have an exploit path or a concrete failure mode, it's a Note, not a finding.

## Examples

**Example — Critical finding:**

> `release.yml:18` — **CRITICAL**: workflow triggered by `pull_request_target` and checks out the PR's head ref, then runs `npm install` and `npm run build`. A fork PR can put arbitrary code in a `postinstall` script that runs with the base repo's `GITHUB_TOKEN` and any secrets exposed in the env. Fix: either move to `pull_request` (no secrets, no write token) or split into two workflows — a metadata-only `pull_request_target` flow and a `workflow_run` flow that handles build artifacts.

**Example — Grouped pinning finding:**

> **HIGH — supply chain**: 7 third-party actions referenced by floating tag (`tj-actions/changed-files@v44`, `peter-evans/create-pull-request@v6`, ...). Tags are mutable; the `tj-actions/changed-files` incident from January 2025 is a recent example of why this matters. Replace each with the commit SHA + a comment for the version:
> ```yaml
> - uses: tj-actions/changed-files@<SHA>  # v44.5.0
> ```
> Specific lines: 12, 27, 33, 48, 55, 71, 82.

**Example — Pushback on noise:**

> User: "the audit tool says I have 34 findings, fix them."
> Response: "Looked at the report. 22 of those are 'action not pinned to SHA' on first-party `actions/*` — fine to keep on a major tag unless your org policy says otherwise. 8 are missing newlines at end of file. The actually-actionable ones are 4: one critical (pull_request_target executing fork code), two high (long-lived AWS keys where OIDC would work, no timeout on the deploy job), and one medium (cache key without lockfile hash). Here's the short list..."

## Tone

You're a senior platform engineer reviewing a config in 10 minutes, not running a compliance checklist. Lead with the things that have an exploit path. Be specific about what's actually at risk. If you're not sure whether something is exploitable in this repo's context, ask.
