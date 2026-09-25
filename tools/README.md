# tools/ — manifest publishing

`manifest.json` is the contract the huligan-sdk resolver reads to pick a Chrome
build (version + sha256 + `min_conf_schema`). These scripts keep it correct and
remove hand-editing.

## Publish a new build

After a patched-Chrome build passes validation (BrowserScan 100%×2, CreepJS
no-lies) and its zip is uploaded to the GitHub Release `v{version}`:

```bash
# 1. add the entry from the exact zip you uploaded (does NOT promote to latest)
python tools/publish.py 151.0.7900.1 --zip /path/huligan-chrome-151.0.7900.1-win64.zip

# 2. after the validation gate: write evidence/151.0.7900.1.json, then promote and commit
python tools/publish.py 151.0.7900.1 --zip /path/huligan-chrome-151.0.7900.1-win64.zip --set-latest --commit
```

- **sha256 must match the uploaded asset** — the SDK verifies the download
  against it. Compute from the same file you upload.
- The input must be a ZIP with `chrome.exe` at the root or under one top-level
  folder. A version already in the manifest with a **different** sha256 is
  refused: a rebuilt binary gets a new version (re-running with the same zip,
  e.g. only to `--set-latest`, is fine).
- `latest` moves **only** with `--set-latest`. Farms/checkers on the `latest`
  channel never pick up an unvalidated build.
- `min_conf_schema` defaults to the current max. Pass `--min-conf-schema N` only
  when the build requires a new `.conf` key (bump it in lockstep with
  `huligan-sdk` `conf_spec.CONF_SCHEMA_VERSION`) — older SDKs then refuse the
  build instead of launching a degraded fingerprint.
- `--dry-run` previews the resulting manifest without writing.

## Release evidence gate (`--set-latest`)

`--set-latest` is refused unless `evidence/<version>.json` exists and admits the
**exact ZIP** being published. Without `--set-latest` the entry is still written,
but `publish.py` prints a `WARNING` when that evidence is missing or invalid.

Required fields (validator: `tools/evidence.py:validate_evidence`; example:
[`docs/evidence.example.json`](../docs/evidence.example.json)):

| field | rule |
|---|---|
| `version` | equals the version being published |
| `zip_sha256` | 64 lowercase hex, equals sha256 of the `--zip` being published |
| `browserscan_score` | number, **≥ 97** (operator's visual read, headed, real proxy) |
| `creepjs_lies` | integer, **must be 0** (headed, `--cdp-port 0`) |
| `ja4_matches_stock` | `true` — JA4 equals branded stock Chrome of the same major |
| `tested_at` | ISO date `YYYY-MM-DD` (or ISO datetime) |
| `notes` | string — who/how, link to the `этап4_validation_gate.md` run log |

Thresholds are the project's validation gate (BrowserScan ≥ 97 %, CreepJS
lies 0). The numbers must come from the operator's **visual** read of a headed
window — the CDP scraper reports false 100 %. Never write evidence for a build
nobody validated; a rebuilt ZIP (new sha) needs new evidence.

```bash
# after the gate: fill evidence/151.0.7900.1.json, then check it against the zip
python tools/evidence.py 151.0.7900.1 --zip /path/huligan-chrome-151.0.7900.1-win64.zip
python tools/publish.py 151.0.7900.1 --zip /path/huligan-chrome-151.0.7900.1-win64.zip --set-latest --commit
```

`--evidence PATH` overrides the default location (`evidence/<version>.json`
next to the manifest). Commit the evidence file together with the manifest
change. Versions published before the gate existed have no evidence; promoting
one of them back to `latest` (rollback) needs an evidence file written from its
recorded validation run.

**Rollback.** `--set-latest --rollback` moves `latest` back to a version that is
*already* in the manifest with the same ZIP sha256, without evidence (builds
published before the gate have none). Any other bytes still need evidence.

```bash
python tools/publish.py 152.0.7977.65 --zip builds/huligan-chrome-152.0.7977.65-win64.zip --set-latest --rollback --commit
```

## Validate

```bash
python tools/validate_manifest.py            # checks manifest.json
python -m pytest tools/test_manifest_tools.py -q
```

The `validate-manifest` GitHub Action runs both on every PR that touches the
manifest or these tools.
