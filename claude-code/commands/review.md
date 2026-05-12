---
description: Review the current diff or a specified PR with structured, severity-tagged comments
argument-hint: "[optional: branch or PR ref, e.g. main, origin/main, #412]"
---

Run a structured code review.

**Target:** `$ARGUMENTS` (if empty, use `git diff --staged` first; fall back to `git diff main...HEAD`).

Steps:
1. Run the diff command and read the full output.
2. For changed files, read each end-to-end (not just the hunks) to get context.
3. Output the review in this format:

```
## Summary
[2–4 sentences]

## Blocking issues
[file:line — BLOCKER: explanation + fix]

## Suggestions
[file:line — MAJOR/MINOR: explanation + fix]

## Nits & style
[only include if no MAJOR/MINOR issues]

## What's good
[1–3 things done well]
```

Priorities, in order: correctness → security → error handling → data integrity → tests → API/schema → performance → readability → consistency.

Skip: line-by-line restatement of the diff, formatter-handled style (prettier/black/gofmt), personal-taste rewrites, repeated nits (mention once + "similar at X, Y").

Be specific, direct, and kind. State the issue → why it matters → what to do instead.
