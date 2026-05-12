# ai-code-skills

A curated collection of **AI Skills, slash commands, and editor rules** that help developers manage their code smoothly — across code review, refactoring, testing, documentation, dependency hygiene, and git workflows.

Works with **Claude (Skills + Claude Code)**, **Cursor**, and **Windsurf**. Pick the format your tooling supports — the underlying instructions are the same.

---

## What's inside

| Area | What the skill does |
|---|---|
| **Code review & PRs** | Generates structured review comments, drafts PR descriptions, summarizes diffs |
| **Refactor & cleanup** | Identifies dead code, suggests extractions, modernizes idioms safely |
| **Testing & debugging** | Writes missing tests, reproduces bugs, traces stack flows |
| **Docs & changelogs** | Generates READMEs, JSDoc/TSDoc/docstrings, Keep-a-Changelog entries |
| **Dependency & security audits** | Audits `package.json` / `requirements.txt` / `pyproject.toml`, flags CVEs, suggests upgrades |
| **Git workflow** | Conventional commits, branch naming, interactive rebase plans, semantic merge prep |

---

## Repository layout

```
ai-code-skills/
├── skills/                      # Anthropic-format Skills (SKILL.md folders)
│   ├── code-review/
│   ├── refactor-cleanup/
│   ├── test-debug/
│   ├── docs-changelog/
│   ├── deps-security/
│   └── git-workflow/
├── claude-code/
│   ├── commands/                # Claude Code slash commands (/review, /commit, etc.)
│   └── agents/                  # Claude Code subagents (specialized roles)
├── cursor-rules/                # .mdc rule files for Cursor
├── windsurf-rules/              # .windsurfrules for Windsurf
└── .github/workflows/           # Lint + validate skill manifests on PR
```

---

## Installation

### 1. Anthropic Skills (Claude.ai, Claude Code, API)

Each folder under `skills/` is a self-contained Skill. Install one of three ways:

**Claude.ai / Claude apps** — zip the folder and upload via Settings → Capabilities → Skills.

**Claude Code** — clone into your project:
```bash
git clone https://github.com/<you>/ai-code-skills.git .claude/skills-source
ln -s .claude/skills-source/skills .claude/skills
```

**API** — reference the skill folder path when invoking the Skills feature.

### 2. Claude Code slash commands & subagents

```bash
# From your project root
cp -r ai-code-skills/claude-code/commands/* .claude/commands/
cp -r ai-code-skills/claude-code/agents/* .claude/agents/
```

Then in Claude Code: `/review`, `/commit`, `/changelog`, etc.

### 3. Cursor

Copy `.mdc` files into `.cursor/rules/` at your project root. Cursor auto-loads them based on glob patterns defined in each file's frontmatter.

```bash
mkdir -p .cursor/rules && cp ai-code-skills/cursor-rules/*.mdc .cursor/rules/
```

### 4. Windsurf

Concatenate or symlink the rules files into `.windsurfrules` at your project root.

```bash
cat ai-code-skills/windsurf-rules/*.md > .windsurfrules
```

---

## Audience

Designed to be useful at every scale:

- **Solo devs & indie hackers** — get review/test/docs help without a teammate
- **Startups** — establish lightweight engineering conventions early
- **Enterprise teams** — drop in as a baseline; extend with internal references
- **OSS maintainers** — automate PR triage, changelog drafting, CONTRIBUTING enforcement

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md). The short version: each new skill needs a `SKILL.md` with valid YAML frontmatter (`name`, `description`), a description that includes both *what it does* and *when to trigger it*, and ideally 2–3 example prompts in a `references/examples.md` file.

## License

MIT.
