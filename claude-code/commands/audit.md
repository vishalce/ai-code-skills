---
description: Audit project dependencies for CVEs, outdated packages, and supply-chain risks
argument-hint: "[optional: 'quick' for headline issues only, 'full' for everything]"
---

Audit the project's dependencies and produce a prioritized action list.

Steps:
1. Detect the ecosystem(s) from lock files and manifests: `package.json`, `requirements.txt`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `Gemfile`, etc.
2. Run the appropriate audit tools (don't install them; report if missing):
   - Node: `npm audit --json` or `pnpm audit --json` or `yarn npm audit`
   - Python: `pip-audit` or `safety check`
   - Rust: `cargo audit`
   - Go: `govulncheck ./...`
   - Ruby: `bundler-audit`
3. For "outdated" info, run `npm outdated --json` / `pip list --outdated` / `cargo outdated` / etc.
4. For unused deps (Node only, if available): `npx depcheck`.

Output in this order — most actionable first:

```
## Critical
[CVEs needing fixes this week. Each: package, version, advisory ID, fix version.]

## High priority
[Major-stale security-sensitive packages, license red flags.]

## Medium priority  
[Outdated lower-risk packages, unused deps, lock-file issues.]

## Notes
[Unreachable advisories, deprecated transitives, etc.]

## Suggested commands
[Per-package upgrade commands, scoped to highest priority.]
```

Do not suggest `npm audit fix --force` or equivalent blunt-instrument commands. Recommend per-package upgrades with breaking-change notes.

If `$ARGUMENTS` is `quick`, only output the Critical and High sections.
