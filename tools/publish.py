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

``--set-latest`` is GATED: it requires ``evidence/{version}.json`` (see
``tools/evidence.py``) whose ``zip_sha256`` equals the sha256 of the ZIP being
published and whose results pass the validation gate (BrowserScan >= 97,
CreepJS lies 0, JA4 == stock). Without ``--set-latest`` the entry is still
written, with a warning if that evidence is missing or invalid.

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
import re
import subprocess
import sys
import zipfile
from datetime import date
from pathlib import Path

# Sibling import (Python puts the script's dir on sys.path[0]).
from evidence import check_evidence_file, evidence_path
from validate_manifest import ASSET_TEMPLATE, validate_manifest

_EMPTY_MANIFEST = {"schema_version": 1, "latest": None, "platforms": ["win64"], "versions": {}}
_TOP_CHROME_RE = re.compile(r"[^/]+/chrome\.exe")


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for buf in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(buf)
    return h.hexdigest()


def check_zip(zip_path: Path) -> None:
    """Refuse anything that is not a Chrome package the SDK can install.

    The SDK extracts the asset and then looks for ``chrome.exe`` at the root
    (after lifting a single top-level folder), so accept ``chrome.exe`` or
    ``<folder>/chrome.exe``. Raises ValueError otherwise.
    """
    if not zipfile.is_zipfile(zip_path):
        raise ValueError(f"refusing to publish {zip_path}: not a ZIP archive")
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    if not any(n == "chrome.exe" or _TOP_CHROME_RE.fullmatch(n) for n in names):
        raise ValueError(
            f"refusing to publish {zip_path}: no chrome.exe at the archive root "
            f"or under a single top-level folder")


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


def default_evidence_file(version: str, manifest_path: Path, override=None) -> Path:
    """``override`` if given, else ``evidence/<version>.json`` beside the manifest."""
    if override is not None:
        return Path(override)
    return evidence_path(version, Path(manifest_path).resolve().parent)


def publish(
    version: str,
    zip_path: Path,
    manifest_path: Path,
    *,
    set_latest: bool,
    min_conf_schema=None,
    released=None,
    evidence_file=None,
    rollback: bool = False,
) -> dict:
    """Return the updated manifest dict (does not write). Raises on invalid result.

    With ``set_latest`` the evidence file (default ``evidence/<version>.json``
    next to the manifest) must admit this exact ZIP, else ValueError.

    ``rollback`` waives the evidence requirement ONLY for a version already in
    the manifest with the same sha256 - i.e. moving ``latest`` back to a build
    that was published before (possibly before the gate existed). New bytes
    never pass without evidence.
    """
    check_zip(zip_path)

    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = json.loads(json.dumps(_EMPTY_MANIFEST))  # deep copy: never mutate the template

    if min_conf_schema is None:
        min_conf_schema = carry_min_conf_schema(manifest)
    if released is None:
        released = date.today().isoformat()

    entry = build_entry(version, zip_path, min_conf_schema, released)

    # A published version is immutable: clients that already installed it
    # verified THAT sha256 and never re-download. Re-running with the same zip
    # (e.g. just to --set-latest) is fine; different bytes need a new version.
    existing = manifest.get("versions", {}).get(version)
    if isinstance(existing, dict):
        old_sha = (existing.get("win64") or {}).get("sha256")
        new_sha = entry["win64"]["sha256"]
        if old_sha and old_sha != new_sha:
            raise ValueError(
                f"refusing to overwrite {version}: it is already published with sha256 "
                f"{old_sha[:12]}..., this zip is {new_sha[:12]}... — a new build must get "
                f"a new version")

    if rollback and not set_latest:
        raise ValueError("--rollback only makes sense with --set-latest")
    if rollback and not (isinstance(existing, dict)
                         and (existing.get("win64") or {}).get("sha256") == entry["win64"]["sha256"]):
        raise ValueError(
            f"refusing --rollback to {version}: it is not already published with this exact "
            f"zip — a rollback may only move latest to a previously published build")
    if set_latest and not rollback:
        ev_file = default_evidence_file(version, manifest_path, evidence_file)
        problems = check_evidence_file(ev_file, version, entry["win64"]["sha256"])
        if problems:
            raise ValueError(
                f"refusing --set-latest for {version}: no valid release evidence\n"
                + "\n".join(f"  - {p}" for p in problems)
                + "\n  (fill evidence/<version>.json after the validation gate; "
                  "see tools/README.md)")

    manifest.setdefault("versions", {})[version] = entry
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
    ap.add_argument("--evidence", default=None,
                    help="release evidence JSON (default: evidence/{version}.json next "
                         "to the manifest); required and validated for --set-latest")
    ap.add_argument("--rollback", action="store_true",
                    help="with --set-latest: move latest back to an ALREADY published version "
                         "(same zip sha256) without requiring release evidence")
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
            evidence_file=args.evidence,
            rollback=args.rollback,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if not args.set_latest:
        ev_file = default_evidence_file(args.version, manifest_path, args.evidence)
        problems = check_evidence_file(
            ev_file, args.version, manifest["versions"][args.version]["win64"]["sha256"])
        if problems:
            print(f"WARNING: {args.version} has no valid release evidence — publishing the "
                  f"entry anyway (latest is NOT moved); --set-latest will be refused until "
                  f"it is fixed:\n" + "\n".join(f"  - {p}" for p in problems),
                  file=sys.stderr)

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
        to_add = [str(manifest_path)]
        if args.set_latest and args.evidence is None and not args.rollback:
            # the gate passed: the in-repo evidence belongs in the same commit
            to_add.append(str(default_evidence_file(args.version, manifest_path)))
        subprocess.run(["git", "add", *to_add], check=True)
        msg = f"manifest: publish Chrome {args.version}"
        if args.set_latest:
            msg += " (latest, rollback)" if args.rollback else " (latest)"
        subprocess.run(["git", "commit", "-m", msg], check=True)
        print("Committed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
