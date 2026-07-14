#!/usr/bin/env python3
"""Add or update a Chrome build in ``manifest.json`` from a local zip.

Run this AFTER a patched-Chrome build has passed validation (BrowserScan 100%x2,
CreepJS no-lies) and its ``huligan-chrome-{version}-win64.zip`` has been / will be
uploaded to the GitHub Release ``v{version}``. The script computes size + sha256
from the local zip and writes the manifest entry the SDK resolver reads.

Important: the sha256 must match the EXACT zip uploaded to the release — the SDK
verifies the downloaded asset against this value. Compute from the same file you
upload.

The manifest ``latest`` only moves when you pass ``--set-latest`` — publishing an
entry does not silently promote it, so farms on the ``latest`` channel never pick
up an unvalidated build.

Examples:
    # add the entry but do NOT promote it yet
    python tools/publish.py 151.0.7900.1 --zip ../builds/huligan-chrome-151.0.7900.1-win64.zip

    # promote to latest and commit
    python tools/publish.py 151.0.7900.1 --set-latest --commit

    # preview only
    python tools/publish.py 151.0.7900.1 --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

# Sibling import (Python puts the script's dir on sys.path[0]).
from validate_manifest import ASSET_TEMPLATE, validate_manifest

_EMPTY_MANIFEST = {"schema_version": 1, "latest": None, "platforms": ["win64"], "versions": {}}


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for buf in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(buf)
    return h.hexdigest()


def carry_min_conf_schema(manifest: dict) -> int:
    """Default a new build to the highest schema already published (>=1).

    Carrying forward avoids accidentally under-declaring the gate; bump
    explicitly with --min-conf-schema when a build introduces a new .conf key.
    """
    vals = [
        e.get("min_conf_schema", 1)
        for e in manifest.get("versions", {}).values()
        if isinstance(e.get("min_conf_schema", 1), int)
    ]
    return max(vals) if vals else 1


def build_entry(version: str, zip_path: Path, min_conf_schema: int, released: str) -> dict:
    return {
        "tag": f"v{version}",
        "released": released,
        "min_conf_schema": min_conf_schema,
        "win64": {
            "asset": ASSET_TEMPLATE.format(version=version),
            "size": zip_path.stat().st_size,
            "sha256": sha256_of(zip_path),
        },
    }


def publish(
    version: str,
    zip_path: Path,
    manifest_path: Path,
    *,
    set_latest: bool,
    min_conf_schema=None,
    released=None,
) -> dict:
    """Return the updated manifest dict (does not write). Raises on invalid result."""
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = dict(_EMPTY_MANIFEST)

    if min_conf_schema is None:
        min_conf_schema = carry_min_conf_schema(manifest)
    if released is None:
        released = date.today().isoformat()

    manifest.setdefault("versions", {})[version] = build_entry(
        version, zip_path, min_conf_schema, released)
    if set_latest:
        manifest["latest"] = version

    errors = validate_manifest(manifest)
    if errors:
        raise ValueError(
            "refusing to write an invalid manifest:\n"
            + "\n".join(f"  - {e}" for e in errors))
    return manifest


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Publish a Chrome build into manifest.json")
    ap.add_argument("version", help="e.g. 151.0.7900.1")
    ap.add_argument("--zip", help="path to the built zip (default: "
                                  "huligan-chrome-{version}-win64.zip in CWD)")
    ap.add_argument("--set-latest", action="store_true",
                    help="promote this build to the 'latest' channel")
    ap.add_argument("--min-conf-schema", type=int, default=None,
                    help="override the .conf schema this build requires "
                         "(default: carry forward the current max)")
    ap.add_argument("--released", default=None, help="YYYY-MM-DD (default: today)")
    ap.add_argument("--manifest", default="manifest.json")
    ap.add_argument("--commit", action="store_true", help="git add + commit the manifest")
    ap.add_argument("--dry-run", action="store_true", help="print the result, write nothing")
    args = ap.parse_args(argv)

    zip_path = Path(args.zip) if args.zip else Path(ASSET_TEMPLATE.format(version=args.version))
    if not zip_path.is_file():
        print(f"zip not found: {zip_path}", file=sys.stderr)
        return 1

    manifest_path = Path(args.manifest)
    try:
        manifest = publish(
            args.version, zip_path, manifest_path,
            set_latest=args.set_latest,
            min_conf_schema=args.min_conf_schema,
            released=args.released,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    text = json.dumps(manifest, indent=2) + "\n"
    if args.dry_run:
        print(text)
        return 0

    manifest_path.write_text(text, encoding="utf-8")
    entry = manifest["versions"][args.version]["win64"]
    print(f"Updated {manifest_path}")
    print(f"  {args.version}: {entry['size']} bytes, sha256 {entry['sha256'][:12]}...")
    print(f"  latest: {'-> ' + args.version if args.set_latest else 'unchanged'}")

    if args.commit:
        subprocess.run(["git", "add", str(manifest_path)], check=True)
        msg = f"manifest: publish Chrome {args.version}"
        if args.set_latest:
            msg += " (latest)"
        subprocess.run(["git", "commit", "-m", msg], check=True)
        print("Committed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
