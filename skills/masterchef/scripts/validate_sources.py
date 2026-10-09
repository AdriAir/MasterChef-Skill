#!/usr/bin/env python3
"""Validate the MasterChef source registry and check URLs against it.

The checker is deliberately offline: registry regions inform an agent, but do
not authorize or deny a URL based on geographic location.
"""

import argparse
import datetime as dt
import ipaddress
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit


PURPOSES = {"recipe", "weather", "geocoding", "season", "food_safety"}
LANGUAGES = {"es", "en"}
TOP_LEVEL_FIELDS = {"schema_version", "sources"}
SOURCE_FIELDS = {
    "id", "name", "purposes", "hosts", "paths", "path_prefixes", "regions",
    "coverage_note", "languages", "rationale", "evidence_urls", "checked_at",
    "attribution",
}
DEFAULT_REGISTRY = Path(__file__).resolve().parents[1] / "references" / "sources.json"
HOST_RE = re.compile(r"(?=.{1,253}\Z)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)(?:\.(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?))*\Z")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
PERCENT_RE = re.compile(r"%(?![0-9A-Fa-f]{2})")
ROUTE_META_RE = re.compile(r"[*?\[\]{}()|^$\\\\]")


def _is_ascii_hostname(value):
    if not isinstance(value, str) or not value.isascii() or value.endswith("."):
        return False
    if not HOST_RE.fullmatch(value):
        return False
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return True
    return False


def _valid_date(value):
    if not isinstance(value, str) or not DATE_RE.fullmatch(value):
        return False
    try:
        dt.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _valid_string_list(value, allowed=None):
    return isinstance(value, list) and bool(value) and all(
        isinstance(item, str) and item.strip() and (allowed is None or item in allowed)
        for item in value
    )


def _valid_route(route, prefix=False):
    if not isinstance(route, str) or not route.startswith("/") or "\\" in route:
        return False
    if any(ord(character) < 32 or ord(character) == 127 for character in route):
        return False
    if PERCENT_RE.search(route) or ROUTE_META_RE.search(route):
        return False
    if prefix and route != "/" and not route.endswith("/"):
        return False
    return _safe_path(route) is not None


def validate_registry(data):
    """Return schema errors; an empty list means the registry is usable."""
    errors = []
    if not isinstance(data, dict):
        return ["registry must be an object"]
    unknown_top_level = set(data) - TOP_LEVEL_FIELDS
    if unknown_top_level:
        errors.append("registry contains unknown field: {0}".format(sorted(unknown_top_level)[0]))
    if type(data.get("schema_version")) is not int or data.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    sources = data.get("sources")
    if not isinstance(sources, list) or not sources:
        return errors + ["sources must be a non-empty list"]

    seen_ids = set()
    required_strings = ("id", "name", "coverage_note", "rationale", "attribution")
    for index, item in enumerate(sources):
        label = "sources[{0}]".format(index)
        if not isinstance(item, dict):
            errors.append(label + " must be an object")
            continue
        unknown_fields = set(item) - SOURCE_FIELDS
        if unknown_fields:
            errors.append(label + " contains unknown field: {0}".format(sorted(unknown_fields)[0]))
        for field in required_strings:
            if not isinstance(item.get(field), str) or not item[field].strip():
                errors.append(label + "." + field + " must be a non-empty string")
        source_id = item.get("id")
        if isinstance(source_id, str) and source_id.strip():
            if source_id in seen_ids:
                errors.append(label + ".id must be unique")
            seen_ids.add(source_id)
        if not _valid_string_list(item.get("purposes"), PURPOSES):
            errors.append(label + ".purposes contains an invalid purpose")
        elif len(item["purposes"]) != 1:
            errors.append(label + ".purposes must contain exactly one purpose")
        hosts = item.get("hosts")
        if not _valid_string_list(hosts) or not all(_is_ascii_hostname(host) for host in hosts):
            errors.append(label + ".hosts must contain exact ASCII hostnames")
        if not _valid_string_list(item.get("regions")):
            errors.append(label + ".regions must be a non-empty string list")
        if not _valid_string_list(item.get("languages"), LANGUAGES):
            errors.append(label + ".languages contains an invalid language")
        evidence_urls = item.get("evidence_urls")
        if not _valid_string_list(evidence_urls) or not all(_is_https_url(url) for url in evidence_urls):
            errors.append(label + ".evidence_urls must contain HTTPS URLs")
        if not _valid_date(item.get("checked_at")):
            errors.append(label + ".checked_at must be YYYY-MM-DD")
        paths = item.get("paths", [])
        prefixes = item.get("path_prefixes", [])
        if not isinstance(paths, list) or not all(_valid_route(path) for path in paths):
            errors.append(label + ".paths must contain exact paths")
        if not isinstance(prefixes, list) or not all(_valid_route(prefix, prefix=True) for prefix in prefixes):
            errors.append(label + ".path_prefixes must contain slash-terminated prefixes")
        if not paths and not prefixes:
            errors.append(label + " must define paths or path_prefixes")
    return errors


