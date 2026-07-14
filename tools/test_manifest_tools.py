"""Tests for the manifest publish/validate tools.

Run: python -m pytest tools/test_manifest_tools.py -q
(The tools dir is put on sys.path so the sibling imports resolve.)
"""

import hashlib
import json
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

import publish  # noqa: E402
import validate_manifest as vm  # noqa: E402


REPO_MANIFEST = Path(__file__).resolve().parents[1] / "manifest.json"


def _good_manifest():
    return {
        "schema_version": 1,
        "latest": "150.0.7871.101",
        "platforms": ["win64"],
        "versions": {
            "150.0.7871.101": {
                "tag": "v150.0.7871.101",
                "released": "2026-07-10",
                "min_conf_schema": 1,
                "win64": {
                    "asset": "huligan-chrome-150.0.7871.101-win64.zip",
                    "size": 194193762,
                    "sha256": "a" * 64,
                },
            }
        },
    }


# --- validator ------------------------------------------------------------

def test_real_manifest_is_valid():
    data = json.loads(REPO_MANIFEST.read_text(encoding="utf-8"))
    assert vm.validate_manifest(data) == []


def test_good_manifest_passes():
    assert vm.validate_manifest(_good_manifest()) == []


def test_latest_must_exist():
    m = _good_manifest()
    m["latest"] = "999.0.0.0"
    assert any("latest" in e for e in vm.validate_manifest(m))


def test_wrong_tag_flagged():
    m = _good_manifest()
    m["versions"]["150.0.7871.101"]["tag"] = "v149"
    assert any(".tag" in e for e in vm.validate_manifest(m))


def test_wrong_asset_name_flagged():
    m = _good_manifest()
    m["versions"]["150.0.7871.101"]["win64"]["asset"] = "wrong.zip"
    assert any(".asset" in e for e in vm.validate_manifest(m))


def test_bad_sha_flagged():
    m = _good_manifest()
    m["versions"]["150.0.7871.101"]["win64"]["sha256"] = "XYZ"
    assert any("sha256" in e for e in vm.validate_manifest(m))


def test_missing_min_conf_schema_flagged():
    m = _good_manifest()
    del m["versions"]["150.0.7871.101"]["min_conf_schema"]
    assert any("min_conf_schema" in e for e in vm.validate_manifest(m))


def test_bool_min_conf_schema_rejected():
    m = _good_manifest()
    m["versions"]["150.0.7871.101"]["min_conf_schema"] = True  # bool is not a valid int here
    assert any("min_conf_schema" in e for e in vm.validate_manifest(m))


# --- publish --------------------------------------------------------------

@pytest.fixture
def fake_zip(tmp_path):
    z = tmp_path / "huligan-chrome-151.0.7900.1-win64.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("chrome.exe", b"binary-bytes")
    return z


def test_sha256_of_matches_hashlib(fake_zip):
    expected = hashlib.sha256(fake_zip.read_bytes()).hexdigest()
    assert publish.sha256_of(fake_zip) == expected


def test_build_entry_shape(fake_zip):
    entry = publish.build_entry("151.0.7900.1", fake_zip, 1, "2026-07-20")
    assert entry["tag"] == "v151.0.7900.1"
    assert entry["min_conf_schema"] == 1
    assert entry["win64"]["asset"] == "huligan-chrome-151.0.7900.1-win64.zip"
    assert entry["win64"]["size"] == fake_zip.stat().st_size
    assert entry["win64"]["sha256"] == hashlib.sha256(fake_zip.read_bytes()).hexdigest()


def test_publish_adds_entry_without_promoting(tmp_path, fake_zip):
    mpath = tmp_path / "manifest.json"
    mpath.write_text(json.dumps(_good_manifest()), encoding="utf-8")

    out = publish.publish("151.0.7900.1", fake_zip, mpath,
                          set_latest=False, released="2026-07-20")
    assert "151.0.7900.1" in out["versions"]
    assert out["latest"] == "150.0.7871.101"  # unchanged
    assert vm.validate_manifest(out) == []


def test_publish_carries_min_conf_schema(tmp_path, fake_zip):
    m = _good_manifest()
    m["versions"]["150.0.7871.101"]["min_conf_schema"] = 3
    mpath = tmp_path / "manifest.json"
    mpath.write_text(json.dumps(m), encoding="utf-8")

    out = publish.publish("151.0.7900.1", fake_zip, mpath,
                          set_latest=True, released="2026-07-20")
    assert out["versions"]["151.0.7900.1"]["min_conf_schema"] == 3  # carried forward
    assert out["latest"] == "151.0.7900.1"


def test_publish_from_empty_manifest(tmp_path, fake_zip):
    mpath = tmp_path / "manifest.json"  # does not exist
    out = publish.publish("151.0.7900.1", fake_zip, mpath,
                          set_latest=True, released="2026-07-20")
    assert out["latest"] == "151.0.7900.1"
    assert out["schema_version"] == 1
    assert vm.validate_manifest(out) == []


def test_cli_dry_run_writes_nothing(tmp_path, fake_zip, capsys):
    mpath = tmp_path / "manifest.json"
    mpath.write_text(json.dumps(_good_manifest()), encoding="utf-8")
    before = mpath.read_text(encoding="utf-8")

    rc = publish.main([
        "151.0.7900.1", "--zip", str(fake_zip),
        "--manifest", str(mpath), "--released", "2026-07-20", "--dry-run",
    ])
    assert rc == 0
    assert mpath.read_text(encoding="utf-8") == before  # untouched
    assert "151.0.7900.1" in capsys.readouterr().out


def test_cli_writes_manifest(tmp_path, fake_zip):
    mpath = tmp_path / "manifest.json"
    mpath.write_text(json.dumps(_good_manifest()), encoding="utf-8")

    rc = publish.main([
        "151.0.7900.1", "--zip", str(fake_zip), "--set-latest",
        "--manifest", str(mpath), "--released", "2026-07-20",
    ])
    assert rc == 0
    data = json.loads(mpath.read_text(encoding="utf-8"))
    assert data["latest"] == "151.0.7900.1"
    assert vm.validate_manifest(data) == []


def test_cli_missing_zip_errors(tmp_path, capsys):
    mpath = tmp_path / "manifest.json"
    mpath.write_text(json.dumps(_good_manifest()), encoding="utf-8")
    rc = publish.main([
        "151.0.7900.1", "--zip", str(tmp_path / "nope.zip"),
        "--manifest", str(mpath),
    ])
    assert rc == 1
