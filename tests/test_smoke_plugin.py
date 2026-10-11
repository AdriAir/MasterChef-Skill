"""Security boundaries for validating an installed package, without a network."""

import importlib.util
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("smoke_plugin", ROOT / "scripts" / "smoke_plugin.py")
smoke = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(smoke)


class InstalledRegistryTests(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory(prefix="masterchef-smoke-security-")
        self.addCleanup(self.workspace.cleanup)
        self.work = Path(self.workspace.name)
        self.skill = self.work / "installed" / "skills" / "masterchef"
        (self.skill / "scripts").mkdir(parents=True)
        (self.skill / "references").mkdir()
        self.helper = self.skill / "scripts" / "validate_sources.py"
        self.registry = self.skill / "references" / "sources.json"
        shutil.copyfile(ROOT / "skills" / "masterchef" / "scripts" / "validate_sources.py", self.helper)
        shutil.copyfile(ROOT / "skills" / "masterchef" / "references" / "sources.json", self.registry)
        self.environment = dict(os.environ)

    def test_validates_installed_registry_from_an_unrelated_working_directory(self):
        smoke.validate_installed_registry(self.skill, self.work, self.environment)

    def test_rejects_modified_remote_helper_without_executing_it(self):
        marker = self.work / "remote-code-executed"
        self.helper.write_text("from pathlib import Path\nPath({!r}).touch()\n".format(str(marker)))
        with self.assertRaisesRegex(RuntimeError, "integrity"):
            smoke.validate_installed_registry(self.skill, self.work, self.environment)
        self.assertFalse(marker.exists())

    def test_pythonpath_cannot_inject_a_module_into_validation(self):
        rogue = self.work / "rogue"
        rogue.mkdir()
        marker = self.work / "injected-module-executed"
        (rogue / "json.py").write_text(
            "from pathlib import Path\nPath({!r}).touch()\nraise RuntimeError('injection')\n".format(str(marker)))
        self.environment["PYTHONPATH"] = str(rogue)
        smoke.validate_installed_registry(self.skill, rogue, self.environment)
        self.assertFalse(marker.exists())

    def test_rejects_an_invalid_installed_registry(self):
        self.registry.write_text(json.dumps({"schema_version": 1, "sources": []}))
        with self.assertRaisesRegex(RuntimeError, "registry failed validation"):
            smoke.validate_installed_registry(self.skill, self.work, self.environment)

    def test_registry_cannot_be_a_symlink_outside_the_installed_skill(self):
        external = self.work / "external-registry.json"
        shutil.copyfile(self.registry, external)
        self.registry.unlink()
        try:
            self.registry.symlink_to(external)
        except OSError:
            self.skipTest("Creating symlinks is unavailable in this environment")
        with self.assertRaisesRegex(RuntimeError, "escapes the skill directory"):
            smoke.validate_installed_registry(self.skill, self.work, self.environment)


if __name__ == "__main__":
    unittest.main()