def _contains_controls(value):
    return any(ord(character) < 32 or ord(character) == 127 for character in value)


def _safe_path(path):
    if not isinstance(path, str) or not path.startswith("/") or "\\" in path or _contains_controls(path):
        return None
    if PERCENT_RE.search(path):
        return None
    try:
        decoded = unquote(path, errors="strict")
        decoded_twice = unquote(decoded, errors="strict")
    except UnicodeDecodeError:
        return None
    # Any percent escape left after one pass is nested encoding.  Reject it
    # conservatively so no later decoding layer can turn it into traversal.
    if re.search(r"%[0-9A-Fa-f]{2}", decoded):
        return None
    for value in (path, decoded, decoded_twice):
        if "\\" in value or _contains_controls(value):
            return None
        if any(segment in {".", ".."} for segment in value.split("/")):
            return None
    # Encoded separators become literal separators after decoding and are invalid.
    if "/" in decoded and "%2f" in path.lower():
        return None
    if "/" in decoded_twice and "%2f" in decoded.lower():
        return None
    return decoded


def _is_https_url(value):
    return _parse_url(value)[0] is not None


def _parse_url(value):
    if not isinstance(value, str) or not value or _contains_controls(value) or "\\" in value:
        return None, "invalid_url"
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return None, "invalid_url"
    if parsed.scheme.lower() != "https":
        return None, "https_required"
    if parsed.username is not None or parsed.password is not None:
        return None, "invalid_url"
    host = parsed.hostname
    if not host or not _is_ascii_hostname(host):
        return None, "invalid_url"
    if port not in (None, 443):
        return None, "invalid_port"
    path = _safe_path(parsed.path or "/")
    if path is None:
        return None, "invalid_path"
    if PERCENT_RE.search(parsed.query) or _contains_controls(parsed.query) or _contains_controls(unquote(unquote(parsed.query))):
        return None, "invalid_url"
    return {"host": host.lower(), "path": path}, None


def _matches_route(source, parsed):
    candidate = parsed["path"]
    for exact_path in source.get("paths", []):
        normalized = _safe_path(exact_path)
        if normalized == candidate:
            return True
    for prefix in source.get("path_prefixes", []):
        normalized = _safe_path(prefix)
        if normalized == "/" or candidate.startswith(normalized):
            return True
    return False


def check_url(registry, url, purpose, final_url=None):
    """Return the stable allow/deny object for one URL check."""
    if validate_registry(registry):
        return {"allowed": False, "reason": "invalid_registry"}
    parsed, reason = _parse_url(url)
    if reason:
        return {"allowed": False, "reason": reason}
    candidates = [source for source in registry["sources"] if parsed["host"] in {host.lower() for host in source["hosts"]}]
    if not candidates:
        return {"allowed": False, "reason": "host_not_allowed"}
    purpose_candidates = [source for source in candidates if purpose in source["purposes"]]
    if not purpose_candidates:
        return {"allowed": False, "reason": "purpose_not_allowed"}
    matching = next((source for source in purpose_candidates if _matches_route(source, parsed)), None)
    if matching is None:
        return {"allowed": False, "reason": "path_not_allowed"}
    if final_url is not None:
        final, final_reason = _parse_url(final_url)
        if final_reason or final["host"] not in {host.lower() for host in matching["hosts"]} or not _matches_route(matching, final):
            return {"allowed": False, "reason": "final_url_not_allowed"}
    return {"allowed": True, "reason": "allowed", "source_id": matching["id"]}


class DuplicateJsonKeyError(ValueError):
    pass


def _reject_duplicate_keys(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise DuplicateJsonKeyError("duplicate JSON key: {0}".format(key))
        value[key] = item
    return value


def _load_registry(path):
    try:
        with Path(path).open(encoding="utf-8") as handle:
            return json.load(handle, object_pairs_hook=_reject_duplicate_keys), []
    except (OSError, json.JSONDecodeError, DuplicateJsonKeyError) as error:
        return None, ["could not load registry: {0}".format(error)]


def _json_output(value):
    print(json.dumps(value, ensure_ascii=False, sort_keys=True))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate MasterChef source URLs offline.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    check_parser = subparsers.add_parser("check")
    check_parser.add_argument("url")
    check_parser.add_argument("--purpose", required=True, choices=sorted(PURPOSES))
    check_parser.add_argument("--final-url")
    check_parser.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    args = parser.parse_args(argv)
    data, load_errors = _load_registry(args.registry)
    if args.command == "validate":
        errors = load_errors or validate_registry(data)
        _json_output({"valid": not errors, "errors": errors})
        return 0 if not errors else 1
    if load_errors:
        _json_output({"allowed": False, "reason": "invalid_registry"})
        return 1
    result = check_url(data, args.url, args.purpose, args.final_url)
    _json_output(result)
    return 0 if result["allowed"] else 1


if __name__ == "__main__":
    sys.exit(main())
