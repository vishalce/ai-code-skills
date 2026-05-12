#!/usr/bin/env python3
"""
Scaffold a GitHub Actions workflow from a Jenkinsfile.

This is intentionally a SCAFFOLDER, not a transparent translator. Jenkins-to-GHA
migrations have too many platform-specific constructs (shared libraries, Groovy
script blocks, credential types, agent labels) for an automated translation to
be safe. This script:

  1. Parses the Jenkinsfile for declarative `stage('X') { steps { sh '...' } }` patterns.
  2. Emits a starter GHA workflow with one job per stage, sh blocks copied verbatim.
  3. Marks every uncertain value with `# CHECK:` so the user can verify before merging.
  4. Refuses to guess at things it can't translate (shared library calls, Groovy
     `script {}` blocks, agent labels) — emits a `# CHECK:` placeholder instead.

You are expected to hand-edit the output. The script's job is to save you the
typing, not to produce a finished workflow.

Usage:
  python3 scripts/migrate_jenkins_to_gha.py Jenkinsfile [-o .github/workflows/ci.yml]

Exit codes:
  0  scaffold produced
  1  parse error
  2  usage / file error
"""

from __future__ import annotations

import argparse
import re
import sys
import textwrap
from pathlib import Path
from datetime import date


STAGE_RE = re.compile(r"stage\(\s*['\"]([^'\"]+)['\"]\s*\)\s*\{", re.MULTILINE)
SH_RE = re.compile(r"sh\s*'''(.*?)'''|sh\s*\"\"\"(.*?)\"\"\"|sh\s*['\"]([^'\"]+)['\"]", re.DOTALL)
AGENT_LABEL_RE = re.compile(r"agent\s*\{\s*label\s*['\"]([^'\"]+)['\"]\s*\}")
TIMEOUT_RE = re.compile(r"timeout\(\s*time:\s*(\d+)\s*,\s*unit:\s*['\"](\w+)['\"]\s*\)")
WITHCREDENTIALS_RE = re.compile(r"withCredentials\s*\(\s*\[([^\]]+)\]\s*\)")
LIBRARY_RE = re.compile(r"@Library\(\s*['\"]([^'\"]+)['\"]\s*\)")
SCRIPT_BLOCK_RE = re.compile(r"\bscript\s*\{")


