#!/usr/bin/env python3
"""Install the local plugin in an isolated child-process Codex home."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    codex = shutil.which("codex")
    if not codex:
        raise RuntimeError("codex is not available on PATH")
    with tempfile.TemporaryDirectory(prefix="masterchef-smoke-") as task_home:
        task_env = dict(os.environ, CODEX_HOME=task_home)

        def run(arguments):
            result = subprocess.run([codex, *arguments], cwd=task_home, env=task_env,
                                    capture_output=True, text=True, timeout=60)
            if result.returncode:
                raise RuntimeError("Codex command failed: " + result.stderr.strip())
            return json.loads(result.stdout)

        added = run(["plugin", "marketplace", "add", str(ROOT), "--json"])
        if added["marketplaceName"] != "masterchef":
            raise RuntimeError("Unexpected marketplace name")
        available = run(["plugin", "list", "--available", "--json"])
        if not any(item["pluginId"] == "masterchef@masterchef" for item in available["available"]):
            raise RuntimeError("Plugin was not discovered")
        installation = run(["plugin", "add", "masterchef@masterchef", "--json"])
        installed = run(["plugin", "list", "--json"])
        if not any(item["pluginId"] == "masterchef@masterchef" and item["enabled"]
                   for item in installed["installed"]):
            raise RuntimeError("Plugin was not enabled")
        skill = Path(installation["installedPath"]) / "skills" / "masterchef"
        if not (skill / "SKILL.md").is_file() or not (skill / "agents" / "openai.yaml").is_file():
            raise RuntimeError("Installed skill is incomplete")
        checked = subprocess.run([sys.executable, str(skill / "scripts" / "validate_sources.py"), "validate"],
                                 cwd=task_home, env=task_env, capture_output=True, text=True, timeout=30)
        if checked.returncode or json.loads(checked.stdout).get("valid") is not True:
            raise RuntimeError("Installed source registry failed validation")
        for reference in ("source-policy.md", "fidelity.md", "context.md"):
            if not (skill / "references" / reference).is_file():
                raise RuntimeError("Missing installed reference: " + reference)
    print(json.dumps({"valid": True, "plugin": "masterchef@masterchef", "version": "0.1.0",
                      "checks": ["discovery", "installation", "enabled", "installed_skill", "installed_registry"]}))


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
        print(json.dumps({"valid": False, "error": str(error)}))
        sys.exit(1)
