import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "skills" / "masterchef" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from validate_sources import check_url, validate_registry


def source(**overrides):
    value = {
        "id": "example-recipes",
        "name": "Example Recipes",
        "purposes": ["recipe"],
        "hosts": ["recipes.example.com", "www.recipes.example.com"],
        "paths": ["/recipe/tortilla"],
        "path_prefixes": ["/recipes/"],
        "regions": ["ES"],
        "coverage_note": "Synthetic test coverage.",
        "languages": ["es", "en"],
        "rationale": "Tests exact URLs and prefixes.",
        "evidence_urls": ["https://recipes.example.com/about"],
        "checked_at": "2026-10-09",
        "attribution": "Example editorial team",
    }
    value.update(overrides)
    return value


def registry(*sources):
    return {"schema_version": 1, "sources": list(sources)}


class ValidateRegistryTests(unittest.TestCase):
    def test_accepts_complete_schema_and_requires_route_rule(self):
        self.assertEqual(validate_registry(registry(source())), [])
        errors = validate_registry(registry(source(paths=[], path_prefixes=[])))
        self.assertTrue(any("paths or path_prefixes" in error for error in errors))

    def test_rejects_malformed_registry_entries(self):
        bad = registry(source(
            id="duplicate",
            purposes=["recipe", "not-a-purpose"],
            hosts=["*.example.com"],
            languages=["fr"],
            checked_at="yesterday",
            paths=["/recipe/*"],
        ), source(id="duplicate"))
        bad["schema_version"] = True
        errors = validate_registry(bad)
        self.assertTrue(any("schema_version" in error for error in errors))
        self.assertTrue(any("hosts" in error for error in errors))
        self.assertTrue(any("checked_at" in error for error in errors))
        self.assertTrue(any("purposes" in error for error in errors))
        self.assertTrue(any("languages" in error for error in errors))
        self.assertTrue(any("paths" in error for error in errors))
        self.assertTrue(any("id must be unique" in error for error in errors))

    def test_handles_wrong_field_types_without_crashing(self):
        errors = validate_registry(registry(source(
            purposes={"recipe": True}, hosts=[["recipes.example.com"]],
            paths="/recipe/tortilla", path_prefixes={"/recipes/"},
        )))
        self.assertTrue(errors)

    def test_rejects_unknown_keys_and_multiple_purposes(self):
        data = registry(source(purposes=["recipe", "weather"], ignored_policy="allow-all"))
        data["unexpected"] = True
        errors = validate_registry(data)
        self.assertTrue(any("unknown field" in error for error in errors))
        self.assertTrue(any("exactly one purpose" in error for error in errors))


class CheckUrlTests(unittest.TestCase):
    def setUp(self):
        self.registry = registry(source())

    def test_allows_exact_path_prefix_and_explicit_alias(self):
        for url in (
            "https://recipes.example.com/recipe/tortilla",
            "https://recipes.example.com/recipes/arroz?servings=4#method",
            "https://www.recipes.example.com/recipes/arroz",
        ):
            result = check_url(self.registry, url, "recipe")
            self.assertEqual(result, {"allowed": True, "reason": "allowed", "source_id": "example-recipes"})

    def test_final_url_must_remain_at_the_same_explicit_source(self):
        result = check_url(
            self.registry,
            "https://recipes.example.com/recipes/arroz",
            "recipe",
            final_url="https://www.recipes.example.com/recipes/arroz",
        )
        self.assertTrue(result["allowed"])
        denied = check_url(
            self.registry,
            "https://recipes.example.com/recipes/arroz",
            "recipe",
            final_url="https://other.example.com/recipes/arroz",
        )
        self.assertEqual(denied["reason"], "final_url_not_allowed")
        wrong_path = check_url(
            self.registry,
            "https://recipes.example.com/recipes/arroz",
            "recipe",
            final_url="https://www.recipes.example.com/private",
        )
        self.assertEqual(wrong_path["reason"], "final_url_not_allowed")

    def test_rejects_lookalikes_and_wrong_purpose(self):
        cases = {
            "https://recipes.example.com/recipes-evil/arroz": "path_not_allowed",
            "https://evilrecipes.example.com/recipes/arroz": "host_not_allowed",
            "https://recipes.example.com@evil.example/recipes/arroz": "invalid_url",
            "http://recipes.example.com/recipes/arroz": "https_required",
            "https://recipes.example.com:444/recipes/arroz": "invalid_port",
            "https://127.0.0.1/recipes/arroz": "invalid_url",
            "https://[::1]/recipes/arroz": "invalid_url",
            "https://recipes.example.com./recipes/arroz": "invalid_url",
            "https://r\u0435cipes.example.com/recipes/arroz": "invalid_url",
            "https://recipes.example.com/recipes/\x01arroz": "invalid_url",
            "https://recipes.example.com/recipes/arroz?q=%": "invalid_url",
            "https://recipes.example.com/recipes/arroz?q=%0A": "invalid_url",
        }
        for url, expected_reason in cases.items():
            with self.subTest(url=url):
                self.assertEqual(check_url(self.registry, url, "recipe")["reason"], expected_reason)
        self.assertEqual(check_url(self.registry, "https://recipes.example.com/recipes/arroz", "weather")["reason"], "purpose_not_allowed")

    def test_allows_unicode_paths_but_rejects_path_bypasses(self):
        self.assertTrue(check_url(self.registry, "https://recipes.example.com/recipes/paella-espa\u00f1ola", "recipe")["allowed"])
        self.assertTrue(check_url(self.registry, "https://recipes.example.com/recipes/paella-%E2%9C%93", "recipe")["allowed"])
        for suffix in ("../private", "%2e%2e/private", "%2Fprivate", "%5cprivate", "%252fprivate", "%252e%252e/private", "%25252e%25252e/private", "%FF", "%", "a%ZZ"):
            with self.subTest(suffix=suffix):
                result = check_url(self.registry, "https://recipes.example.com/recipes/" + suffix, "recipe")
                self.assertEqual(result["reason"], "invalid_path")

    def test_matches_percent_encoded_unicode_exact_routes(self):
        encoded_registry = registry(source(paths=["/food/%2B"], path_prefixes=[]))
        self.assertTrue(check_url(encoded_registry, "https://recipes.example.com/food/%2B", "recipe")["allowed"])

    def test_registry_errors_fail_closed(self):
        result = check_url(registry(source(hosts=["*.example.com"])), "https://recipes.example.com/recipes/arroz", "recipe")
        self.assertEqual(result, {"allowed": False, "reason": "invalid_registry"})


