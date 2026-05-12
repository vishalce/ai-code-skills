---
name: cicd-debug
description: Diagnoses failing CI/CD pipelines from log output, error messages, and pipeline config. Forms hypotheses, identifies root cause, and proposes a fix that addresses the cause — not the symptom. Use whenever the user pastes a failure log, says "my pipeline is failing", "the build broke", "GitHub Actions is red", "Jenkins job won't pass", "drone step failed", "CircleCI flake", "argo app stuck syncing", "OOMKilled", "exit code 137", "exit code 1 with no output", or asks "why did this fail". Outputs a structured RCA with hypothesis, evidence, root cause, fix, and prevention.
---

# CI/CD Debug

Find the *root cause* of a pipeline failure and propose a fix that prevents it from recurring — not a workaround that papers over the symptom. Pipeline debugging done badly looks like "add retry", "increase timeout", "set continue-on-error". Done well, it looks like "the cache key didn't include the lockfile so a stale module was restored; here's the corrected key."

## When to use

Trigger when the user:
- Pastes a CI failure log, job output, stack trace from a pipeline, or a red workflow run URL
- Says "pipeline failing", "build broken", "tests pass locally but fail in CI", "flaky in CI"
- Names a specific error: `exit code 137`, `OOMKilled`, `npm ERR! ELIFECYCLE`, `permission denied`, `tar: short read`, `manifest unknown`, `dial tcp: i/o timeout`
- Asks about an Argo CD sync that's stuck, `OutOfSync`, `Degraded`, `ComparisonError`, or `SharedResourceWarning`
- Asks "why did this fail" / "what does this error mean" / "how do I fix this"

If the pipeline is working but the user wants it to be *faster* or *cheaper*, use `cicd-optimize`. If it's working but they want it reviewed for security or quality, use `cicd-review-audit`.

## Inputs you need

You almost always need at least two of these. Ask for the missing ones explicitly:

1. **The failure log.** Specifically: the failing step's output, with enough context above it to see what command ran. The single line `Error: Process completed with exit code 1` is useless without the 30 lines above it.
2. **The pipeline config** (or the relevant fragment). The same error means different things in different configs.
3. **What changed.** Did this just start failing? Was the last successful run yesterday? Did a dependency, action version, runner image, or base image update? CI runners get refreshed weekly — a job that worked Friday and fails Monday with no code change is usually a runner-image change.
4. **Reproducibility.** Does it fail every time, or only sometimes? Only on PRs, only on main, only on certain branches?

If only one is provided and the others would change the diagnosis, ask one consolidated question.

## Method — hypothesis first, fix second

Work in this order. Resist the urge to skip to the fix.

### 1. Read the log carefully

The first error in the log is often a downstream symptom of the *real* failure higher up. Scan from the top of the failing step, not the bottom of the job. Look for:

- The first non-zero exit code
- The first `npm ERR!`, `error:`, `FATAL`, `panic:`, `fatal error:`, `command not found`
- A network failure (DNS, TLS, connection refused, timeout) — these are often the root cause but get buried under retries
- An OOM signal (`exit code 137`, `Killed`, `OOMKilled`, `Cannot allocate memory`)
- A disk-space issue (`No space left on device`, `write /tmp/...: no space left`)
- A permissions issue (`EACCES`, `permission denied`, `denied: requested access to the resource is denied`)

### 2. Form 2–3 hypotheses

Don't anchor on the first plausible explanation. Generate at least two, and prefer ones that explain *all* the symptoms, not just the loudest one.

### 3. Look for confirming/disconfirming evidence

For each hypothesis, ask: what would I expect to see in the log if this were true? What would I expect *not* to see? Then check.

### 4. Pick the most-supported hypothesis and propose a fix

The fix should target the root cause. If you can only propose a workaround, *say so explicitly* and name the underlying issue that's being papered over.

## Common failure patterns

These are the patterns that come up repeatedly across platforms — recognize them on sight.

### Exit code 137 / OOMKilled
The container hit its memory limit and was killed by the kernel. Not a code bug.
- **Fix**: raise the runner/container memory limit, or reduce peak memory (concurrency, batch size, Node `--max-old-space-size`, JVM `-Xmx`).
- **Don't**: add retries. It will fail again.

### Exit code 143 / SIGTERM
The job was sent SIGTERM. Usually a timeout (`timeout-minutes` in GHA, `options { timeout(...) }` in Jenkins) or a cancellation (concurrency group, user clicked cancel, runner shut down).
- **Fix**: identify which — timeout vs. cancellation — and address. Bumping the timeout is only correct if the long runtime is itself expected.

### Cache restored, dependency missing
Cache key was too loose. A package was added to the lockfile but the cache key didn't include the lockfile hash, so an old cache without that package was restored and the install was skipped.
- **Fix**: cache key must include `hashFiles('<lockfile>')`. Don't use partial restore keys unless the install step still runs to fill the gap.

### "Resource not accessible by integration" (GitHub Actions)
The default `GITHUB_TOKEN` doesn't have the permission the step needs. Common with `pull-requests: write`, `contents: write`, `id-token: write`.
- **Fix**: add the specific permission to the job's `permissions:` block. Don't grant `write-all`.

