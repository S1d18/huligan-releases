#!/usr/bin/env python3
"""Release evidence: the proof a build passed the validation gate.

``evidence/<version>.json`` is a required input for ``publish.py --set-latest``.
It records the operator's validation of ONE exact ZIP (bound by sha256), so the
``latest`` channel can only move to a build that was actually checked — not to
"a build of that version" and not to a rebuild nobody looked at.

Required fields (extra fields are allowed and ignored)::

    {
      "version": "154.0.8037.58",          # must equal the version being published
      "zip_sha256": "<64 lowercase hex>",  # must equal sha256 of the ZIP being published
      "browserscan_score": 100,            # number, >= MIN_BROWSERSCAN_SCORE (headed, real proxy)
      "creepjs_lies": 0,                   # int, must be <= MAX_CREEPJS_LIES (i.e. 0)
      "ja4_matches_stock": true,           # JA4 equals branded stock Chrome of the same major
      "tested_at": "2026-09-21",           # ISO date (or ISO datetime)
      "notes": "..."                       # free text: who/where/how, links to the этап4 log
    }

Thresholds come from the project's validation gate: BrowserScan >= 97 %,
CreepJS lies(0). The operator's VISUAL read of a headed window is the
authoritative number — the CDP scraper reports false 100 %.

CLI (check an evidence file before promoting)::

    python tools/evidence.py 154.0.8037.58 --zip huligan-chrome-154.0.8037.58-win64.zip
    python tools/evidence.py 154.0.8037.58          # sha taken from manifest.json
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path

MIN_BROWSERSCAN_SCORE = 97
MAX_CREEPJS_LIES = 0

REQUIRED_FIELDS = (
    "version", "zip_sha256", "browserscan_score", "creepjs_lies",
    "ja4_matches_stock", "tested_at", "notes",
)

_SHA_RE = re.compile(r"[0-9a-f]{64}")


def evidence_path(version: str, repo_root: Path) -> Path:
    """Where the evidence for ``version`` lives: ``<repo_root>/evidence/<version>.json``."""
    return Path(repo_root) / "evidence" / f"{version}.json"


def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _parse_iso(value: str) -> bool:
    for parse in (datetime.date.fromisoformat, datetime.datetime.fromisoformat):
        try:
            parse(value)
            return True
        except ValueError:
            pass
    return False


def validate_evidence(ev, version: str, zip_sha256: str) -> list[str]:
    """Return a list of problems (empty == the evidence admits this exact build)."""
    if not isinstance(ev, dict):
        return ["evidence must be a JSON object"]
    errors = [f"missing field '{k}'" for k in REQUIRED_FIELDS if k not in ev]

    if "version" in ev and ev["version"] != version:
        errors.append(f"version is {ev['version']!r}, publishing {version!r}")

    if "zip_sha256" in ev:
        sha = ev["zip_sha256"]
        if not isinstance(sha, str) or not _SHA_RE.fullmatch(sha):
            errors.append("zip_sha256 must be 64 lowercase hex characters")
        elif sha != zip_sha256.lower():
            errors.append(f"zip_sha256 {sha[:12]}... does not match the ZIP being published "
                          f"({zip_sha256[:12]}...) — the evidence is for different bytes")

    if "browserscan_score" in ev:
        s = ev["browserscan_score"]
        if not _is_number(s) or not 0 <= s <= 100:
            errors.append("browserscan_score must be a number 0..100")
        elif s < MIN_BROWSERSCAN_SCORE:
            errors.append(f"browserscan_score {s} < {MIN_BROWSERSCAN_SCORE}")

    if "creepjs_lies" in ev:
        lies = ev["creepjs_lies"]
        if not isinstance(lies, int) or isinstance(lies, bool) or lies < 0:
            errors.append("creepjs_lies must be a non-negative integer")
        elif lies > MAX_CREEPJS_LIES:
            errors.append(f"creepjs_lies {lies} > {MAX_CREEPJS_LIES}")

    if "ja4_matches_stock" in ev and ev["ja4_matches_stock"] is not True:
        errors.append("ja4_matches_stock must be true")

    if "tested_at" in ev:
        t = ev["tested_at"]
        if not isinstance(t, str) or not _parse_iso(t):
            errors.append("tested_at must be an ISO date (YYYY-MM-DD) or datetime")

    if "notes" in ev and not isinstance(ev["notes"], str):
        errors.append("notes must be a string")

    return errors


def check_evidence_file(path: Path, version: str, zip_sha256: str) -> list[str]:
    """Load ``path`` and validate it; a missing/unparsable file is an error too."""
    path = Path(path)
    if not path.is_file():
        return [f"no evidence file at {path}"]
    try:
        ev = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"cannot read {path}: {exc}"]
    return [f"{path.name}: {e}" for e in validate_evidence(ev, version, zip_sha256)]


def _sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for buf in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(buf)
    return h.hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Validate evidence/<version>.json")
    ap.add_argument("version")
    ap.add_argument("--zip", help="ZIP to bind against (default: sha256 from the manifest entry)")
    ap.add_argument("--manifest", default="manifest.json")
    ap.add_argument("--evidence", help="evidence file (default: evidence/<version>.json "
                                       "next to the manifest)")
    args = ap.parse_args(argv)

    manifest_path = Path(args.manifest)
    if args.zip:
        sha = _sha256_of(Path(args.zip))
    else:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            sha = manifest["versions"][args.version]["win64"]["sha256"]
        except (OSError, ValueError, KeyError, TypeError):
            print(f"{args.version} is not in {manifest_path}; pass --zip", file=sys.stderr)
            return 1

    path = Path(args.evidence) if args.evidence else evidence_path(
        args.version, manifest_path.resolve().parent)
    errors = check_evidence_file(path, args.version, sha)
    if errors:
        print("evidence NOT valid:\n" + "\n".join(f"  - {e}" for e in errors), file=sys.stderr)
        return 1
    print(f"evidence OK: {path} admits {args.version} (sha256 {sha[:12]}...)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
