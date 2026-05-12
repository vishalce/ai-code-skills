---
name: refactor-cleanup
description: Safely refactors code — extracting functions, renaming, removing dead code, splitting large files, modernizing idioms, and reducing duplication. Use whenever the user says "refactor", "clean up", "simplify", "this is too long", "extract", "DRY this up", "modernize", "tidy", or asks to split a file, rename across a codebase, or reduce complexity. Also use when the user shares a file and asks Claude what could be improved structurally (not behaviorally). The skill makes behavior-preserving changes and explicitly flags anything that might alter behavior.
---

# Refactor & Cleanup

Refactoring is changing structure without changing behavior. That second half — *without changing behavior* — is the part that gets violated most often. Treat it as a hard constraint.

## When to use

Trigger when the user:
- Says "refactor", "clean up", "simplify", "tidy", "DRY", "extract", "split"
- Shares a long function or file and asks how to improve it
- Asks to rename a symbol across a codebase
- Asks to modernize legacy patterns (callbacks → async/await, class components → hooks, var → let/const, etc.)
- Says "this is hard to read" or "this is too complex"

Don't trigger if the user is asking to *change behavior* (add a feature, fix a bug, change output). That's a different task — refactoring may be a step, but it's not the goal.

## The discipline

Before touching code:

1. **Identify the test surface.** Are there tests covering this code? If yes, note them and plan to run them after. If no, *say so* and offer to write characterization tests first for anything non-trivial.
2. **State the goal in one sentence.** "Extract the parsing logic from `handleRequest` into a pure function." If you can't write that sentence, you don't know what you're refactoring yet.
3. **List the changes you'll make.** Mechanical: rename, extract, inline, move. Each change should be obviously behavior-preserving.
4. **Flag anything that *might* change behavior** — even subtle things like evaluation order, error types thrown, or log output. Surface these as questions, don't make the call silently.

## Refactoring patterns

In rough priority:

### Extract function / extract method
When a block of code has a clear, nameable purpose, pull it out. The name in the extraction is most of the value — if you can't name it well, the extraction is wrong.

### Rename
Local renames are nearly always safe. Cross-file renames need confidence in tooling — use LSP/IDE refactor if available; if doing it textually, search for *all* references including string references (DI containers, route names, serialized configs) and flag anything ambiguous.

### Remove dead code
- Unused exports → check for external consumers first (look for the symbol in tests, configs, and route registrations).
- Commented-out blocks → delete. Git remembers.
- Feature flags long since rolled out → ask if the flag can be retired before removing branches.

### Reduce nesting
Replace `if (good) { ... } else { return error }` chains with early returns. Stop nesting where the function ends.

### Split a large file
A file is "too big" when it holds multiple unrelated responsibilities, not just because it crossed a line count. Split by responsibility, not by length.

### Modernize idioms
Conservative defaults — only modernize when:
- The new idiom is a project convention (check neighboring files)
- The change doesn't alter error semantics (Promise chains can throw at different points than async/await without care)
- Tests exist to catch regressions

### Remove duplication
DRY is a heuristic, not a law. Two pieces of code that *look* the same but represent different concepts should stay separate. Only collapse duplication when the duplicated code is genuinely one concept that's been copy-pasted.

## What to do, step by step

1. Read the target file(s) end to end before proposing anything.
2. Read neighboring files to learn conventions — imports, error handling, naming.
3. Output a **refactor plan** before writing code:
   ```
   ## Plan
   - [ ] Extract X from Y into new file Z
   - [ ] Rename `foo` → `parseFoo` to reflect what it returns
   - [ ] Remove dead branch handling `LEGACY_MODE` (flag retired Q1 2024 per CHANGELOG)
   
   ## Behavior-preserving? Yes, with one note:
   - Log line at line 47 will move from `handleRequest` to `parseFoo`. Output identical, but if log search filters on the function name, that filter needs updating.
   ```
4. Make the changes. Keep edits minimal and obvious — one logical change per edit.
5. After the refactor, **state what to verify**: run tests, run linter, eyeball N specific behaviors.

## Anti-patterns to avoid

- **Refactor + feature in one pass.** If asked to "refactor and also add X", split it: refactor first (no behavior change, verify), then add X. Mixed changes are nearly impossible to review safely.
- **Over-abstraction.** Extracting a single-call-site function "in case we need it later" usually makes code harder to read. Wait for the second caller.
- **Renaming based on personal preference.** `getUserData` → `fetchUserData` is taste, not improvement. Only rename if the name is actively misleading.
- **Silent semantic shifts.** `Array.forEach` → `for...of` looks innocuous; it changes how `await` and early-return behave. Flag these.

## Examples

**Example — Plan output:**
> ## Plan
> - Extract pagination logic from `listOrders` (lines 34–78) into `paginate(query, opts)` in `lib/pagination.ts`
> - `listOrders` becomes 12 lines and calls `paginate`
> - No public API change
>
> ## Behavior-preserving? Yes.
> One small note: the existing code computed `offset` lazily inside the loop; the extraction computes it upfront. Same value, computed once instead of N times. This is technically a behavior change (perf, not correctness) — flagging in case it matters.

**Example — Pushback:**
> User: "DRY up these three handlers, they all look the same."
> Response: "Looked at them — they share the *shape* (validate, fetch, respond) but the validation and fetch logic differ meaningfully. Collapsing them into a generic handler would require passing 4–5 callbacks and the result reads worse than the duplication. I'd leave them. Happy to extract the common error-mapping into a helper if that's useful — that piece is genuinely duplicated."
