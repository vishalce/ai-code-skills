---
description: Security audit of CI/CD pipeline configs — OIDC, secrets, permissions, supply-chain, unpinned actions. Distinct from /audit (which is for application dependencies).
argument-hint: "[optional: path to pipeline file or 'all' to scan all workflows]"
---

Run a security and supply-chain audit on CI/CD pipeline configuration.

**Target:** `$ARGUMENTS` — a path to a pipeline file, or `all` (default) to scan everything: `.github/workflows/*.yml`, `Jenkinsfile`, `.drone.yml`, `.circleci/config.yml`, `argocd/**/*.yaml`.

This is the *pipeline* audit. For *application* dependency CVEs (`npm audit`, `pip audit`, etc.) use `/audit`.

Steps:
1. Read every target file.
2. Run through the audit checklist in priority order:
   - **Critical**: plaintext Kubernetes Secrets in Git (Argo CD); `pull_request_target` checking out fork code AND executing it (GHA); production Argo CD app with `automated.prune+selfHeal` that's never reconciled; `permissions: write-all` on workflows that build/publish; unpinned third-party action that touches secrets.
   - **High**: long-lived cloud access keys where OIDC is available; unpinned third-party actions/orbs/plugins generally; missing `permissions:` block on privileged workflows; no `set -euo pipefail`; secrets in workflow-level `env:`.
   - **Medium**: missing timeouts (job + step); cache keys without lockfile hashes; broad concurrency groups; `actions/*` on a major tag where org policy is SHA-only; `Application.spec.project: default` without intent.
   - **Note**: stylistic, naming, comments — don't pad the report.
3. Group findings — don't list every unpinned action separately. "7 third-party actions unpinned (lines 12, 27, 33, 48, 55, 71, 82)" beats 7 separate findings.
4. Cite file + line for every finding so the user can navigate.

Output:

```
## Critical
[file:line — what's wrong, exploit path / failure mode, exact fix.]

## High
[same shape]

## Medium
[hardening + hygiene]

## Notes
[informational only, not findings]

## Suggested patches
[smallest diff for the top 2–3 items where concrete]
```

Severity calibration:
- A finding is **Critical** only if there's a clear exploit path or a real production-destroying failure mode.
- A finding is **High** if there's a credible security or supply-chain risk but no immediate exploit (e.g., unpinned actions that don't currently touch secrets).
- "Best practice not followed" without a failure mode is a **Note**, not a finding.

Anti-patterns to avoid:
- Pretending to have run the workflow. You're reading config — say so.
- Citing CVE numbers for the pipeline itself. Pipelines don't have CVEs; their dependencies do.
- Listing every "best practice" as a finding. Filter to what's exploitable in this repo's context.
