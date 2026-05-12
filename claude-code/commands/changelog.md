---
description: Generate a Keep-a-Changelog entry for the unreleased changes or a specified version range
argument-hint: "[optional: range like v1.4.0..HEAD]"
---

Generate or update the CHANGELOG.

Steps:
1. If `$ARGUMENTS` is a range, use it. Else use `<last-tag>..HEAD` (find last tag with `git describe --tags --abbrev=0`).
2. Gather inputs:
   - `git log <range> --oneline`
   - Merged PR titles (parse from commit messages like "Merge pull request #N from ...")
   - `git diff <range> --stat` for shape of changes
   - For breaking changes, scan diffs of public API files (route definitions, exported signatures, schema files)
3. Read the existing `CHANGELOG.md` (create if absent) to match format.
4. Group entries under the Keep-a-Changelog buckets: **Added**, **Changed**, **Deprecated**, **Removed**, **Fixed**, **Security**.
5. Write entries from the consumer's perspective. "Added webhook retries" — not "Refactored EventDispatcher".
6. Tag breaking changes with **BREAKING:** in bold.
7. Each entry references its PR/issue: `(#412)`.
8. Show the proposed `## [Unreleased]` (or version) section and ask before writing.

Skip: every-commit logs, "bumped version" entries, internal refactor noise that doesn't affect consumers.