def find_stage_blocks(text: str) -> list[tuple[str, str]]:
    """Return [(stage_name, stage_body), ...] for each declarative `stage('X') { ... }`."""
    blocks: list[tuple[str, str]] = []
    for m in STAGE_RE.finditer(text):
        name = m.group(1)
        start = m.end()  # position after the opening `{`
        depth = 1
        i = start
        while i < len(text) and depth > 0:
            ch = text[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            i += 1
        if depth == 0:
            blocks.append((name, text[start:i - 1]))
    return blocks


def extract_sh_commands(stage_body: str) -> list[str]:
    """Return shell commands found inside a stage body, dedented and stripped of a leading `set -e*` line."""
    commands: list[str] = []
    for m in SH_RE.finditer(stage_body):
        cmd = m.group(1) or m.group(2) or m.group(3) or ""
        cmd = textwrap.dedent(cmd).strip("\n")
        # The scaffold output already prepends `set -euo pipefail` to each run block.
        # Drop a leading set -e* line from the source so we don't double it.
        lines = cmd.splitlines()
        if lines and re.match(r"^\s*set\s+-[eu]+o?\s*(pipefail)?\s*$", lines[0]):
            lines = lines[1:]
        cmd = "\n".join(lines).strip("\n")
        if cmd:
            commands.append(cmd)
    return commands


def slugify(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("-").lower()
    return s or "stage"


def detect_warnings(text: str) -> list[str]:
    """Detect Jenkins constructs that the scaffolder can't translate cleanly."""
    warnings: list[str] = []
    if LIBRARY_RE.search(text):
        warnings.append("Jenkinsfile imports a `@Library(...)` — shared library calls cannot be auto-translated. Replace each call manually with a composite action / reusable workflow / inline script.")
    if SCRIPT_BLOCK_RE.search(text):
        warnings.append("Jenkinsfile contains `script { ... }` (Groovy) blocks. These cannot be auto-translated; rewrite as bash or a JavaScript composite action.")
    if WITHCREDENTIALS_RE.search(text):
        warnings.append("Jenkinsfile uses `withCredentials(...)`. Translate each credentialsId to a `${{ secrets.NAME }}` reference; the user must recreate the secrets in the new repo. See the verification checklist in the output.")
    if AGENT_LABEL_RE.search(text):
        warnings.append("Jenkinsfile uses `agent { label '...' }`. The scaffold defaults to `ubuntu-latest`. Confirm or switch to a self-hosted runner with matching tooling.")
    return warnings


def build_workflow(jenkinsfile: Path, text: str) -> tuple[str, list[str]]:
    stages = find_stage_blocks(text)
    if not stages:
        return "", ["No `stage('X') { ... }` blocks found. Is this a declarative Jenkinsfile?"]

    warnings = detect_warnings(text)
    timeout_minutes = 30
    tm = TIMEOUT_RE.search(text)
    if tm:
        amount = int(tm.group(1))
        unit = tm.group(2).upper()
        if unit.startswith("MINUTE"):
            timeout_minutes = amount
        elif unit.startswith("HOUR"):
            timeout_minutes = amount * 60

    lines: list[str] = []
    lines.append(f"# .github/workflows/ci.yml")
    lines.append(f"# Purpose: scaffolded from {jenkinsfile.name} — REVIEW BEFORE USE.")
    lines.append(f"# Runtime: ubuntu-latest. CHECK: confirm the Jenkins agent's preinstalled tooling matches.")
    lines.append(f"# Required secrets: CHECK — see the original Jenkins credentialsIds and recreate as GH secrets.")
    lines.append(f"# verified-on: {date.today().isoformat()}  # CHECK: bump this after you verify the scaffold works end-to-end")
    lines.append("")
    lines.append("name: ci")
    lines.append("")
    lines.append("on:")
    lines.append("  push:")
    lines.append("    branches: [main]  # CHECK: adjust to your default branch")
    lines.append("  pull_request:")
    lines.append("")
    lines.append("permissions:")
    lines.append("  contents: read  # CHECK: add per-job permissions as needed (packages:write, id-token:write, etc.)")
    lines.append("")
    lines.append("concurrency:")
    lines.append("  group: ci-${{ github.ref }}")
    lines.append("  cancel-in-progress: ${{ github.event_name == 'pull_request' }}")
    lines.append("")
    lines.append("jobs:")

    for i, (stage_name, stage_body) in enumerate(stages):
        job_id = slugify(stage_name)
        needs = f"\n    needs: {slugify(stages[i - 1][0])}" if i > 0 else ""
        lines.append(f"  {job_id}:")
        lines.append(f"    name: {stage_name}")
        lines.append(f"    runs-on: ubuntu-latest  # CHECK: original Jenkins agent label")
        lines.append(f"    timeout-minutes: {timeout_minutes}")
        if needs:
            lines.append(needs.lstrip("\n    needs:").rstrip() + needs.split('needs:')[0] if False else f"    needs: {slugify(stages[i - 1][0])}")
        lines.append(f"    steps:")
        lines.append(f"      - uses: actions/checkout@CHECK  # v4.x.x — re-pin to current SHA")
        sh_cmds = extract_sh_commands(stage_body)
        if not sh_cmds:
            lines.append(f"      # CHECK: original stage had no `sh` step; translate manually.")
            lines.append(f"      - name: TODO {stage_name}")
            lines.append(f"        run: echo 'CHECK: translate this stage'")
        else:
            for j, cmd in enumerate(sh_cmds):
                step_name = f"{stage_name} step {j + 1}" if len(sh_cmds) > 1 else stage_name
                lines.append(f"      - name: {step_name}")
                lines.append(f"        run: |")
                lines.append(f"          set -euo pipefail")
                for cmd_line in cmd.splitlines():
                    lines.append(f"          {cmd_line}")
        lines.append("")

    return "\n".join(lines), warnings


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Scaffold a GitHub Actions workflow from a Jenkinsfile.")
    parser.add_argument("jenkinsfile", type=Path, help="Path to the source Jenkinsfile")
    parser.add_argument("-o", "--output", type=Path, default=None, help="Output path (default: stdout)")
    args = parser.parse_args(argv[1:])

    if not args.jenkinsfile.is_file():
        print(f"not a file: {args.jenkinsfile}", file=sys.stderr)
        return 2

    text = args.jenkinsfile.read_text(encoding="utf-8")
    workflow, warnings = build_workflow(args.jenkinsfile, text)

    if not workflow:
        for w in warnings:
            print(f"  - {w}", file=sys.stderr)
        return 1

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(workflow + "\n", encoding="utf-8")
        print(f"wrote scaffold: {args.output}", file=sys.stderr)
    else:
        print(workflow)

    if warnings:
        print("\n# CHECK — things this scaffolder could not translate:", file=sys.stderr)
        for w in warnings:
            print(f"#   - {w}", file=sys.stderr)
        print("\n# Re-read the workflow and resolve every `# CHECK:` marker before using.", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
