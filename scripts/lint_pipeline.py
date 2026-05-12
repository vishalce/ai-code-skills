#!/usr/bin/env python3
"""
Lint CI/CD pipeline configs for structural hygiene.

Scans known pipeline files in the given paths (or repo-wide by default) and reports:
  - missing header comment block (purpose / runtime / required secrets / verified-on)
  - third-party action references not pinned to a 40-char commit SHA (GitHub Actions)
  - missing top-level `permissions:` block (GitHub Actions)
  - shell steps without `set -euo pipefail`
  - CircleCI orbs on floating major versions (e.g. `@4` instead of `@4.1.3`)

This is structural linting. For security findings, use `audit_pipeline.py`.

Usage:
  python3 scripts/lint_pipeline.py                       # scan repo from CWD
  python3 scripts/lint_pipeline.py path/to/file.yml      # scan one file
  python3 scripts/lint_pipeline.py path/to/dir           # scan a directory

Exit codes:
  0  OK — no findings
  1  Findings — see stdout for details
  2  Usage / environment error
"""

from __future__ import annotations

import fnmatch
import re
import sys
from dataclasses import dataclass
from pathlib import Path


# Patterns that identify a pipeline file by path (relative to repo root or a passed path).
PIPELINE_GLOBS = [
    ".github/workflows/*.yml",
    ".github/workflows/*.yaml",
    "**/Jenkinsfile",
    "**/Jenkinsfile.*",
    ".drone.yml",
    ".drone.yaml",
    ".circleci/config.yml",
    ".circleci/config.yaml",
]

HEADER_KEYS = ("Purpose:", "Runtime:", "Required secrets:", "verified-on:")

# Third-party action: anything that is NOT one of these first-party prefixes.
FIRSTPARTY_ACTION_OWNERS = {"actions", "github", "docker"}

GHA_USES_RE = re.compile(r"^\s*-?\s*uses:\s*([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+)@([A-Za-z0-9._-]+)")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
CIRCLECI_ORB_RE = re.compile(r"^\s*([A-Za-z0-9_-]+):\s*([A-Za-z0-9_-]+/[A-Za-z0-9_-]+)@([A-Za-z0-9._-]+)")


@dataclass
class Finding:
    path: Path
    line: int
    rule: str
    message: str


def detect_platform(path: Path) -> str:
    name = path.name
    parts = path.parts
    if "workflows" in parts and any(p == ".github" for p in parts):
        return "github-actions"
    if name == "Jenkinsfile" or name.startswith("Jenkinsfile."):
        return "jenkins"
    if name in (".drone.yml", ".drone.yaml"):
        return "drone"
    if "circleci" in parts and name.startswith("config.yml"):
        return "circleci"
    if name in ("config.yml", "config.yaml") and ".circleci" in parts:
        return "circleci"
    return "unknown"


def check_header(path: Path, text: str) -> list[Finding]:
    """Header comment with purpose / runtime / required secrets / verified-on at the top of the file."""
    head = "\n".join(text.splitlines()[:30])
    missing = [k for k in HEADER_KEYS if k not in head]
    if missing:
        return [Finding(path, 1, "header", f"missing header keys: {', '.join(missing)}")]
    return []


def check_gha_action_pinning(path: Path, text: str) -> list[Finding]:
    """Third-party GHA actions must be pinned to a 40-char SHA."""
    findings: list[Finding] = []
    for idx, line in enumerate(text.splitlines(), 1):
        m = GHA_USES_RE.match(line)
        if not m:
            continue
        ref, version = m.group(1), m.group(2)
        # Skip local actions (./.github/...) and docker:// scheme — those follow different rules.
        if ref.startswith("./") or ref.startswith("docker://"):
            continue
        owner = ref.split("/", 1)[0]
        if owner in FIRSTPARTY_ACTION_OWNERS:
            # First-party tag is acceptable; org policy may require SHA — flag as info elsewhere.
            continue
        if not SHA_RE.match(version):
            findings.append(
                Finding(
                    path,
                    idx,
                    "pinning",
                    f"third-party action {ref}@{version} is not pinned to a 40-char commit SHA",
                )
            )
    return findings


def check_gha_permissions(path: Path, text: str) -> list[Finding]:
    """GitHub Actions workflow root should declare `permissions:`."""
    if "permissions:" not in text:
        return [Finding(path, 1, "permissions", "no top-level `permissions:` block — inherits repo default (often write-all)")]
    # If present at workflow root but set to `write-all`, that's a finding.
    for idx, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("permissions:") and "write-all" in stripped:
            return [Finding(path, idx, "permissions", "`permissions: write-all` defeats least-privilege")]
    return []


