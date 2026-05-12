---
description: Add or update documentation — README, JSDoc/docstrings, or ADRs
argument-hint: "[readme | docstrings <file> | adr <decision>]"
---

Generate or update documentation.

Parse `$ARGUMENTS`:
- `readme` — write/update the project README following the 5-section structure (what / why / install / quick start / where next).
- `docstrings <file>` — add docstrings (JSDoc/TSDoc/Python/etc. — match the file's language) to all exported symbols in the file. Use one-line summary, params, returns, throws, example.
- `adr <decision>` — create an ADR in `docs/adr/` (or wherever ADRs live) with Context / Decision / Consequences / Alternatives. Number it sequentially.

For any mode:
- Read existing docs first to match style and structure.
- Inline comments answer **why**, not **what**. Skip comments that restate the code.
- Use `TODO(name, ticket): description` format for TODOs — never bare `TODO`.
- For docstrings on exported APIs, always include an example if the function takes more than one argument or has non-obvious behavior.

Output a draft, ask for confirmation if it's substantial (more than ~50 lines), then write.
