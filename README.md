# ai-code-skills

A curated collection of **AI Skills, slash commands, and editor rules** that help developers manage their code smoothly — across code review, refactoring, testing, documentation, dependency hygiene, git workflows, and CI/CD pipelines.

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
| **CI/CD pipeline authoring** | Drafts production-grade GitHub Actions / Jenkins / Drone / CircleCI / Argo CD configs with pinning, OIDC, least privilege baked in |
| **CI/CD debug** | Hypothesis-first RCA on failing pipelines from log + config — root cause, not symptom |
| **CI/CD review & audit** | Security audit of pipelines: supply chain, OIDC hygiene, secrets, permissions, Argo CD anti-patterns |
| **CI/CD migrate** | Jenkins ↔ GHA, CircleCI → GHA, Drone → GHA with translation table + verification checklist |
| **CI/CD optimize** | Cache strategy, parallelization, matrix tuning, runner sizing — ranked by likely time saved |
| **GitOps with Argo CD** | App-of-apps vs ApplicationSet, sync waves, progressive rollouts, drift detection, secret management |

---

## Supported CI/CD platforms

| Platform | Authoring | Debug | Audit | Migrate from | Templates |
|---|:---:|:---:|:---:|:---:|:---:|
| **GitHub Actions** | ✓ | ✓ | ✓ | (target) | ✓ |
| **Jenkins** | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Drone CI** | ✓ | ✓ | ✓ | ✓ | ✓ |
| **CircleCI** | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Argo CD (GitOps)** | ✓ | ✓ | ✓ | — | ✓ |

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
│   ├── git-workflow/
│   ├── cicd-config-author/      # Pipeline authoring (5 platforms)
│   ├── cicd-debug/              # Failure RCA
│   ├── cicd-review-audit/       # Pipeline security audit
│   ├── cicd-migrate/            # Cross-platform translation
│   ├── cicd-optimize/           # Speed + cost
│   └── gitops-argocd/           # Argo CD patterns
├── claude-code/
│   ├── commands/                # Slash commands (/review, /commit, /pipeline-review, ...)
│   └── agents/                  # Subagents (code-reviewer, cicd-reviewer, ...)
├── cursor-rules/                # .mdc rule files for Cursor
├── windsurf-rules/              # .windsurfrules for Windsurf
├── templates/                   # Battle-tested pipeline starters per platform
│   ├── github-actions/
│   ├── jenkins/
│   ├── drone/
│   ├── circleci/
│   └── argocd/
├── scripts/                     # Validators + linters
│   ├── validate_skills.py       # Validates SKILL.md frontmatter
│   ├── lint_pipeline.py         # Structural hygiene check across platforms
│   ├── audit_pipeline.py        # Security audit (companion to cicd-review-audit)
│   └── migrate_jenkins_to_gha.py # Jenkinsfile → GHA scaffolder (not a transparent translator)
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
