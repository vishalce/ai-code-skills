---
description: Review a CI/CD pipeline config (workflow, Jenkinsfile, .drone.yml, circleci config) for quality and obvious correctness issues
argument-hint: "[optional: path to pipeline file, e.g. .github/workflows/test.yml]"
---

Review a CI/CD pipeline config and produce structured, severity-tagged feedback.

**Target:** `$ARGUMENTS` (if empty, find pipeline files in the repo: `.github/workflows/*.yml`, `Jenkinsfile`, `.drone.yml`, `.circleci/config.yml`, `argocd/**/*.yaml`).

Steps:
1. Read the target file(s) end to end.
2. For each file, identify the platform from the path or content.
3. Run through the review checklist in priority order:
   - Pinning (third-party actions/orbs/plugins to SHA; tools to exact version; base images to digest)
   - Permissions and credentials (least privilege; OIDC over static creds; no secrets in workflow-level `env`)
   - Secret handling (no `echo`, no shell interpolation into logged strings, no plaintext in Argo Git)
   - Triggers (explicit; `pull_request_target` checked-out-fork-code is critical)
   - Timeouts (job + step level)
   - Shell discipline (`set -euo pipefail`; no piped curls)
   - Platform-specific footguns (Jenkins declarative/scripted mixing; Drone missing `trigger:`; CircleCI floating orbs; Argo CD auto-prune+selfHeal on new app)
4. Output:

```
## Summary
[2–3 sentences: what the pipeline does, headline concern.]

## Critical
[file:line — what's wrong, why it matters, exact fix.]

## High
[same shape]

## Medium
[hardening + hygiene]

## Notes
[informational, not findings]

## Suggested patches
[smallest diff for the top 2–3 items, when concrete]
```

Skip:
- "Best practices" with no exploit path or concrete failure mode — those are Notes at most
- Listing every unpinned action separately — group them
- Application-dependency CVEs — that's `/audit`, not this command

For application dependency audits use `/audit`. For pipeline failures (not config quality) use `/pipeline-debug`. For platform migration use `/migrate-ci`.
