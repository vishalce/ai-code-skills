---
description: Propose a behavior-preserving refactor of the specified file or selection
argument-hint: "[file path or 'staged' for current staged changes]"
---

Propose and execute a behavior-preserving refactor.

Steps:
1. Determine target from `$ARGUMENTS` (file path) or fall back to current staged changes.
2. Read the target file(s) end to end. Read 1–2 neighboring files to learn conventions.
3. Identify the test surface. If no tests cover the target, say so and offer to write characterization tests first.
4. State the refactor goal in one sentence. If you can't, ask the user what they want improved (length? duplication? nesting? naming?).
5. Output a plan BEFORE editing:

```
## Plan
- [ ] Specific mechanical change 1
- [ ] Specific mechanical change 2

## Behavior-preserving? [Yes / Yes with notes]
[Any subtle changes: evaluation order, error types, log output, perf characteristics]
```

6. Ask the user to confirm.
7. On confirmation, make the changes — one logical change per edit. Keep edits minimal and obvious.
8. After editing, state what to verify: tests to run, behaviors to eyeball.

Hard rule: do not mix refactoring with feature work. If the user asked for both, do the refactor first as a separate, verifiable step.

Defer when in doubt — over-abstraction (premature helper extraction, unnecessary class hierarchies) makes code worse, not better.
