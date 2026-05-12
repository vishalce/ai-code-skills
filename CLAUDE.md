# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A content repository — not an application. It ships AI prompts/instructions in four parallel formats, all aimed at the same set of developer tasks (review, refactor, test/debug, docs, deps/security, git workflow):

- `skills/<topic>/SKILL.md` — Anthropic-format Skills (Claude.ai, Claude Code, API)
- `claude-code/commands/*.md` — Claude Code slash commands (`/review`, `/commit`, `/test`, `/refactor`, `/docs`, `/audit`, `/changelog`)
- `claude-code/agents/*.md` — Claude Code subagents (`code-reviewer`, `debugger`, `security-auditor`)
- `cursor-rules/*.mdc` — Cursor rules with glob-matched activation
- `windsurf-rules/windsurfrules-combined.md` — single concatenated Windsurf rules file

The six topic areas in `skills/` are the canonical source of intent. Commands/agents/cursor-rules/windsurf-rules are format-specific projections of the same guidance — when editing one, check whether sibling formats need the same change to stay consistent.

## Commands

There is no build, no test framework, no package manifest. The only executable check is the skill validator:

```bash
python3 scripts/validate_skills.py     # requires PyYAML (pip install pyyaml)
```

Run it after touching anything under `skills/`. It enforces: valid YAML frontmatter, `name` + `description` keys, description ≥ 40 chars, body ≥ 100 chars. Exit 0 = pass, 1 = validation failure, 2 = environment problem (missing PyYAML or no skills dir).

## Authoring conventions

### The `description` field is the trigger

For every Skill, subagent, and command, the `description` field is the primary triggering signal — not a summary. It must state **what the artifact does AND when to invoke it**, with concrete user phrases ("review this", "PR review", "look at my code"). Phrasing should be on the pushy side ("Use whenever the user mentions...") because these tend to under-trigger. When adding or editing a description, preserve the explicit list of trigger phrases — it's load-bearing, not filler.

### Format-specific frontmatter

Each artifact type has its own frontmatter contract — don't mix them:

- **Skills** (`skills/*/SKILL.md`): `name`, `description`
- **Commands** (`claude-code/commands/*.md`): `description`, `argument-hint`. Body references `$ARGUMENTS`.
- **Subagents** (`claude-code/agents/*.md`): `name`, `description`, `tools` (YAML list)
- **Cursor rules** (`cursor-rules/*.mdc`): `description`, `globs`, `alwaysApply`

### Body style

- Imperative voice ("Output the review", not "The skill outputs the review")
- Severity tags are uppercase keywords inside content (`BLOCKER`, `MAJOR`, `MINOR`, `NIT`, `PRAISE`); surrounding prose stays normal case
- One verb per command — keep them focused (`/review`, `/commit`, never `/do-everything`)
- Skills should stay under ~500 lines; long-form content goes in `skills/<topic>/references/` and is linked from `SKILL.md`
- Include 2–3 concrete input → output examples; explain *why* rules matter rather than just asserting MUSTs

### What won't be accepted

Per `CONTRIBUTING.md`: skills that overlap heavily with an existing one (extend instead), skills that bake one project's conventions into universal rules (keep them general), or AI-generated descriptions without human review.

## Cross-format consistency

When adding a new capability, the typical fan-out is: write or extend the canonical `skills/<topic>/SKILL.md`, then mirror the change into the matching `claude-code/commands/`, `claude-code/agents/`, `cursor-rules/`, and the appropriate section of `windsurf-rules/windsurfrules-combined.md`. The README's capability table should also reflect any new category.
