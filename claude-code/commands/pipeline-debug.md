---
description: Diagnose a failing CI/CD pipeline from logs + config. Hypothesis-first RCA, not symptom-patching.
argument-hint: "[path to log file, or paste the log into the prompt]"
---

Find the root cause of a CI/CD pipeline failure and propose a fix that addresses the cause, not the symptom.

**Inputs:** `$ARGUMENTS` may be a path to a saved log file. If empty, ask the user to paste the failure log (the *failing step's* output with ~30 lines of context above it — not the last "Process completed with exit code 1" line alone).

Also read the relevant pipeline config (`.github/workflows/*.yml`, `Jenkinsfile`, `.drone.yml`, `.circleci/config.yml`, or the Argo `Application`) to interpret the log in context.

Method:
1. **Scan the log from the top** of the failing step, not the bottom. The first error is usually the cause; the last is usually a cascade.
2. Look specifically for: first non-zero exit code, OOM signals (`exit code 137`, `Killed`, `OOMKilled`), disk-full (`No space left on device`), permission errors (`EACCES`, `denied:`), network errors (DNS / TLS / `i/o timeout` / `dial tcp`).
3. **Form 2–3 hypotheses.** Don't anchor on the first plausible one.
4. For each, ask: what would I expect to see (or not see) in the log if this were true? Check.
5. Pick the most-supported hypothesis. If only a workaround is possible (e.g., a third-party endpoint flake), say so explicitly.

Output:

```
## Hypothesis
[Most-supported explanation, one sentence.]

## Evidence
[2–4 bullets quoting specific log lines / config snippets, with line numbers where available.]

## Root cause
[What is actually wrong — in terms of state or configuration, not "the build failed".]

## Fix
[Minimal change addressing the root cause. Show a diff or the exact config to change.]

## Prevention
[1–2 changes so this class of failure can't recur silently.]

## Alternative hypotheses considered
[1–2 ruled out, with why. Skip if there was only one plausible explanation.]
```

Anti-patterns to avoid:
- Suggesting "add retries" or "increase timeout" without confirming the root cause
- `continue-on-error: true` as a fix
- Confusing the loudest error in the log for the cause

For pipeline *quality* review (not failure), use `/pipeline-review`. For security audit use `/pipeline-audit`.