class CliTests(unittest.TestCase):
    def write_registry(self, directory):
        path = Path(directory) / "sources.json"
        path.write_text(json.dumps(registry(source())), encoding="utf-8")
        return path

    def run_cli(self, *args, cwd=None):
        return subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "validate_sources.py"), *args],
            cwd=cwd or PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_cli_json_and_exit_codes(self):
        with tempfile.TemporaryDirectory() as directory:
            registry_path = self.write_registry(directory)
            accepted = self.run_cli("check", "https://recipes.example.com/recipes/arroz", "--purpose", "recipe", "--registry", str(registry_path))
            self.assertEqual(accepted.returncode, 0)
            self.assertEqual(json.loads(accepted.stdout)["source_id"], "example-recipes")
            denied = self.run_cli("check", "http://recipes.example.com/recipes/arroz", "--purpose", "recipe", "--registry", str(registry_path))
            self.assertEqual(denied.returncode, 1)
            self.assertEqual(json.loads(denied.stdout)["reason"], "https_required")
            invalid = self.run_cli("validate", "--registry", str(Path(directory) / "missing.json"))
            self.assertEqual(invalid.returncode, 1)
            self.assertFalse(json.loads(invalid.stdout)["valid"])
            syntax = self.run_cli("check", "https://recipes.example.com/recipes/arroz")
            self.assertEqual(syntax.returncode, 2)

    def test_cli_fails_closed_for_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            duplicate_root = Path(directory) / "duplicate-root.json"
            duplicate_root.write_text('{"schema_version": 1, "schema_version": 1, "sources": []}', encoding="utf-8")
            duplicate_source = Path(directory) / "duplicate-source.json"
            duplicate_source.write_text(
                '{"schema_version": 1, "sources": ['
                '{"id": "one", "id": "two", "name": "Example", "purposes": ["recipe"], '
                '"hosts": ["recipes.example.com"], "paths": ["/recipe/tortilla"], "path_prefixes": [], '
                '"regions": ["ES"], "coverage_note": "coverage", "languages": ["es"], '
                '"rationale": "reason", "evidence_urls": ["https://recipes.example.com/evidence"], '
                '"checked_at": "2026-10-09", "attribution": "team"}]}',
                encoding="utf-8",
            )
            for registry_path in (duplicate_root, duplicate_source):
                with self.subTest(registry_path=registry_path.name):
                    validated = self.run_cli("validate", "--registry", str(registry_path))
                    self.assertEqual(validated.returncode, 1)
                    self.assertFalse(json.loads(validated.stdout)["valid"])
                    checked = self.run_cli("check", "https://recipes.example.com/recipe/tortilla", "--purpose", "recipe", "--registry", str(registry_path))
                    self.assertEqual(checked.returncode, 1)
                    self.assertEqual(json.loads(checked.stdout), {"allowed": False, "reason": "invalid_registry"})

    def test_default_registry_is_resolved_relative_to_script_not_cwd(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_cli("validate", cwd=directory)
            self.assertEqual(result.returncode, 0)
            self.assertTrue(json.loads(result.stdout)["valid"])


if __name__ == "__main__":
    unittest.main()
