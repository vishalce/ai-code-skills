# Contributing

Thanks for considering a contribution. This repo collects AI Skills, slash commands, and editor rules that help developers manage their code. Quality and consistency matter more than volume here — one well-tested skill beats five sloppy ones.

## Adding a new Skill

Every skill under `skills/` must include a `SKILL.md` with valid YAML frontmatter:

```yaml
---
name: skill-name
description: What the skill does AND when to trigger it. Both halves matter — the description is the primary triggering signal for the AI.
---
```

### Description requirements

The `description` field is the single most important part of a skill. It should:

1. **State what the skill does** in concrete terms ("Reviews diffs and outputs severity-tagged comments")
2. **State when to trigger it** with specific phrases users say ("Use when the user says 'review this', 'PR review', pastes a unified diff...")
3. **Be on the pushy side.** Skills tend to under-trigger. Phrasing like "Use whenever the user mentions..." beats "Can be used for..."

### Body requirements

The body of `SKILL.md` should:

- Use imperative voice ("Output the review", not "The skill outputs the review")
- Stay under ~500 lines; if longer, split into `references/` files and link from SKILL.md
- Include 2–3 concrete examples of input → output behavior
- Explain *why* important rules matter, not just state them as MUSTs

### Folder structure

```
skills/your-skill/
├── SKILL.md            (required)
├── references/         (optional — long-form docs Claude can load on demand)
│   └── examples.md
├── scripts/            (optional — executable helpers)
└── assets/             (optional — templates or fixtures)
```

## Adding a Claude Code command

Files in `claude-code/commands/` define slash commands. Format:

```markdown
---
description: One-line description for the slash-command picker
argument-hint: "[optional argument hint shown to user]"
---

[The body — instructions for what the command does. Reference $ARGUMENTS where needed.]
```

Keep commands focused — one verb per command. `/review`, `/commit`, `/test` — not `/do-everything`.

## Adding a Claude Code subagent

Files in `claude-code/agents/` define specialized subagents:

```markdown
---
name: agent-name
description: When to invoke this agent and what it does
tools: [Read, Grep, Glob, Bash, Edit]
---

[The system prompt for the subagent — its role, method, output structure, anti-patterns]
```

## Adding a Cursor rule

Files in `cursor-rules/` use `.mdc` extension and Cursor's frontmatter:

```markdown
---
description: One-line description
globs: ["**/*.ts", "**/*.tsx"]    # file patterns this rule applies to
alwaysApply: false                # true = always in context, false = glob-matched
---

[The rule body]
```

## Adding a Windsurf rule

Windsurf reads a single `.windsurfrules` file. Add your section to `windsurf-rules/windsurfrules-combined.md` with a clear `## Section` header, or create a standalone variant in the same folder.

## CI/CD content — the quality bar

CI/CD content (skills, commands, rules, templates) carries higher risk than the rest of the repo: a broken pipeline example doesn't just confuse the reader, it burns trust and can land in production.

**Non-negotiables for CI/CD additions:**

- **Templates must be correct.** Broken examples are worse than no examples. If you can't verify the template end-to-end on the platform it targets, don't add it — or mark every uncertain value with `# CHECK:` and call it explicitly a "scaffold".
- **Header block required** on every pipeline template:
  ```
  # Purpose: <one line — what this pipeline does>
  # Runtime: <runner, image, language version assumptions>
  # Required secrets: <names of secrets that must exist>
  # verified-on: YYYY-MM-DD
  ```
- **`# CHECK:` marker** for anything you're not 100% sure about — image digests, credential names, exact SHAs, deploy targets. A future reader will trust a `# CHECK:` marker; they won't trust a confidently-wrong default value.
- **Security defaults are non-negotiable.** Every template applies: SHA-pinning of third-party actions/orbs/plugins, least-privilege permissions, OIDC over static creds, no secrets in workflow-level `env:`, encrypted-only secrets for Argo CD. See `cursor-rules/cicd-security.mdc` for the full list.
- **Skill descriptions must list trigger phrases** specifically: "Use whenever the user says 'X', 'Y', 'Z'..." with concrete examples. The CI/CD skills tend to under-trigger if descriptions are abstract.
- **Cross-format consistency.** A new CI/CD concept added to a skill should be mirrored into the matching command (`claude-code/commands/`), subagent (`claude-code/agents/`), cursor rule (`cursor-rules/cicd-*.mdc`), and Windsurf section (`windsurf-rules/windsurfrules-combined.md` under `## CI/CD Pipelines`).

**Specific things that get rejected:**

- Pipeline templates with floating action references (no SHA pin) — even on first-party `actions/*`, prefer SHA + version comment for templates other people will copy.
- Examples that reproduce official-docs verbatim — those are pedagogical, not production-ready (often omit `permissions:`, pinning, timeouts).
- "Best practices" sections in skills without a named failure mode — if you can't say what goes wrong when the practice is violated, it's not a rule worth writing.
- Argo CD `Application` examples with `automated.prune: true` + `selfHeal: true` and no comment about the staged-rollout caveat. Day-one auto-prune is a silent foot-cannon.
- Jenkinsfile examples mixing declarative and scripted syntax in one `pipeline {}` block. Pick one.

**Verifying your CI/CD additions:**

```bash
python3 scripts/validate_skills.py          # frontmatter + body checks (all skills)
python3 scripts/lint_pipeline.py templates/ # structural hygiene on pipeline templates
python3 scripts/audit_pipeline.py templates/ # security audit (templates will surface intentional placeholders)
```

The audit script will surface findings on templates because templates have intentional placeholders (`spec.project: default`, `# CHECK:` markers). That's expected. What's *not* expected: findings on something you didn't mean to include.

---

## Style guide

- **Direct, specific, kind.** Same tone the skills themselves recommend.
- **Examples over abstractions.** Show one good output, then one anti-pattern.
- **No filler.** If a sentence doesn't add information, cut it.
- **Lowercase keywords.** `BLOCKER`, `MAJOR`, etc. when used as severity tags, but body prose stays normal.

## Pull request process

1. Fork and branch (`feat/your-skill-name`).
2. Add the skill/command/rule + an entry in the README's table if it's a new category.
3. Open a PR with a description that includes 2–3 example prompts the skill should trigger on.
4. Maintainers will sanity-check the triggering description and the output structure.

## What we won't merge

- Skills that overlap heavily with an existing one (extend the existing one instead)
- Skills that include malware, exploit code, or anything that would surprise users in their stated intent
- Skills generated by an AI without human review — the descriptions especially need human judgment
- Skills that bake in a single project's conventions as universal rules (factor those out, keep the skill general)
