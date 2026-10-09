"""Integration contracts for the installable plugin (no recipe wording checks)."""

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "masterchef"


class PackageTests(unittest.TestCase):
    def read_json(self, path):
        return json.loads((ROOT / path).read_text(encoding="utf-8"))

    def test_marketplace_resolves_a_self_contained_plugin(self):
        marketplace = self.read_json(".agents/plugins/marketplace.json")
        self.assertEqual(marketplace["name"], "masterchef")
        self.assertEqual(len(marketplace["plugins"]), 1)
        entry = marketplace["plugins"][0]
        self.assertEqual(entry["source"], {"source": "local", "path": "./"})
        plugin = self.read_json(".codex-plugin/plugin.json")
        self.assertEqual((entry["name"], entry["version"]), (plugin["name"], plugin["version"]))
        self.assertEqual(plugin["version"], "0.1.0")
        self.assertEqual(plugin["skills"], "./skills/")
        self.assertTrue((ROOT / plugin["skills"] / "masterchef" / "SKILL.md").is_file())
        self.assertNotIn("mcpServers", plugin)

    def test_skill_references_resolve_inside_the_installed_skill(self):
        documents = [SKILL / "SKILL.md", *sorted((SKILL / "references").glob("*.md"))]
        self.assertGreater(len(documents), 1)
        for document in documents:
            for target in re.findall(r"\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
                if "://" in target or target.startswith("#"):
                    continue
                resolved = (document.parent / target.split("#", 1)[0]).resolve()
                with self.subTest(document=document.name, target=target):
                    self.assertTrue(resolved.is_relative_to(SKILL.resolve()))
                    self.assertTrue(resolved.is_file())

    def test_registry_has_ten_culinary_sources_and_separate_context(self):
        registry = self.read_json("skills/masterchef/references/sources.json")
        recipes = [source for source in registry["sources"] if "recipe" in source["purposes"]]
        self.assertEqual(len(recipes), 10)
        self.assertTrue(all(source["purposes"] == ["recipe"] for source in recipes))
        purposes = {purpose for source in registry["sources"] for purpose in source["purposes"]}
        self.assertEqual(purposes, {"recipe", "weather", "geocoding", "season", "food_safety"})
        by_id = {source["id"]: source for source in registry["sources"]}
        self.assertEqual(by_id["food-hero-season"]["regions"], ["US-OR"])
        self.assertEqual(by_id["sydney-markets-season"]["regions"], ["AU-NSW"])


if __name__ == "__main__":
    unittest.main()
