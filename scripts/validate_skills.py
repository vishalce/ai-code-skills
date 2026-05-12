#!/usr/bin/env python3
"""
Validate every SKILL.md in skills/ has:
  - valid YAML frontmatter
  - required keys: name, description
  - description that's substantive (>= 40 chars)
  - body content beyond the frontmatter

Exit 0 on success, 1 on any failure.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML required: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)
SKILLS_DIR = Path(__file__).parent.parent / "skills"


def validate_skill(skill_md: Path) -> list[str]:
    """Return a list of error messages for this SKILL.md. Empty list = valid."""
    errors: list[str] = []
    text = skill_md.read_text(encoding="utf-8")

    match = FRONTMATTER_RE.match(text)
    if not match:
        return ["missing or malformed YAML frontmatter (expected --- ... --- block at top)"]

    raw_frontmatter, body = match.group(1), match.group(2)

    try:
        fm = yaml.safe_load(raw_frontmatter)
    except yaml.YAMLError as e:
        return [f"YAML parse error: {e}"]

    if not isinstance(fm, dict):
        return ["frontmatter must be a YAML mapping"]

    if "name" not in fm:
        errors.append("missing required key: name")
    elif not isinstance(fm["name"], str) or not fm["name"].strip():
        errors.append("name must be a non-empty string")

    if "description" not in fm:
        errors.append("missing required key: description")
    elif not isinstance(fm["description"], str):
        errors.append("description must be a string")
    elif len(fm["description"].strip()) < 40:
        errors.append(
            f"description too short ({len(fm['description'].strip())} chars; "
            "want >= 40, ideally mentioning what + when to trigger)"
        )

    if len(body.strip()) < 100:
        errors.append("body too short — skill needs actual instructions")

    return errors


def main() -> int:
    if not SKILLS_DIR.exists():
        print(f"skills directory not found: {SKILLS_DIR}", file=sys.stderr)
        return 2

    skill_files = sorted(SKILLS_DIR.glob("*/SKILL.md"))
    if not skill_files:
        print(f"no SKILL.md files found under {SKILLS_DIR}", file=sys.stderr)
        return 2

    total_errors = 0
    for skill_md in skill_files:
        errors = validate_skill(skill_md)
        rel = skill_md.relative_to(SKILLS_DIR.parent)
        if errors:
            total_errors += len(errors)
            print(f"✗ {rel}")
            for err in errors:
                print(f"    - {err}")
        else:
            print(f"✓ {rel}")

    print()
    if total_errors:
        print(f"FAILED: {total_errors} error(s) across {len(skill_files)} skill(s)")
        return 1

    print(f"OK: {len(skill_files)} skill(s) validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
