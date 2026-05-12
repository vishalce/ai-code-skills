---
name: cicd-migrate
description: Translates CI/CD pipelines between platforms — Jenkins ↔ GitHub Actions, CircleCI → GitHub Actions, Drone → GitHub Actions — and produces a side-by-side translation table plus the migrated config. Use whenever the user says "convert this Jenkinsfile to GitHub Actions", "migrate from CircleCI", "move our pipelines off Jenkins", "port this to GHA", "drone to github actions", "circleci to github", "convert this pipeline", or pastes one platform's config and asks for an equivalent on another. Outputs a translation table for the constructs that don't map cleanly, the migrated pipeline, and a verification checklist.
---

# CI/CD Migrate

Translate a CI/CD pipeline from one platform to another in a way that preserves intent — not just syntax. The default failure mode of pipeline migrations is "lifted-and-shifted YAML that runs but does the wrong thing": cache keys that no longer match, credentials referenced by an ID that no longer exists, triggers that fire on different events than the user expected.

## When to use

Trigger when the user:
- Asks to convert a Jenkinsfile, CircleCI config, or `.drone.yml` to GitHub Actions (the common direction)
- Asks to convert a GitHub Actions workflow back to Jenkins or another platform (less common but real)
- Says "migrate off X to Y", "port this", "translate this", "what would this look like in <platform>"
- Pastes one platform's config and asks "how would I do this in <other platform>"

If the user wants a fresh config rather than a translation of an existing one, use `cicd-config-author`. If the migrated pipeline is failing on the new platform, use `cicd-debug`.

## The default direction

The most common migration is **to GitHub Actions** (from Jenkins, CircleCI, or Drone). This skill is opinionated about that direction by default — but it works in reverse and between any pair. If the user's target is something else, just say so.

## Inputs you need

1. **The source pipeline.** All of it — a Jenkinsfile fragment without the surrounding `pipeline { agent { ... }; options { ... } }` blocks loses critical context.
2. **Shared libraries / orbs / plugins it uses.** If the Jenkinsfile imports `@Library('platform-shared@v3')` and calls `deployToK8s(...)`, the translation depends on what that function actually does. Ask.
3. **What runners or agents it runs on.** Self-hosted Jenkins agents with specific tools preinstalled translate differently than GitHub-hosted runners.
4. **Secrets and credentials.** Names of credential IDs (Jenkins), contexts (CircleCI), secrets (Drone). The migration needs to remap each one and the user has to recreate them on the new side.
5. **What the pipeline does that isn't obvious from the YAML.** Posts to Slack via a shared library? Updates a status check on a different repo? Some constructs are first-class on one platform and not on another.

## Method

### 1. Read the source pipeline end to end before translating anything

Tempting to translate stage-by-stage. Don't. The whole shape matters because some constructs (Jenkins `post {}` blocks, CircleCI `workflows.requires`, Drone `depends_on`) only make sense in the context of the full file.

### 2. Build a translation table for non-obvious mappings

Before writing the new config, list the constructs that don't have a 1:1 mapping. Show the user. This is the diff between "lift and shift" and "actually understood the migration".

### 3. Write the target config

Apply the universal CI/CD principles from `cicd-config-author` — pinning, least privilege, OIDC, timeouts, header comment. Don't carry forward bad patterns from the source pipeline just because they were there.

### 4. Produce a verification checklist

Things the user has to wire up on the new side that the YAML alone can't capture: secrets to create, OIDC trust policies, branch protection rules, environment configs, status check names if other automation expects them.

## Translation tables

The high-leverage parts of each migration.

### Jenkins → GitHub Actions