def check_shell_pipefail(path: Path, text: str) -> list[Finding]:
    """Multi-line shell steps should start with `set -euo pipefail`."""
    findings: list[Finding] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        # Look for `run: |` or `commands:` blocks.
        if stripped in ("run: |", "run: |-", "commands:") or stripped.endswith("run: |"):
            indent = len(line) - len(line.lstrip())
            # Scan the next few lines of the block.
            block_lines: list[str] = []
            for j in range(i + 1, min(i + 10, len(lines))):
                if lines[j].strip() == "":
                    continue
                line_indent = len(lines[j]) - len(lines[j].lstrip())
                if line_indent <= indent:
                    break
                block_lines.append(lines[j])
            if block_lines and not any("set -euo pipefail" in bl or "set -e" in bl for bl in block_lines[:3]):
                # Only flag if the block has more than a single command (single commands don't need it).
                if len(block_lines) > 1:
                    findings.append(
                        Finding(path, i + 1, "pipefail", "multi-command shell block missing `set -euo pipefail`")
                    )
        i += 1
    return findings


def check_circleci_orbs(path: Path, text: str) -> list[Finding]:
    """CircleCI orbs should be pinned to exact patch version, not floating major."""
    findings: list[Finding] = []
    in_orbs_block = False
    orbs_indent = 0
    for idx, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped == "orbs:":
            in_orbs_block = True
            orbs_indent = len(line) - len(line.lstrip())
            continue
        if in_orbs_block:
            if line and not line.startswith(" ") and not line.startswith("\t"):
                in_orbs_block = False
                continue
            line_indent = len(line) - len(line.lstrip())
            if line and line_indent <= orbs_indent and stripped:
                in_orbs_block = False
                continue
            m = CIRCLECI_ORB_RE.match(line)
            if m:
                _, _, version = m.group(1), m.group(2), m.group(3)
                # Heuristic: a fully-pinned orb version has the form X.Y.Z.
                if not re.match(r"^\d+\.\d+\.\d+$", version):
                    findings.append(
                        Finding(path, idx, "pinning", f"CircleCI orb pinned to non-exact version `@{version}` — pin to X.Y.Z")
                    )
    return findings


PLATFORM_CHECKS = {
    "github-actions": [check_header, check_gha_action_pinning, check_gha_permissions, check_shell_pipefail],
    "jenkins": [check_header, check_shell_pipefail],
    "drone": [check_header, check_shell_pipefail],
    "circleci": [check_header, check_circleci_orbs, check_shell_pipefail],
}


def gather_files(targets: list[str]) -> list[Path]:
    """Resolve user-supplied targets (paths or globs) into a list of pipeline files."""
    out: set[Path] = set()
    if not targets:
        targets = ["."]
    for t in targets:
        p = Path(t)
        if p.is_file():
            out.add(p.resolve())
            continue
        base = p if p.is_dir() else Path(".")
        for pattern in PIPELINE_GLOBS:
            for match in base.rglob("*"):
                if match.is_file() and fnmatch.fnmatch(str(match), f"*{pattern}*"):
                    # Final guard: confirm it's a recognized pipeline file
                    if detect_platform(match) != "unknown":
                        out.add(match.resolve())
    return sorted(out)


def main(argv: list[str]) -> int:
    targets = argv[1:]
    files = gather_files(targets)
    if not files:
        print("no pipeline files found", file=sys.stderr)
        return 2

    all_findings: list[Finding] = []
    for f in files:
        platform = detect_platform(f)
        checks = PLATFORM_CHECKS.get(platform, [check_header])
        try:
            text = f.read_text(encoding="utf-8")
        except OSError as e:
            print(f"could not read {f}: {e}", file=sys.stderr)
            continue
        for check in checks:
            all_findings.extend(check(f, text))

    if not all_findings:
        print(f"OK: {len(files)} pipeline file(s) linted, no findings")
        return 0

    by_file: dict[Path, list[Finding]] = {}
    for f in all_findings:
        by_file.setdefault(f.path, []).append(f)
    for path, findings in sorted(by_file.items()):
        print(f"\n{path}")
        for fnd in findings:
            print(f"  {path.name}:{fnd.line}  [{fnd.rule}]  {fnd.message}")
    print(f"\nFAILED: {len(all_findings)} finding(s) across {len(by_file)} file(s)")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
