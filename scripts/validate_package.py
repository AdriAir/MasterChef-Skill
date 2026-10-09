#!/usr/bin/env python3
"""Development-only YAML and packaging checks; requires requirements-dev.txt."""

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def main():
    skill = ROOT / "skills" / "masterchef"
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    frontmatter = re.match(r"\A---\n(.*?)\n---(?:\n|$)", text, flags=re.S)
    if frontmatter is None:
        raise ValueError("SKILL.md must start with YAML frontmatter")
    header = yaml.safe_load(frontmatter.group(1))
    if not isinstance(header, dict) or header.get("name") != "masterchef":
        raise ValueError("Skill name must be masterchef")
    description = header.get("description")
    if not isinstance(description, str) or not description.strip() or len(description) > 1024:
        raise ValueError("Skill description must be a non-empty string <=1024 characters")
    metadata = yaml.safe_load((skill / "agents" / "openai.yaml").read_text(encoding="utf-8"))
    interface = metadata["interface"]
    if not 25 <= len(interface["short_description"]) <= 64:
        raise ValueError("short_description must have 25-64 characters")
    if "$masterchef" not in interface["default_prompt"]:
        raise ValueError("default_prompt must invoke $masterchef")
    if metadata["policy"].get("allow_implicit_invocation") is not True:
        raise ValueError("Implicit invocation must be enabled")
    # Parse CI too: a malformed workflow otherwise fails only after publication.
    workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"))
    if not isinstance(workflow, dict) or not workflow.get("jobs"):
        raise ValueError("CI must define jobs")
    print(json.dumps({"valid": True, "checks": ["frontmatter", "openai.yaml", "ci.yml"]}))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError, yaml.YAMLError) as error:
        print(json.dumps({"valid": False, "error": str(error)}))
        sys.exit(1)
