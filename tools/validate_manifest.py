#!/usr/bin/env python3
"""Validate the structure of ``manifest.json``.

Pure, offline schema checks — the same rules ``publish.py`` enforces before it
writes, and what the ``validate-manifest`` GitHub Action runs on every PR that
touches the manifest. Catches the mistakes that would silently break the SDK's
resolver: a wrong asset name, a malformed sha256, a ``latest`` pointing at a
version that isn't published, a missing ``min_conf_schema`` (Phase 2 gate).

Usage:
    python tools/validate_manifest.py [--manifest manifest.json]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ASSET_TEMPLATE = "huligan-chrome-{version}-win64.zip"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_TOP = ("schema_version", "latest", "platforms", "versions")


def validate_manifest(data: dict) -> list:
    """Return a list of human-readable error strings (empty == valid)."""
    errors: list = []

    if not isinstance(data, dict):
        return ["manifest root must be a JSON object"]

    for key in _REQUIRED_TOP:
        if key not in data:
            errors.append(f"missing top-level key: {key}")

    versions = data.get("versions")
    if not isinstance(versions, dict) or not versions:
        errors.append("'versions' must be a non-empty object")
        return errors  # nothing else is checkable

    latest = data.get("latest")
    if latest is not None and latest not in versions:
        errors.append(f"'latest' {latest!r} is not present in versions")

    for ver, entry in versions.items():
        loc = f"versions.{ver}"
        if not isinstance(entry, dict):
            errors.append(f"{loc} must be an object")
            continue

        if entry.get("tag") != f"v{ver}":
            errors.append(f"{loc}.tag should be 'v{ver}', got {entry.get('tag')!r}")

        mcs = entry.get("min_conf_schema")
        if not isinstance(mcs, int) or isinstance(mcs, bool) or mcs < 1:
            errors.append(f"{loc}.min_conf_schema must be an int >= 1, got {mcs!r}")

        win = entry.get("win64")
        if not isinstance(win, dict):
            errors.append(f"{loc}.win64 is missing or not an object")
            continue

        expected_asset = ASSET_TEMPLATE.format(version=ver)
        if win.get("asset") != expected_asset:
            errors.append(
                f"{loc}.win64.asset should be {expected_asset!r}, got {win.get('asset')!r}")

        size = win.get("size")
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            errors.append(f"{loc}.win64.size must be a positive int, got {size!r}")

        sha = win.get("sha256")
        if not isinstance(sha, str) or not _SHA256_RE.match(sha):
            errors.append(f"{loc}.win64.sha256 must be 64 lowercase hex chars, got {sha!r}")

    return errors


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Validate manifest.json structure")
    ap.add_argument("--manifest", default="manifest.json")
    args = ap.parse_args(argv)

    path = Path(args.manifest)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"manifest not found: {path}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"manifest is not valid JSON: {exc}", file=sys.stderr)
        return 1

    errors = validate_manifest(data)
    if errors:
        print("Manifest INVALID:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(f"Manifest OK: {len(data['versions'])} version(s), latest={data.get('latest')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
