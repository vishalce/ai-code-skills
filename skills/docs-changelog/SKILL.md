---
name: docs-changelog
description: Generates and maintains code documentation — READMEs, API docs, JSDoc/TSDoc/Python docstrings, inline comments, and Keep-a-Changelog-formatted CHANGELOG entries. Use whenever the user says "write a README", "add docs", "document this", "add JSDoc", "add docstrings", "write a changelog", "update CHANGELOG", "what changed since v...", or asks for usage examples, API reference, or migration notes. Also use when generating CONTRIBUTING, ARCHITECTURE, or similar repo-level docs.
---

# Docs & Changelog

Docs that go unread are wasted; docs that mislead are worse than none. Aim for the shortest doc that lets the reader do the thing.

## When to use

Trigger when the user:
- Asks to write or update a README, CONTRIBUTING, ARCHITECTURE, or similar
- Asks to add JSDoc/TSDoc/docstrings/godoc/rustdoc to a file or function
- Asks for a CHANGELOG entry, release notes, or "what changed since v..."
- Asks for usage examples or an API reference
- Asks to document an architectural decision (ADR)

## READMEs

A README answers, in order:

1. **What is this?** (one sentence — what it does, who it's for)
2. **Why does it exist?** (the problem it solves — one short paragraph)
3. **How do I install it?** (copy-pasteable commands)
4. **How do I use it?** (the smallest example that does something useful)
5. **Where do I go next?** (links to API docs, examples, CONTRIBUTING)

That's it for most projects. Don't pad with badges, philosophy, or "Table of Contents" until the project earns them.

### README template

```markdown
# project-name

One sentence saying what this is.

## What it does

2–4 sentences. The problem. Who it's for. The shape of the solution.

## Install

\`\`\`bash
npm install project-name
# or
pip install project-name
\`\`\`

## Quick start

\`\`\`ts
import { thing } from 'project-name';

const result = thing({ ... });
\`\`\`

## Docs

- [Full API reference](./docs/api.md)
- [Examples](./examples/)
- [Contributing](./CONTRIBUTING.md)

## License

MIT (or whatever)
```

## Docstrings & inline comments

### Docstrings (JSDoc / TSDoc / Python / etc.)

Document every **exported** function, type, and constant. Internal helpers only need docs if the name doesn't carry the meaning.

A good docstring covers:
- **What** it does (one line, present tense, imperative-ish: "Parses a duration string into seconds.")
- **Parameters** — name, type, what each represents (skip if obvious from type)
- **Returns** — what comes back and in what shape
- **Throws / errors** — what errors are raised when
- **Example** — for anything non-trivial

```ts
/**
 * Parses a human-readable duration string into seconds.
 *
 * Accepts forms like "1h", "30m", "1h30m", "2d". Whitespace and case
 * are ignored. Negative durations are rejected.
 *
 * @param input - the duration string to parse
 * @returns the duration in seconds
 * @throws {RangeError} if the input is negative or unparseable
 *
 * @example
 * parseDuration("1h30m") // → 5400
 */
export function parseDuration(input: string): number { ... }
```

### Inline comments

Inline comments answer **why**, not **what**. The code says what it does; the comment says why it's that way.

- ✗ `// increment i` (says what — code already says this)
- ✗ `// loop through users` (says what)
- ✓ `// Stripe rate-limits at 100/sec; sleep keeps us under the threshold` (says why)
- ✓ `// HACK: server returns ISO strings but docs say epoch — remove when fixed` (says why, flags debt)

Use `TODO`, `FIXME`, `HACK`, `NOTE` tags consistently. A `TODO` without a name and a ticket reference is a `TODO` no one will ever do — write `// TODO(vishal, GBM-412): handle pagination`.

## Changelogs (Keep a Changelog format)

Use the [Keep a Changelog](https://keepachangelog.com) convention. Group entries under: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`.

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Multi-vendor support for the catalog API (#412)

### Fixed
- `SUMMER25` discount code now applies 25%, not 5% (#418)

## [1.4.0] - 2026-04-10

### Added
- Webhook retries with exponential backoff (#398)

### Changed
- **BREAKING**: `createOrder` now requires `vendorId` (#401)

### Security
- Bumped `axios` to 1.7.4 to address GHSA-... (#405)
```

### Entry-writing rules

- Write entries from the **consumer's** point of view, not the implementer's. "Added webhook retries" — not "Refactored EventDispatcher to use exponential backoff."
- Each entry references its PR or issue number.
- Breaking changes are **bold-tagged BREAKING** so they can't be missed.
- Don't list every commit. Group meaningfully.

### Generating from a diff

If the user asks "what changed since v1.4?", look at:
1. Commit messages between tags (`git log v1.4..HEAD --oneline`)
2. Merged PR titles
3. The actual diff for breaking signature/schema changes

Then group by the six Keep-a-Changelog buckets and dedupe overlapping commits.

## Architecture Decision Records (ADRs)

For significant decisions, suggest an ADR:

```markdown
# ADR-007: Switch from Laravel to NestJS for backend

**Status:** Accepted
**Date:** 2026-03-15

## Context
[The situation forcing the decision]

## Decision
[What was chosen]

## Consequences
[What changes — good, bad, and neutral]

## Alternatives considered
[What else was on the table and why it was rejected]
```

Number ADRs sequentially. Never delete them, even when superseded — add a new ADR that supersedes the old one and update the status.

## Tone

Docs are written for someone in a hurry who is mildly annoyed they have to read this. Be direct, use examples liberally, skip the marketing voice, and stop when the reader has what they need.
