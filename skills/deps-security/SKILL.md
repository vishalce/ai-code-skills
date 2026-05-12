---
name: deps-security
description: Audits project dependencies for outdated versions, known CVEs, unused packages, license conflicts, and supply-chain risks. Use whenever the user mentions "audit", "vulnerabilities", "CVE", "outdated packages", "npm audit", "pip audit", "dependency review", "supply chain", "should I upgrade X", "is X safe", or shares a package.json / requirements.txt / pyproject.toml / Cargo.toml / go.mod and asks about its health. Produces prioritized findings with concrete upgrade or removal actions.
---

# Dependency & Security Audit

Audit a project's dependencies — find what's outdated, what's vulnerable, what's unused, what's risky — and turn that into a short, prioritized action list. Most "audit" output is unreadable noise; this skill's job is to filter it into things actually worth doing.

## When to use

Trigger when the user:
- Says "audit", "vulnerabilities", "CVE", "outdated", "supply chain"
- Shares a `package.json`, `package-lock.json`, `requirements.txt`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `Gemfile`, etc.
- Asks "is X safe to use?" or "should I upgrade X?"
- Asks about license compatibility
- Asks to interpret `npm audit` / `pip audit` / `cargo audit` / `osv-scanner` output

## What to check

Run through these categories. For each, surface only what matters — don't dump raw tool output.

### 1. Known vulnerabilities (CVEs)

The highest-priority category. For each finding:
- **Severity** (Critical / High / Medium / Low — use the advisory's rating, not your own)
- **Direct or transitive** — is it a package the project imports, or a dependency-of-a-dependency?
- **Reachable?** — does the project actually call the vulnerable function? Many advisories are scary on paper but unreachable in practice. Don't overstate this — if you can't tell, say so.
- **Fix** — the version that resolves it, and whether the upgrade is a major bump (breaking) or a patch.

Sources to check or recommend:
- `npm audit` / `pnpm audit` / `yarn audit`
- `pip-audit` (PyPI), `safety check`
- `cargo audit` (Rust)
- `govulncheck` (Go)
- `bundler-audit` (Ruby)
- GitHub Dependabot alerts if available
- OSV.dev for cross-ecosystem lookups

### 2. Outdated packages

Not every outdated package is a problem. Prioritize:
- **High**: major versions behind on packages with active security work (frameworks, auth libs, crypto, HTTP clients, ORMs)
- **Medium**: any package > 12 months stale that's still maintained
- **Low / ignore**: minor or patch behind, no security implications, low blast radius

For each upgrade, note **breaking changes** by checking the changelog. Don't promise "safe to upgrade" without looking.

### 3. Unused dependencies

Dependencies that aren't imported anywhere are pure liability — install time, attack surface, license obligations, audit noise. Find them via:
- `depcheck` (Node)
- `pip-extra-reqs` and `pip-missing-reqs` (Python)
- Manual grep if no tool available

Flag suspects but don't unilaterally remove — some packages are loaded dynamically (plugins, drivers, CLI entry points).

### 4. Suspicious / supply-chain risk

Flag packages that:
- Have very low download counts but recent install (typosquatting risk — `expres`, `lodahs`, etc.)
- Were published within the last 30 days by a new maintainer of a previously stable package
- Have postinstall scripts in unexpected places
- Are scoped under a name that doesn't match the upstream org

These are heuristics — confirm before alarming.

### 5. License compatibility

If the project has a declared license, check that dependency licenses are compatible. The common rule:
- **MIT / BSD / Apache-2.0 / ISC** — broadly compatible with most projects
- **GPL / AGPL** — copyleft; flag if the host project isn't also GPL/AGPL or doesn't intend to be
- **Unlicense / WTFPL / CC0** — usually fine but some legal teams reject them
- **Custom / proprietary** — always flag

When in doubt, recommend the user run it past their legal/compliance contact. Don't render a verdict on a custom license — surface the text.

### 6. Lock file health

- Is there a lock file? (`package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `Pipfile.lock`, `poetry.lock`, `Cargo.lock`, `go.sum`) If not, recommend creating one.
- Is the lock file checked into version control? If not, flag it.
- Are there duplicated versions of the same package at different points in the tree? (Often resolvable with `npm dedupe` or resolutions.)

## Output format

Always output in this order — most actionable first:

```
## Critical
[Vulnerabilities that need fixing this week. Each entry: package, version, CVE, fix.]

## High priority
[Major-version-stale packages with security implications, high-severity CVEs without immediate fix, license red flags.]

## Medium priority
[Outdated but lower-risk packages, unused dependencies, lock file issues.]

## Notes
[Things worth knowing but not acting on: deprecated transitive dependencies you can't directly fix, advisories on packages you don't use the vulnerable code path of, etc.]

## Suggested commands
[Copy-pasteable upgrade commands, scoped to the highest-priority items only.]
```

## A specific anti-pattern to avoid

Don't write "run `npm audit fix --force`" as advice. That flag will happily install breaking major versions across the tree and leave the user with a broken build and no understanding of what changed. Recommend per-package upgrades with the breaking-change notes inline.

## Examples

**Example — Critical entry:**
> **`lodash@4.17.20`** — High severity prototype pollution (CVE-2020-8203 / GHSA-p6mc-m468-83gw). Used directly. Fixed in 4.17.21.
> Upgrade: `npm install lodash@^4.17.21` (no breaking changes within 4.x).

**Example — Pushback on noise:**
> User: "npm audit shows 47 vulnerabilities, fix them all."
> Response: "Looked at the report. Of the 47, 38 are in `node_modules/something-build-tool` and only affect builds run on the package author's machine, not yours. 6 more are duplicates. The actually-actionable ones are 3 — two patch bumps and one minor. Here's the short list..."