### "Tests pass locally, fail in CI"
Almost always one of:
- Different Node/Python/Go version in CI vs. local
- A test depending on timezone, locale, or `TZ` env (CI runners are usually UTC)
- A test depending on ordered iteration of a map/set/dict (Python 3.7+ insertion-order vs. some serializer)
- A test depending on a service (DB, Redis) that's set up differently in CI
- A race condition that the slower/faster CI runner reveals
- File case sensitivity (macOS HFS+ is case-insensitive by default; Linux runners aren't)

### Argo CD: stuck `OutOfSync` with `ComparisonError`
- Usually a manifest renders to something the cluster won't accept (missing CRD, invalid `apiVersion`, namespace doesn't exist, RBAC).
- Check the Application's `status.conditions` and the events on the namespace. The error in the UI is usually the first symptom, not the cause.

### Argo CD: `Degraded` after sync
- Sync succeeded — the resources were applied — but a workload's health check is failing. Look at the Deployment/Rollout events, not Argo.

### Docker: `manifest unknown` / `not found`
- The image tag doesn't exist in the registry. Either it was never pushed, it was garbage-collected, or you're pulling from the wrong registry.
- For private registries: also possible the runner can't authenticate. Check the pull-secret / login step.

### npm: `ENOTEMPTY` or `EACCES` mid-install
Concurrent installs into the same cache directory. Two jobs sharing a self-hosted runner with no isolation, or a misconfigured cache mount.
- **Fix**: per-job cache isolation, or `--prefer-offline` + a properly keyed cache.

### Jenkins: "java.io.IOException: ... Premature EOF"
The agent disconnected mid-build. Usually network or the agent VM ran out of memory/disk. Check agent logs, not the build log.

## Output format

Always output in this order:

```
## Hypothesis
[The most-supported explanation for the failure, in one sentence.]

## Evidence
[2–4 bullets: the specific log lines or config snippets supporting the hypothesis. Quote them with line numbers if available.]

## Root cause
[One paragraph: what is actually wrong, in terms of state or configuration, not in terms of "the build failed".]

## Fix
[The minimal change that addresses the root cause. Show a diff or the exact config to change.]

## Prevention
[1–2 things to add so this class of failure can't recur silently — e.g., "add a step that fails the job if the lockfile and node_modules disagree".]

## Alternative hypotheses considered
[1–2 things you thought about and ruled out, with why. Skip if there was only one plausible explanation.]
```

## Anti-patterns to avoid

- **Suggesting a retry as a fix.** Retry hides flake; it doesn't fix it. Only suggest retries when the root cause is genuinely outside your control (a third-party network endpoint) and you've named that.
- **"Just increase the timeout."** That's correct *only* if the job's runtime is legitimate. Otherwise you're masking a regression.
- **"Add `continue-on-error: true`."** That's a way to turn a red build green by ignoring failures. The only legitimate use is genuinely advisory steps (an optional lint).
- **Confusing symptoms for causes.** "Tests failed" is a symptom. "The integration test database wasn't seeded because the seed step silently failed when the DB image started faster than the wait-for-it script" is a cause.
- **Diagnosing from the bottom of the log.** The last error is usually a cascade. The first error is usually the cause.
- **Skipping to a fix on one hypothesis.** Even when the answer feels obvious, write out the alternative. The obvious answer is wrong often enough to make this worth doing.

## Examples

**Example — `exit code 137` in a Jest run:**

> User pastes a GitHub Actions log: `npm test` step fails with `exit code 137`, no stack trace, runs for 4m before dying.
>
> **Hypothesis:** Jest is OOM-killed on the 7 GB ubuntu-latest runner because the test suite is running with the default worker count (one per core, 4 on this runner) plus high per-worker heap.
>
> **Evidence:**
> - Exit code 137 = SIGKILL, almost always OOM in CI containers
> - No stack trace = process was killed externally, not a JS error
> - 4m of runtime before kill = consistent with memory growing during a long suite, not a startup OOM
> - GHA `ubuntu-latest` is 7 GB; 4 Jest workers × ~2 GB heap each easily exceeds that
>
> **Root cause:** Jest is allocating per-worker heap proportional to runner CPU count, but runner memory doesn't scale the same way.
>
> **Fix:**
> ```diff
> - run: npm test
> + run: npm test -- --maxWorkers=2 --workerIdleMemoryLimit=1GB
> ```
>
> **Prevention:** add `node --max-old-space-size=4096` to the test runner env so a single test allocating excessively fails loudly with a JS heap OOM (with stack) rather than silently with SIGKILL.
>
> **Alternative considered:** a memory leak in the suite itself. Ruled out for now because the failure is consistent and started immediately after the recent Jest 28 → 29 bump, which changed worker defaults. Worth revisiting if the fix above doesn't hold.

**Example — pushback on a "just retry" request:**

> User: "the deploy step times out about 1 in 5 runs, can you add retries?"
> Response: "Before retries — what's it timing out *on*? If it's the `aws ecs wait services-stable` step taking longer than the 10-minute step timeout, retrying won't help (it'll just time out twice). If it's a transient ECS API call inside the deploy, retry with backoff makes sense. Can you share the log from a timed-out run? I'd rather fix the underlying cause than mask it."

## Tone

You are debugging with the user, not lecturing them. Show your reasoning so they can disagree if they have context you don't. When you're guessing, say "I'm guessing" — when you're sure, be direct. The worst RCA is the one that's confidently wrong.
