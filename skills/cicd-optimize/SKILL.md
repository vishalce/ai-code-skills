---
name: cicd-optimize
description: Reduces CI/CD pipeline runtime and cost — cache strategy, parallelization, matrix tuning, runner sizing, build avoidance, layer caching. Use whenever the user says "my CI is slow", "pipeline takes too long", "speed up GitHub Actions", "reduce CI cost", "CI is expensive", "optimize this workflow", "the build takes 40 minutes", "we're paying a fortune for CI", or shares a slow pipeline and asks how to make it faster. Outputs a prioritized list of changes ranked by likely time saved, not by how clever they sound.
---

# CI/CD Optimize

Make pipelines faster and cheaper without making them flakier. The cardinal rule: optimize the wall-clock critical path, not the things that are easy to measure. Cutting a 30-second linter while a 20-minute integration test sits untouched is theater.

## When to use

Trigger when the user:
- Says "CI is slow", "build takes too long", "speed this up", "reduce CI cost / minutes / credits"
- Pastes a workflow with timing annotations and asks where to cut
- Asks about caching, parallelization, matrix strategies, runner sizing, or "should I use a bigger runner"
- Asks about build-time analysis tools (`actions/timing-action`, CircleCI insights, Buildkite analytics)

If the pipeline is *failing*, use `cicd-debug`. If it's a security review, use `cicd-review-audit`. If it's a fresh design, use `cicd-config-author`.

## Inputs you need

1. **The current pipeline.** Optimizing without seeing the config is guessing.
2. **Wall-clock timing per job/step.** GHA shows step durations in the UI; CircleCI has the insights view; Jenkins has timestamps with the Timestamper plugin. Without this you can't tell the critical path from the noise.
3. **Whether this runs on PRs, main, both.** PR optimization (fast feedback) and main-branch optimization (correctness, artifact production) have different priorities.
4. **The budget constraint.** Wall-clock time? Runner credits / GHA minutes / CircleCI credits? Self-hosted runner saturation? These point to different fixes.

If timing data is missing, *ask for it* — don't optimize blind. If the user can't get timing data, ask them to run one slow build and share the step durations from the run summary.

## Method — measure, then cut

### 1. Identify the critical path

The critical path is the longest chain of dependent jobs from start to finish. Parallel jobs that finish before the longest one don't matter for wall-clock time (they may still matter for cost).

Ask: which single job is the bottleneck? If that job were instant, what would the new total be?

### 2. Rank candidates by likely time saved, not by ease

A 40% speedup on a 20-minute job (saves 8 minutes) beats a 90% speedup on a 30-second job (saves 27 seconds). Always.

### 3. Verify each change actually helped

CI runtimes vary run-to-run. A 10% improvement on a single run could be noise. Look at the median across 5+ runs, not the best case.

## High-leverage things to check first

These yield the biggest wins most often.

### 1. Dependency installation

If `npm ci` / `pip install` / `bundle install` is taking minutes, it's almost always a cache miss.

- **Cache hit rate**: log it explicitly. GHA's `actions/cache` reports `cache-hit: true/false` as an output — use it.
- **Cache key**: must include the lockfile hash. `hashFiles('**/package-lock.json')`, `hashFiles('**/poetry.lock')`, etc. A constant cache key restores stale state but might appear to "work".
- **Restore keys (partial restore)**: useful when most dependencies are stable but one changed — restore the closest match, then `npm install` only the diff. Be deliberate: partial restore can mask missing-dep bugs if your install step doesn't run.
- **Cache scope**: GHA caches are per-branch with fallback to default branch. Don't expect PR caches to hit each other.

### 2. Test parallelism

If the test suite is the bottleneck, splitting it is usually the highest-ROI change.

- **Jest**: `--shard=$N/$TOTAL` with a matrix of `[1/4, 2/4, 3/4, 4/4]`.
- **pytest**: `pytest --splits 4 --group $N` (pytest-split) or `pytest-xdist` for in-process parallelism.
- **Go**: `go test -p N` parallelizes packages by default; the real wins are running test packages on separate runners.
- **Diminishing returns**: 4-way split usually wins; 16-way split usually doesn't because runner-startup overhead dominates. Measure.

### 3. Build caching (layer caching for Docker)

- **Docker buildx with cache exports**: `docker/build-push-action@SHA` with `cache-from: type=gha` and `cache-to: type=gha,mode=max` for GHA-native cache. `type=registry,ref=...` if pushing to your own registry.
- **Multi-stage Dockerfiles**: order so the cache-busting `COPY . .` happens *after* the dependency install. Cache hits stop at the first changed line.
- **`mode=max` vs `mode=min`**: max caches intermediate layers (faster subsequent builds, more storage); min only caches the final layer. Default `mode=max` for first-class build caching.

### 4. Job vs step parallelism

- Things that don't depend on each other should run in parallel jobs, not sequential steps within one job.
- Counterpoint: each GHA job pays a runner-startup cost (~10-30s on GHA-hosted runners). Don't split below a job that's already under ~30s of work.

### 5. Conditional execution (path filters, skip-CI)

- `on.push.paths` / `on.pull_request.paths`: skip workflows entirely when only docs changed.
- **Required status checks gotcha**: if you skip a job, GHA reports it as `skipped`, but branch protection that requires it will *fail*. Fix: use a wrapper job that always runs and gates the skip, or use the `paths-ignore` pattern with care.

### 6. Right-sized runners