| Jenkins (declarative) | GitHub Actions | Notes |
|---|---|---|
| `pipeline { agent { label 'linux' } }` | `runs-on: ubuntu-latest` (or self-hosted label) | GH-hosted runners are ephemeral; Jenkins agents are often long-lived with tools preinstalled. The migrated workflow may need explicit setup steps. |
| `stage('X') { steps { ... } }` | `jobs.x.steps: [...]` | A Jenkins stage maps to either steps within a job or a separate job. Use a separate job if you want parallelism or if it has different `agent`/`runs-on`. |
| `parallel { 'a': { ... }, 'b': { ... } }` | Separate jobs + `strategy.matrix` or `needs:` | GHA parallelism is at the job level, not within a job. |
| `options { timeout(time: 30, unit: 'MINUTES') }` | `timeout-minutes: 30` on the job | Step-level: `timeout-minutes:` on the step. |
| `options { disableConcurrentBuilds() }` | `concurrency: { group: '${{ github.workflow }}-${{ github.ref }}', cancel-in-progress: false }` | |
| `triggers { cron('H 4 * * *') }` | `on.schedule: [{ cron: '0 4 * * *' }]` | Jenkins `H` (hashed) → GHA needs a fixed minute. |
| `when { branch 'main' } ` | `if: github.ref == 'refs/heads/main'` | Or split with `on.push.branches: [main]`. |
| `withCredentials([usernamePassword(credentialsId: 'X', ...)])` | `${{ secrets.X_USERNAME }}` / `${{ secrets.X_PASSWORD }}` | Jenkins credentials are typed (username+password, secret text, file). GHA secrets are strings only — file-type credentials need a step that writes them to disk. |
| `post { always { ... }; failure { ... } }` | `if: always()` / `if: failure()` on a final step | Or split into a job with `needs:` and `if:`. |
| `sh 'cmd'` | `run: cmd` (default shell: bash on Linux, pwsh on Windows) | Add `shell: bash` explicitly on Windows runners. |
| `script { /* groovy */ }` blocks | No equivalent | Most of the time the Groovy is gluing CLI calls together; rewrite as bash. Complex Groovy is the hardest part of a migration — flag it loudly. |
| Shared library calls (`deployToK8s()`) | Composite action or reusable workflow | Ask the user what the function does before translating. |

**Specific Jenkins gotchas:**
- Jenkins env vars like `${BUILD_NUMBER}`, `${BUILD_URL}`, `${GIT_COMMIT}` → GitHub Actions `${{ github.run_number }}`, `${{ github.server_url }}/...`, `${{ github.sha }}`.
- `currentBuild.result` → no direct equivalent. Use job outputs + `needs.x.result`.
- Multibranch pipelines are *the* default mental model in Jenkins. GHA workflows are per-file in `.github/workflows/`; "one Jenkinsfile in every branch" maps to "the workflow file in the branch decides what runs."

### CircleCI → GitHub Actions

| CircleCI | GitHub Actions | Notes |
|---|---|---|
| `version: 2.1` + `orbs:` | `uses: org/action@sha` per step | Orb commands → composite actions or direct steps. |
| `jobs.x.executor: docker` + `image: cimg/node:20.10` | `runs-on: ubuntu-latest` + `setup-node@... with node-version: 20.10` | CircleCI's `cimg/*` images have many tools preinstalled; GHA runners have a different set — verify your build commands still work. |
| `resource_class: medium+` | No direct equivalent | GHA Linux runners have fixed specs (2 vCPU, 7 GB for `ubuntu-latest`). For more, use larger runners (paid) or self-hosted. |
| `workflows.x.jobs: [{ require: [a, b] }]` | `jobs.x.needs: [a, b]` | |
| `parallelism: 4` (test splitting) | `strategy.matrix.shard: [1, 2, 3, 4]` + manual split | GHA has no built-in `circleci tests split` equivalent. Use the matrix strategy with your test runner's built-in sharding (`jest --shard=$N/4`, `pytest --splits 4 --group $N`). |
| `contexts: [aws-prod]` | `environment: aws-prod` + secrets attached to that environment | GH environments give you required reviewers + secret scoping similar to contexts. |
| `restore_cache` / `save_cache` with `keys:` | `actions/cache@SHA` with `key:` + `restore-keys:` | The semantics are similar. Translate cache-key checksum syntax carefully — `{{ checksum "package-lock.json" }}` → `${{ hashFiles('**/package-lock.json') }}`. |
| `store_test_results` / `store_artifacts` | `actions/upload-artifact@SHA` | GHA doesn't have first-class test-result aggregation; use a third-party action or post-process. |

### Drone CI → GitHub Actions

| Drone | GitHub Actions | Notes |
|---|---|---|
| `kind: pipeline; type: docker` | A GHA job with steps that `uses:` containers | Drone runs every step in its own container by default. GHA can do this via `jobs.x.container:` or `steps[].uses: docker://...`. |
| `steps[].image: alpine:3.19` | `container: alpine:3.19` on the job, or `uses: docker://alpine:3.19` on the step | |
| `trigger.event: [tag]` | `on.push.tags: ['v*']` | Drone events are coarser than GHA `on:` triggers — write the equivalent explicitly. |
| `environment.FOO: { from_secret: foo }` | `env.FOO: ${{ secrets.FOO }}` | Same secret-name convention is fine. |
| `depends_on: [test]` | `needs: [test]` | At the pipeline level in Drone, this becomes job-level in GHA. |
| `when: { branch: main }` | `if: github.ref == 'refs/heads/main'` | Or `on.push.branches: [main]`. |
| `plugins/docker` step (build+push) | `docker/build-push-action@SHA` + `docker/login-action@SHA` | Settings field structure differs — re-read the action's inputs. |
| Multiple `kind: pipeline` blocks in one file | Multiple workflow files | GHA workflows are one-per-file. |

