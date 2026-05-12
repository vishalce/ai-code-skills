# Windsurf Rules — Code Management

These rules guide AI-assisted code work across review, refactoring, testing, docs, dependencies, and git operations. Copy this file to `.windsurfrules` at your project root.

---

## Code Review

When asked to review a diff or PR, output in this exact structure:

```
## Summary
[2–4 sentences]

## Blocking issues
[file:line — BLOCKER: issue + fix. Omit if none.]

## Suggestions
[file:line — MAJOR/MINOR: issue + fix. Omit if none.]

## Nits & style
[Only if no MAJOR/MINOR issues.]

## What's good
[1–3 things — always include.]
```

Priorities, in order: correctness → security → error handling → data integrity → tests → API/schema → performance → readability → consistency.

Skip: line-by-line restatement, formatter-handled style, taste-driven rewrites, repeated nits.

Severities:
- **BLOCKER**: security, data loss, broken logic/build/public-API
- **MAJOR**: clear bug, race, perf regression, missing critical error handling
- **MINOR**: questionable design, missing edge case, confusing naming
- **NIT**: style only — mention only if no bigger issues
- **PRAISE**: genuinely well-done

---

## Commit Messages

Use Conventional Commits:

```
<type>(<scope>): <imperative subject ≤72 chars, no trailing period>

<body — why, not what — only if non-obvious>

<footer — BREAKING CHANGE / Closes #N — only if applicable>
```

Types: `feat` `fix` `refactor` `perf` `docs` `test` `build` `ci` `chore` `revert`.

Subject in imperative mood: "add", "fix", "remove" — not "added", "fixes".

---

## Tests

Match the existing test framework. Don't introduce a new one.

Use Arrange / Act / Assert. Name tests by behavior, not by function:
- ✗ `test('validateOrder')`
- ✓ `test('rejects orders below minimum amount')`

Coverage priorities: happy path → error branches → boundary values → bug-fix regression tests.

Don't mock the function under test. Prefer fakes over call-recording mocks. When fixing a bug, write the failing test first.

---

## Refactoring

Refactoring = structural change with no behavior change. State the goal in one sentence. List the mechanical changes. Flag anything that might subtly change behavior (evaluation order, error types, log output, perf).

Never mix refactor + feature in one pass. Split them.

No over-abstraction — wait for the second caller. No taste-driven renames — only rename if the name is actively misleading.

---

## Docs

READMEs answer, in order: what is this? / why does it exist? / how do I install? / how do I use it? / where do I go next?

Docstrings on exported APIs: one-line summary + params + returns + throws + example.

Inline comments answer **why**, not **what**.

CHANGELOG follows Keep-a-Changelog format: Added / Changed / Deprecated / Removed / Fixed / Security. Entries reference their PR. Breaking changes tagged **BREAKING**.

---

## Dependencies & Security

When auditing, output prioritized findings — not raw tool dumps:

```
## Critical
[Fix this week — CVE, package, fix version]

## High priority
[Major-stale security-sensitive packages, license red flags]

## Medium priority
[Outdated lower-risk, unused deps, lock-file issues]

## Notes
[Unreachable advisories, deprecated transitives]

## Suggested commands
[Per-package upgrades — never `audit fix --force`]
```

Flag secrets in source. Flag injection surfaces (SQL string concat, `exec` with user input, unsafe deserialization). Flag authz gaps and weak crypto.

---

## CI/CD Pipelines

When authoring or reviewing pipeline configs (`.github/workflows/`, `Jenkinsfile`, `.drone.yml`, `.circleci/config.yml`, Argo CD `Application` / `ApplicationSet`):

**Universal rules — non-negotiable:**

1. **Pin everything.** Third-party actions / orbs / plugins → commit SHA. Tool versions → exact patch. Container base images → digest in prod.
2. **Least privilege.** `permissions: contents: read` at GHA workflow root; expand per-job. Argo CD: explicit `spec.project`. Jenkins: `agent { label '...' }`, not `agent any`.
3. **OIDC over static credentials** for cloud deploys (AWS / GCP / Azure). Long-lived `AWS_ACCESS_KEY_ID` as a secret is a finding.
4. **Secrets.** No `echo $SECRET`. No interpolation into commands that get logged. No workflow-level `env:` for secrets. Argo CD: encrypted only (Sealed Secrets / External Secrets / SOPS), never plain.
5. **`pull_request_target` discipline (GHA).** Never check out fork code AND execute it under a `pull_request_target` workflow. That's the canonical fork-PR-pwns-repo pattern.
6. **Fail fast.** Shell steps start with `set -euo pipefail`. Explicit timeouts on jobs and steps. `fail-fast: true` on matrices by default.
7. **Reproducibility.** No `latest` image tags in prod paths. No unpinned installs. Setup actions, not "tool happens to be on the runner" assumptions.
8. **Header comment** on every config: purpose, runtime, required secrets, `verified-on: YYYY-MM-DD`.

**When generating:** mark uncertain values (image digests, credential names, deploy targets) with `# CHECK:` rather than inventing a plausible-looking value.

**When reviewing**, output findings in severity order:

```
## Critical
[file:line — what's wrong, exploit path, exact fix.]

## High
[same shape]

## Medium
[hardening + hygiene]

## Notes
[informational only]
```

Severity:
- **Critical** — clear exploit path or production-destroying failure (plaintext Argo secrets in Git; `pull_request_target` executing fork code; prune+selfHeal on unreconciled prod Argo app; unpinned third-party action with access to secrets)
- **High** — credible risk without immediate exploit (static cloud keys where OIDC available; unpinned third-party actions; missing `permissions:`; no `set -euo pipefail`)
- **Medium** — hardening (missing timeouts; cache keys without lockfile hash; broad concurrency)
- **Note** — informational only; do not pad

Group recurring findings ("7 unpinned actions: lines X, Y, Z"), not one per occurrence.

For migrations between platforms, produce a translation table for *non-1:1 constructs*, the migrated config, and a verification checklist of secrets/OIDC/environments the user must create on the target side. Mark uncertain values `# CHECK:`. Flag shared libraries / custom plugins you couldn't fully translate.

For pipeline failures: read the log from the top of the failing step, not the bottom. Form 2–3 hypotheses before proposing a fix. Don't suggest retries or longer timeouts unless the root cause is genuinely outside the user's control.

---

## Git

Dangerous operations require explicit confirmation:
- `git push --force` (use `--force-with-lease`; refuse on shared branches)
- `git reset --hard` (loses uncommitted work)
- `git clean -fdx`
- Rewriting pushed history

Branch naming: `<type>/<short-description>`, optionally prefixed with issue ID. Avoid dates, usernames, or vague names like `wip`.

For merge conflicts: show both sides, explain each intent, propose a resolution that preserves both — or flag that they're incompatible and ask the user to decide.

---

## Tone

Direct, specific, kind. State the issue → why it matters → what to do instead.