- `ubuntu-latest` (2 vCPU, 7 GB) is the GHA default and is right for most workloads.
- Larger runners save time only if the job is CPU- or memory-bound. An I/O-bound install step on a 16-vCPU runner is the same speed as on a 2-vCPU runner *and costs 8x*.
- Measure CPU + memory before upsizing. If `time` on the slow step shows >90% CPU and the runtime is meaningful, a bigger runner helps.

### 7. Self-hosted runner saturation

- If self-hosted runners are constantly queueing, *queue time* dominates *runtime* and no amount of pipeline optimization fixes that. The fix is more runners or smarter scheduling.

## Platform-specific notes

### GitHub Actions
- `actions/cache@SHA`: solid for deps. Avoid third-party cache actions unless they offer something the official action can't.
- Setup actions (`actions/setup-node`, `setup-python`, `setup-go`) have a `cache:` input — use it instead of a separate cache step.
- Larger runners (4, 8, 16 cores) are billed at proportionally higher per-minute rates. Net cost only drops if the build is fully CPU-bound and the time savings outpace the per-minute rate.

### Jenkins
- Build agents with pre-warmed Docker layer caches save real time vs ephemeral agents.
- `Lockable Resources` for things that genuinely can't parallelize (e.g., a shared staging env). Don't use them as a "fix" for flaky parallel tests.

### Drone CI
- Steps within a pipeline run sequentially by default; for parallelism use multiple pipelines with `depends_on`.
- Image pulls dominate startup time — pin image versions and use a runner with a warm cache, or use a smaller base image.

### CircleCI
- `parallelism: N` + `circleci tests split --split-by=timings` is the first-class way to shard a test suite. Use it.
- `resource_class` is more granular than GHA — match the class to the actual CPU/memory profile of the job.

### Argo CD (not really a CI optimization, but)
- Slow syncs are usually slow because health checks take time, not because Argo is slow. Look at custom health-check Lua scripts and sync wave depth.

## Output format

```
## Current state
[1–2 sentences: total wall-clock time, critical path, headline cost.]

## Top opportunities (ranked by likely time saved)
1. **[Change]** — Estimated savings: [X minutes / Y%]. [Why this is high-impact.]
2. ...
3. ...

## Diffs / suggested changes
[Concrete config changes for the top 1–3 items, as diffs.]

## Things to measure before/after
[How to verify the change actually helped — what to look at, where to find the timing.]

## Things NOT to do
[Specific things the user might be tempted to do that won't help or will hurt — e.g., "bigger runner won't help because this step is I/O-bound on registry pulls".]
```

## Anti-patterns to avoid

- **"Add more parallelism" without identifying the critical path.** Parallelizing a non-bottleneck wastes runner credits and doesn't change wall-clock.
- **`continue-on-error: true` to "speed things up"** by ignoring failures. That's not optimization, that's hiding bugs.
- **Caching build outputs as a substitute for incremental builds.** Cache deps; for build outputs use the build tool's incremental mode (Turbo, Nx, Bazel, Gradle build cache).
- **Replacing `npm ci` with `npm install` to "use the cache better".** `npm ci` is the right command in CI — it's deterministic and respects the lockfile. The cache-hit problem is in the *cache key*, not the install command.
- **Optimizing PR builds for cost.** PR builds should optimize for *feedback time* — wait time for a developer is expensive. Optimize main-branch and nightly builds for cost.
- **Upgrading to a bigger runner without measuring.** Default to measuring CPU/memory first. The "we just used a 16-core runner and it didn't help" stories are universal.

## Examples

**Example — Ranked recommendations:**

> User: "our GHA Node workflow takes 22 minutes. Mostly the test job."
>
> Looking at the config:
>
> **Current state:** 22 min total, ~18 min in `test`. `npm ci` takes 4m (cache appears not to hit — key doesn't include lockfile), `npm test` runs serially.
>
> **Top opportunities:**
> 1. **Cache `npm ci` properly** — Estimated savings: 3 min per run. Cache key currently `${{ runner.os }}-node` (constant); change to include `hashFiles('package-lock.json')`. This compounds with #2.
> 2. **Shard Jest 4 ways** — Estimated savings: 9 min (14 min → ~5 min on the critical path). Use `--shard` with a matrix of `[1/4, 2/4, 3/4, 4/4]`. Each shard pays its own setup cost (~30s), so 4-way is the sweet spot.
> 3. **Run lint + typecheck in parallel jobs with test, not as sequential steps in `test`** — Estimated savings: 1.5 min. Lint and typecheck are 90s of the current job's serial path.
>
> [Diff for #1 and #2 follows]
>
> **Things to measure**: GHA UI step durations across 5 runs, median. Compare median total before/after.
>
> **Things NOT to do**: don't upgrade to a 4-core runner — `npm ci` and Jest aren't CPU-bound on this codebase, they're disk-bound on `node_modules`. Bigger runner won't help.

**Example — Pushback on a premature ask:**

> User: "switch us to 16-core runners, our CI is too slow."
> Response: "Before that — can you share the step-by-step timing for one slow run? 16-core runners are ~8x the per-minute cost; they save time only if the bottleneck is CPU-bound. The two most common 'CI is slow' causes are (a) `npm ci` cache misses and (b) test suites that should be sharded — bigger runners don't help either. If the timings show actual CPU saturation on a 2-core runner, I'll absolutely recommend the upgrade. I just want to make sure the diagnosis matches the prescription."

## Tone

You're the engineer who has to defend this change to a skeptical platform team. Show the math. Estimate before you change. Measure after. Be honest when an optimization didn't help, and roll it back rather than declare victory.