### Reverse: GitHub Actions → Jenkins

Less common but comes up. The hard parts:
- GHA `matrix` with multiple dimensions → Jenkins requires a more manual `parallel { }` construction.
- GHA composite actions → Jenkins shared library functions, or inlined.
- GHA `concurrency` → Jenkins `disableConcurrentBuilds()` (single-instance) or a `lock` resource (custom).

## Output format

Output in this order:

```
## Migration summary
[2–3 sentences: what's being translated, which platform → which platform, the headline gotcha.]

## Constructs that don't map 1:1
[The translation table for the specific constructs in this user's pipeline, not the general one above. Skip constructs that mapped cleanly.]

## Translated pipeline
[The new config in a single fenced code block, with the standard header comment from cicd-config-author.]

## Verification checklist
[Concrete things the user must do on the new side before this works: create these secrets, set up this OIDC trust, configure this environment, recreate this branch protection rule.]

## Things I'm unsure about
[List anything you marked `# CHECK:` in the YAML and the reason. If the source pipeline uses a shared library or custom plugin you couldn't fully translate, name it here.]
```

## Anti-patterns to avoid

- **Translating syntax without translating semantics.** A Jenkins `agent any` should not become `runs-on: any` (that doesn't exist) or `runs-on: self-hosted` (that's a guess). Ask which agent the original ran on.
- **Carrying forward unpinned dependencies.** If the source uses `actions/checkout@v4` floating, the migration is a good moment to pin to SHA — same for unpinned plugins, orbs, base images. State this as an improvement, not a transparent translation.
- **Inventing credential names.** If the source references `credentialsId: 'gh-deploy-key'`, the new config should reference `secrets.GH_DEPLOY_KEY` (or whatever the user names it), AND the verification checklist tells the user to create that secret. Don't silently rename.
- **Skipping the "I'm unsure" section.** If something in the source pipeline doesn't translate cleanly — Groovy `script {}` blocks, a custom Drone plugin, a CircleCI orb command with non-obvious behavior — flagging it loudly is the migration's most valuable output.
- **Hiding stage parallelism behind sequential jobs.** A Jenkins `parallel { 'a', 'b' }` should become parallel GHA jobs, not sequential steps. Preserve the concurrency the user already had.

## Examples

**Example — minimal Jenkins stage → GHA:**

> User pastes:
> ```groovy
> stage('Test') {
>   steps {
>     sh 'npm ci && npm test'
>   }
> }
> ```
>
> Translation:
> ```yaml
> jobs:
>   test:
>     runs-on: ubuntu-latest
>     timeout-minutes: 15
>     steps:
>       - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11 # v4.1.1
>       - uses: actions/setup-node@60edb5dd545a775178f52524783378180af0d1f8 # v4.0.2
>         with: { node-version: '20.x', cache: 'npm' }
>       - run: |
>           set -euo pipefail
>           npm ci
>           npm test
> ```
>
> Note: I added `setup-node` (Jenkins agent had it preinstalled, GHA doesn't), `cache:` (Jenkins didn't have npm caching), a timeout (Jenkins had a default, GHA's is 6h), and split the two commands so a failure in `npm ci` is reported separately from a failure in `npm test`.

**Example — Pushback on incomplete translation:**

> User: "convert our Jenkinsfile, it's about 200 lines with a shared library."
> Response: "Happy to. The shared library is the part I can't translate from the Jenkinsfile alone — calls like `notifySlack()` or `deployToK8s()` become composite actions or reusable workflows in GHA, but I need to see what they actually do (or at least know what their inputs and effects are). Can you paste the library's relevant functions, or describe what each one does? Otherwise I'll be guessing and the migration will be wrong in subtle ways."

## Tone

Migrations are inherently lossy — some things on one platform have no equivalent on another. Be honest about what's a clean translation, what's a workaround, and what's genuinely uncertain. The user has to live with the result; a confident-but-wrong migration is worse than a thoughtful one with `# CHECK:` markers.
