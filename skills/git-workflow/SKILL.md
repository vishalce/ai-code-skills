---
name: git-workflow
description: Helps with git operations — writing Conventional Commit messages, naming branches, planning interactive rebases, splitting messy commits, resolving merge conflicts thoughtfully, and crafting good PR titles. Use whenever the user says "commit message", "commit this", "what should I name this branch", "rebase", "squash", "split this commit", "merge conflict", or shares `git status` / `git diff` and asks how to commit. Also use when the user wants to understand or rewrite git history before pushing.
---

# Git Workflow

Git is the project's memory. A clean history is one where someone investigating a bug in six months can read the log and understand what happened and why. That goal drives every recommendation here.

## When to use

Trigger when the user:
- Asks for a commit message, says "commit this", shares `git diff` and wants it committed
- Asks for a branch name
- Mentions rebasing, squashing, splitting commits, fixing up history
- Has a merge conflict
- Says "amend", "reword", "reorder commits"
- Asks how to handle a PR (open it, update it, address review)

## Commit messages — Conventional Commits

Use the [Conventional Commits](https://www.conventionalcommits.org) format. It plays well with semver tooling and changelog generators.

```
<type>(<scope>): <short summary>

<body — optional, wrapped at ~72 chars, explains *why*>

<footer — optional, BREAKING CHANGE notes, issue refs>
```

### Types

- `feat` — new user-facing feature
- `fix` — bug fix
- `refactor` — code change that neither fixes a bug nor adds a feature
- `perf` — performance improvement
- `docs` — documentation only
- `test` — adding or fixing tests
- `build` — build system, deps, tooling
- `ci` — CI config
- `chore` — other maintenance (rare; prefer a more specific type)
- `revert` — reverts a prior commit

### Subject line rules

- Imperative mood ("add", "fix", "remove" — not "added", "fixes", "removing")
- Lowercase, no trailing period
- 50 chars or fewer if you can manage it; 72 is the hard ceiling
- The subject should make the change clear without the body

### When to write a body

Always write a body if:
- The *why* isn't obvious from the diff
- The change has non-obvious tradeoffs
- The change closes an issue (reference it in the footer)
- The change is breaking

Skip the body if it would only repeat the subject.

### Examples

```
feat(auth): support OAuth2 device code flow

Adds the device authorization grant for CLI and IoT clients that
can't run a local HTTP server to receive the redirect. The token
endpoint reuses the existing refresh path.

Closes #312
```

```
fix(pricing): apply SUMMER25 discount at 25%, not 5%

The discount lookup was reading `.amount` from the legacy schema
where it meant basis points; the new schema uses percent. Migration
landed in #401 but this code path was missed.

Fixes #418
```

```
refactor(orders): extract pagination into shared helper

No behavior change. Three callsites previously duplicated the
offset/limit math and edge cases (negative offset, page > total).
```

## Splitting a messy commit

If the user has one giant commit that does several unrelated things, suggest splitting it. The mechanic:

1. `git reset HEAD~1` (keeps changes, unstages them)
2. Stage and commit each logical change separately: `git add -p` for granularity
3. If already pushed, this is history rewrite — only do it if the branch is yours and unshared, or coordinate with collaborators

Output a **commit plan** before doing surgery:

```
## Commit plan
1. `feat(api): add /orders/export endpoint` — new files in routes/, controllers/
2. `refactor(orders): rename internal OrderRepo methods for consistency`
3. `test(orders): add coverage for the new export endpoint`
4. `chore(deps): bump csv-stringify to 6.5.0`

That's 4 commits from what's currently 1. The renames in #2 should land
before #1 to keep #1 reviewable.
```

## Branch naming

Aim for short, scannable, and grep-able. Common conventions (pick what the project uses):

- `feat/short-description` or `feature/...`
- `fix/short-description` or `bugfix/...`
- `chore/...`, `docs/...`, `refactor/...`
- Optionally prefix with issue ID: `feat/GBM-412-vendor-listings`

Avoid: dates in branch names, your username (the commit log already has that), or vague names like `update`, `wip`, `temp`.

## Interactive rebase

When asked to clean up history before opening a PR:

1. Identify the merge base: `git merge-base HEAD main`
2. `git rebase -i <merge-base>`
3. Output a plan for what to `pick`, `squash`/`fixup`, `reword`, or `drop`

Output the planned rebase script before executing:

```
## Rebase plan
pick    a1b2c3d  feat(orders): add export endpoint
squash  e4f5g6h  fix typo in route path          ← into the line above
squash  i7j8k9l  address review comment           ← into the line above
reword  m0n1o2p  refactor: rename Repo methods   ← will rewrite subject
drop    q3r4s5t  debug: console.log everywhere   ← was a debugging commit
```

Then ask: "Confirm before I run this?"

## Merge conflicts

Don't auto-resolve conflicts blindly. For each conflict:

1. Show both sides (`<<<<<<< HEAD` and `>>>>>>> branch-name`)
2. Explain what each side is trying to do
3. Propose a resolution that preserves both intents — or, if they're genuinely incompatible, state that and ask the user to choose

Common patterns:
- **Both sides added an entry to a list** → keep both
- **Both sides changed the same line for different reasons** → manual judgment required
- **One side deleted what the other modified** → almost always needs the user

After resolving, recommend running tests before continuing the merge/rebase.

## PR titles & descriptions

PR title = the merge commit's subject. Use the same Conventional Commits style:

```
feat(auth): add OAuth2 device code flow
```

For the description, see the `docs-changelog` skill — it has a PR description template.

## Operations that are dangerous

Flag these and require explicit confirmation:

- `git push --force` (use `--force-with-lease` instead; refuse on shared branches like `main`, `master`, `develop`)
- `git reset --hard` (loses uncommitted work)
- Rewriting history on branches that have been pushed and pulled by others
- `git clean -fdx` (deletes untracked files including ignored ones)

For each, state what will be lost and ask before proceeding.

## Examples

**Example — Commit message from a diff:**
> User: [pastes git diff showing changes to a payment retry handler]
> Response:
> ```
> fix(payments): retry failed charges with jittered backoff
>
> The previous handler retried 3 times immediately, which created
> thundering-herd spikes on Stripe's rate limiter during outages
> and caused legitimate retries to be rate-limited away.
>
> Now retries use exponential backoff (1s, 4s, 16s) with ±20% jitter.
> ```

**Example — Pushback on a force push:**
> User: "push my changes with --force to main"
> Response: "Holding on that — force-pushing to `main` will rewrite shared history and break any teammate's local main. If you really need to (e.g., you committed a secret and need it gone from history), let me know the specific reason and I'll walk you through the safer path: rewrite history on a side branch, fast-forward `main`, then coordinate. What's the underlying need?"
