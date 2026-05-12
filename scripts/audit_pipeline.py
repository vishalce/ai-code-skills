#!/usr/bin/env python3
"""
Security audit for CI/CD pipeline configs.

Scans pipeline files and reports security-focused findings:
  - workflow-level `env:` blocks containing references to `${{ secrets.* }}` (leak surface)
  - `pull_request_target` workflows that check out the PR head ref AND run install/build
  - GHA workflows with `permissions: write-all`
  - long-lived static cloud credentials referenced where OIDC is available
  - Argo CD Application manifests that auto-prune + selfHeal without comment markers
  - plaintext Kubernetes `Secret` manifests in argocd/** paths

This is the *pipeline* audit. For application dependency CVEs use the existing
`deps-security` skill / `/audit` command.

Usage:
  python3 scripts/audit_pipeline.py                  # scan repo from CWD
  python3 scripts/audit_pipeline.py path/to/file.yml # one file
  python3 scripts/audit_pipeline.py path/to/dir      # a directory

Exit codes:
  0  no findings
  1  one or more findings (review stdout)
  2  usage / environment error
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path


PIPELINE_GLOBS = [
    ".github/workflows/*.yml",
    ".github/workflows/*.yaml",
    "**/Jenkinsfile",
    "**/Jenkinsfile.*",
    ".drone.yml",
    ".drone.yaml",
    ".circleci/config.yml",
    ".circleci/config.yaml",
    "argocd/**/*.yaml",
    "argocd/**/*.yml",
]


@dataclass
class Finding:
    path: Path
    line: int
    severity: str  # critical | high | medium | note
    rule: str
    message: str


def detect_platform(path: Path) -> str:
    name = path.name
    parts = path.parts
    if "workflows" in parts and ".github" in parts:
        return "github-actions"
    if name == "Jenkinsfile" or name.startswith("Jenkinsfile."):
        return "jenkins"
    if name in (".drone.yml", ".drone.yaml"):
        return "drone"
    if name.startswith("config.yml") and ".circleci" in parts:
        return "circleci"
    if "argocd" in parts:
        return "argocd"
    return "unknown"


def audit_gha(path: Path, text: str) -> list[Finding]:
    findings: list[Finding] = []
    lines = text.splitlines()

    # `permissions: write-all`
    for idx, line in enumerate(lines, 1):
        if re.match(r"^\s*permissions:\s*write-all\s*$", line):
            findings.append(
                Finding(path, idx, "critical", "permissions", "`permissions: write-all` grants every scope")
            )

    # `pull_request_target` checking out PR head ref
    if "pull_request_target" in text:
        # Heuristic: look for actions/checkout with a ref that references the PR head
        for idx, line in enumerate(lines, 1):
            if "actions/checkout" in line:
                # peek at next few lines for `ref:` referencing pull_request.head
                window = "\n".join(lines[idx:idx + 8])
                if "pull_request.head" in window or "${{ github.event.pull_request.head" in window:
                    findings.append(
                        Finding(
                            path, idx, "critical", "fork-checkout",
                            "`pull_request_target` checks out PR head ref — fork code can pwn base repo secrets",
                        )
                    )

    # Workflow-level env: with secrets — leak surface
    # Look for `^env:` at column 0 within the first ~20 lines, then secrets refs in its block.
    in_workflow_env = False
    workflow_env_start = 0
    for idx, line in enumerate(lines, 1):
        if line.startswith("env:"):
            in_workflow_env = True
            workflow_env_start = idx
            continue
        if in_workflow_env:
            if line and not line.startswith(" ") and not line.startswith("\t") and line.strip():
                in_workflow_env = False
                continue
            if "${{ secrets." in line or "${{secrets." in line:
                findings.append(
                    Finding(
                        path, idx, "high", "secrets-in-env",
                        "workflow-level `env:` contains a secret — scope to the job or step instead",
                    )
                )

    # Static AWS keys where OIDC is available
    if re.search(r"AWS_(ACCESS_KEY_ID|SECRET_ACCESS_KEY)", text):
        # Only flag if the workflow doesn't ALSO use OIDC.
        if "aws-actions/configure-aws-credentials" in text and "role-to-assume" in text:
            pass  # using OIDC, no finding
        else:
            findings.append(
                Finding(path, 1, "high", "oidc-not-used",
                        "references AWS_ACCESS_KEY_ID/SECRET_ACCESS_KEY — prefer OIDC via configure-aws-credentials")
            )

    # echo $SECRET pattern
    for idx, line in enumerate(lines, 1):
        if re.search(r"echo\s+.*\$\{?\{?\s*secrets\.", line, re.IGNORECASE):
            findings.append(
                Finding(path, idx, "critical", "echo-secret",
                        "echoes a secret value to stdout — masking is best-effort, not a guarantee")
            )

    return findings


def audit_drone(path: Path, text: str) -> list[Finding]:
    findings: list[Finding] = []
    # Missing `trigger:` is a finding — pipeline runs on every event by default.
    # Heuristic: any document missing `trigger:` somewhere in its body.
    docs = re.split(r"^---\s*$", text, flags=re.MULTILINE)
    for di, doc in enumerate(docs):
        if "kind: pipeline" in doc and "trigger:" not in doc:
            findings.append(
                Finding(path, 1, "high", "missing-trigger",
                        f"drone pipeline (document {di + 1}) has no `trigger:` block — runs on every event")
            )
    # privileged: true — flag for review
    for idx, line in enumerate(text.splitlines(), 1):
        if re.match(r"^\s*privileged:\s*true", line):
            findings.append(
                Finding(path, idx, "medium", "privileged",
                        "`privileged: true` — confirm this step actually needs kernel access")
            )
    return findings


def audit_argocd(path: Path, text: str) -> list[Finding]:
    findings: list[Finding] = []
    lines = text.splitlines()

    # Plaintext Secret manifest in argocd path
    if re.search(r"^kind:\s*Secret\b", text, re.MULTILINE):
        # Tolerate SealedSecret, ExternalSecret, and ESO-managed Secret
        if not re.search(r"^kind:\s*(SealedSecret|ExternalSecret)\b", text, re.MULTILINE):
            findings.append(
                Finding(path, 1, "critical", "plaintext-secret",
                        "plain `Secret` manifest in argocd path — use SealedSecret / ExternalSecret / SOPS")
            )

    # automated prune + selfHeal without explanation
    if "prune: true" in text and "selfHeal: true" in text:
        # Annotation or comment acknowledging this isn't a first deploy
        if not re.search(r"#.*(reconciled|stage 3|steady state|safe)", text, re.IGNORECASE):
            findings.append(
                Finding(path, 1, "high", "argo-auto-destructive",
                        "`automated.prune: true` + `selfHeal: true` — confirm this Application has reconciled cleanly once")
            )

    # targetRevision pointing at HEAD or a branch
    for idx, line in enumerate(lines, 1):
        m = re.match(r"^\s*targetRevision:\s*(.+)$", line)
        if m:
            rev = m.group(1).strip().strip("'").strip('"')
            if rev in ("HEAD", "main", "master", "develop") or rev.startswith("release/"):
                findings.append(
                    Finding(path, idx, "high", "mutable-revision",
                            f"`targetRevision: {rev}` is mutable — pin to commit SHA or signed tag")
                )

    # spec.project: default
    if re.search(r"^\s*project:\s*default\s*$", text, re.MULTILINE):
        findings.append(
            Finding(path, 1, "medium", "default-project",
                    "`spec.project: default` permits any source/destination — consider a restrictive AppProject")
        )

    return findings


PLATFORM_AUDITORS = {
    "github-actions": audit_gha,
    "drone": audit_drone,
    "argocd": audit_argocd,
}


def gather_files(targets: list[str]) -> list[Path]:
    out: set[Path] = set()
    if not targets:
        targets = ["."]
    for t in targets:
        p = Path(t)
        if p.is_file():
            out.add(p.resolve())
            continue
        base = p if p.is_dir() else Path(".")
        for match in base.rglob("*"):
            if not match.is_file():
                continue
            if detect_platform(match) != "unknown":
                out.add(match.resolve())
    return sorted(out)


SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "note": 3}


def main(argv: list[str]) -> int:
    files = gather_files(argv[1:])
    if not files:
        print("no pipeline files found", file=sys.stderr)
        return 2

    all_findings: list[Finding] = []
    for f in files:
        platform = detect_platform(f)
        auditor = PLATFORM_AUDITORS.get(platform)
        if not auditor:
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except OSError as e:
            print(f"could not read {f}: {e}", file=sys.stderr)
            continue
        all_findings.extend(auditor(f, text))

    if not all_findings:
        print(f"OK: {len(files)} pipeline file(s) audited, no findings")
        return 0

    all_findings.sort(key=lambda x: (SEVERITY_ORDER.get(x.severity, 4), str(x.path), x.line))
    current_sev = None
    for f in all_findings:
        if f.severity != current_sev:
            current_sev = f.severity
            print(f"\n## {current_sev.upper()}")
        print(f"  {f.path.name}:{f.line}  [{f.rule}]  {f.message}  ({f.path})")
    print(f"\nFAILED: {len(all_findings)} finding(s)")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
