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


def _with_version_key(key):
    """Good manifest whose single version is keyed `key` (tag/asset kept consistent)."""
    m = _good_manifest()
    entry = m["versions"].pop("150.0.7871.101")
    entry["tag"] = f"v{key}"
    entry["win64"]["asset"] = f"huligan-chrome-{key}-win64.zip"
    m["versions"][key] = entry
    m["latest"] = key
    return m


@pytest.mark.parametrize("key", ["150", "150.0.7871", "v150.0.7871.101", "150.0.7871.101-beta",
                                 "150.0.7871.x", "150.0.7871.101\n", "150..7871.101"])
def test_malformed_version_key_flagged(key):
    errors = vm.validate_manifest(_with_version_key(key))
    assert any("X.Y.Z.W" in e for e in errors), errors


def test_channels_pointing_at_published_versions_pass():
    m = _good_manifest()
    m["channels"] = {"stable": "150.0.7871.101", "latest": "150.0.7871.101", "beta": None}
    assert vm.validate_manifest(m) == []


def test_dangling_channel_flagged():
    m = _good_manifest()
    m["channels"] = {"stable": "150.0.7871.101", "latest": "151.0.0.0"}
    errors = vm.validate_manifest(m)
    assert any("channels.latest" in e for e in errors)
    assert not any("channels.stable" in e for e in errors)


def test_channels_must_be_object():
    m = _good_manifest()
    m["channels"] = ["150.0.7871.101"]
    assert any("'channels'" in e for e in vm.validate_manifest(m))


def test_non_string_channel_target_flagged():
    m = _good_manifest()
    m["channels"] = {"stable": 150}
    assert any("channels.stable" in e for e in vm.validate_manifest(m))


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


def test_publish_rejects_non_zip(tmp_path):
    fake = tmp_path / "huligan-chrome-151.0.7900.1-win64.zip"
    fake.write_bytes(b"this is not a zip")
    with pytest.raises(ValueError, match="not a ZIP"):
        publish.publish("151.0.7900.1", fake, tmp_path / "manifest.json",
                        set_latest=False, released="2026-07-20")


def test_publish_rejects_zip_without_chrome_exe(tmp_path):
    z = tmp_path / "huligan-chrome-151.0.7900.1-win64.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("huligan-chrome-151.0.7900.1/chrome.dll", b"x")
        zf.writestr("a/b/chrome.exe", b"x")   # too deep: SDK lifts only one folder
    with pytest.raises(ValueError, match="chrome.exe"):
        publish.publish("151.0.7900.1", z, tmp_path / "manifest.json",
                        set_latest=False, released="2026-07-20")


def test_publish_accepts_chrome_exe_under_top_folder(tmp_path):
    z = tmp_path / "huligan-chrome-151.0.7900.1-win64.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("huligan-chrome-151.0.7900.1/chrome.exe", b"x")  # real packager layout
    out = publish.publish("151.0.7900.1", z, tmp_path / "manifest.json",
                          set_latest=True, released="2026-07-20")
    assert out["latest"] == "151.0.7900.1"


def test_publish_refuses_different_sha_for_existing_version(tmp_path, fake_zip):
    mpath = tmp_path / "manifest.json"
    mpath.write_text(json.dumps(_good_manifest()), encoding="utf-8")  # 150 has sha "a"*64
    rebuilt = tmp_path / "huligan-chrome-150.0.7871.101-win64.zip"
    rebuilt.write_bytes(fake_zip.read_bytes())
    with pytest.raises(ValueError, match="new version"):
        publish.publish("150.0.7871.101", rebuilt, mpath,
                        set_latest=False, released="2026-07-20")


def test_publish_same_zip_again_is_idempotent(tmp_path, fake_zip):
    mpath = tmp_path / "manifest.json"
    mpath.write_text(json.dumps(_good_manifest()), encoding="utf-8")
    first = publish.publish("151.0.7900.1", fake_zip, mpath,
                            set_latest=False, released="2026-07-20")
    mpath.write_text(json.dumps(first), encoding="utf-8")
    again = publish.publish("151.0.7900.1", fake_zip, mpath,
                            set_latest=True, released="2026-07-20")  # e.g. just promoting
    assert again["versions"]["151.0.7900.1"] == first["versions"]["151.0.7900.1"]
    assert again["latest"] == "151.0.7900.1"


def test_cli_refuses_overwrite_and_leaves_manifest(tmp_path, fake_zip, capsys):
    mpath = tmp_path / "manifest.json"
    mpath.write_text(json.dumps(_good_manifest()), encoding="utf-8")
    before = mpath.read_text(encoding="utf-8")
    rc = publish.main(["150.0.7871.101", "--zip", str(fake_zip), "--manifest", str(mpath)])
    assert rc == 1
    assert mpath.read_text(encoding="utf-8") == before
    assert "new version" in capsys.readouterr().err


def test_cli_missing_zip_errors(tmp_path, capsys):
    mpath = tmp_path / "manifest.json"
    mpath.write_text(json.dumps(_good_manifest()), encoding="utf-8")
    rc = publish.main([
        "151.0.7900.1", "--zip", str(tmp_path / "nope.zip"),
        "--manifest", str(mpath),
    ])
    assert rc == 1
