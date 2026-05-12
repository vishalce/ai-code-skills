---
name: code-review
description: Performs thorough, structured code reviews on diffs, pull requests, branches, or staged changes. Use whenever the user mentions "review this", "PR review", "look at my code", "review my changes", "code review", asks for feedback on a diff, pastes a unified diff, or asks Claude to comment on a branch. Also use when the user wants a PR description drafted from a diff. The skill produces severity-tagged comments (BLOCKER / MAJOR / MINOR / NIT / PRAISE) grouped by file, plus an overall summary.
---

# Code Review

Run a rigorous, structured review on code changes. The output should read like a senior engineer's review — opinionated where it matters, quiet where it doesn't, and never noisy with stylistic nits when something more important is broken.

## When to use

Trigger this skill when the user:
- Pastes a `git diff`, unified diff, or PR link
- Says "review", "look at", "feedback on", "what do you think of" + a code block
- Asks for a PR description, summary, or changelog entry from a diff
- Asks Claude to compare two branches or commits

If only a single small snippet is shared (under ~20 lines) and the user is asking a specific question about it, you can answer directly without invoking the full review structure.

## Inputs you need

Before reviewing, make sure you have:
1. **The diff itself** — ideally `git diff main...HEAD` or `git diff --staged`. If the user gave a PR URL, ask them to paste the diff or fetch it via available tools.
2. **Context** — what is the change *trying* to do? If the user didn't say, infer from commit messages and ask if you genuinely can't tell.
3. **The stack** — language, framework, conventions in use. Read 1–2 nearby files if needed to understand house style.

If any of these are missing and would meaningfully change your review, ask one focused question. Don't ask three.

## Review structure

Always output in this exact format:

```
## Summary
[2–4 sentences: what the change does, overall verdict, headline concern if any]

## Blocking issues
[Must-fix before merge. Omit the heading if none.]

## Suggestions
[Should-fix, but not blocking. Omit if none.]

## Nits & style
[Optional polish. Omit if none.]

## What's good
[1–3 things done well. Always include this — reviews shouldn't be all negative.]
```

Each comment under those sections should be prefixed with `file.ext:LINE` so the dev can jump to it.

## Severity guide

- **BLOCKER** — security issue, data loss risk, broken logic, breaks the build, breaks public API contracts, breaks tests not in the diff
- **MAJOR** — clear bug, race condition, performance regression at expected scale, missing error handling on a critical path, missing tests for non-trivial logic
- **MINOR** — questionable design, missing edge case, naming that will confuse future readers, missing docstring on exported function
- **NIT** — purely stylistic; only mention if no MAJOR/MINOR issues exist
- **PRAISE** — genuinely good — clever solution, well-named abstraction, thoughtful test

## What to look for

In rough priority order:

1. **Correctness** — does the code do what it claims? Walk through the happy path and one edge case.
2. **Security** — SQL injection, XSS, SSRF, secrets in code, unsafe deserialization, missing authz checks, overly broad CORS, dependency CVEs introduced.
3. **Error handling** — silent catches, unhandled promise rejections, missing timeouts, retries without backoff.
4. **Data integrity** — transactions, idempotency, race conditions, off-by-one in pagination/limits.
5. **Tests** — does the diff include tests proportional to its risk? Are existing tests still meaningful or did they get mocked into uselessness?
6. **API & schema changes** — breaking changes flagged? Migrations reversible? Versioning honored?
7. **Performance** — N+1 queries, unbounded loops, missing indexes implied by new queries, large allocations in hot paths.
8. **Readability** — naming, function length, nesting depth, dead code, commented-out blocks.
9. **Consistency** — matches surrounding conventions (imports, error patterns, logger usage).

## What to skip

- Don't restate what the diff does line-by-line — the reviewer already sees it.
- Don't flag formatting if a formatter is configured (prettier/black/gofmt). Trust the tool.
- Don't suggest rewrites driven by personal taste. The bar is "this will cause a problem", not "I'd do it differently".
- Don't pile on. If the same issue appears 8 times, mention it once with "and similar at lines X, Y, Z".

## PR description mode

If the user asks for a PR description rather than a review, use this template:

```
## What
[1–2 sentences on what changed]

## Why
[The problem this solves or feature it enables]

## How
[Key technical decisions and tradeoffs — only if non-obvious]

## Testing
[How you verified it works]

## Rollout / risk
[Migrations, feature flags, rollback plan — only if relevant]
```

## Examples

**Example — Blocking issue:**
> `auth/login.ts:42` — **BLOCKER**: `compare(plaintext, storedHash)` is using `===` against a bcrypt hash, which will always fail and silently rejects all logins. Use `bcrypt.compare()`.

**Example — Praise:**
> `payments/refund.ts:88` — **PRAISE**: nice use of an idempotency key keyed on `(orderId, refundReason)` — this protects against double refunds on retry without needing a distributed lock.

**Example — Nit (only when nothing bigger):**
> `utils/format.ts:12` — **NIT**: `formatAmt` → `formatAmount` would read more clearly; minor.

## Tone

Direct, specific, kind. Reviewers who are vague ("this feels off") waste the author's time. Reviewers who are mean lose trust. State the issue, state why it matters, state what to do instead — in that order.
