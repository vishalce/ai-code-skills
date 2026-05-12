---
description: Stage and commit current changes with a well-crafted Conventional Commit message
argument-hint: "[optional: scope hint, e.g. auth, payments]"
---

Create a commit for the current changes.

Steps:
1. Run `git status` and `git diff --staged` (fall back to `git diff` if nothing is staged).
2. If nothing is staged, propose what to stage based on the working tree — group related changes, and if there are clearly unrelated changes, suggest splitting into multiple commits.
3. Determine the Conventional Commit type: `feat`, `fix`, `refactor`, `perf`, `docs`, `test`, `build`, `ci`, `chore`, `revert`.
4. Use scope `$ARGUMENTS` if provided, else infer from the changed paths.
5. Draft the message:

```
<type>(<scope>): <imperative subject, ≤72 chars, no trailing period>

<body — explain WHY, wrap at 72 chars — only if non-obvious>

<footer — BREAKING CHANGE: ... / Closes #N — only if applicable>
```

6. Show the draft message and the file list. Ask the user to confirm or edit.
7. On confirmation, run `git add` (only files involved) and `git commit -m "..."`.

Do not commit without showing the message first. Do not stage unrelated files. Do not write the body unless it adds information the subject doesn't.
