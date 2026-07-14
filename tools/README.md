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

# 2. once you're confident, promote and commit
python tools/publish.py 151.0.7900.1 --set-latest --commit
```

- **sha256 must match the uploaded asset** — the SDK verifies the download
  against it. Compute from the same file you upload.
- `latest` moves **only** with `--set-latest`. Farms/checkers on the `latest`
  channel never pick up an unvalidated build.
- `min_conf_schema` defaults to the current max. Pass `--min-conf-schema N` only
  when the build requires a new `.conf` key (bump it in lockstep with
  `huligan-sdk` `conf_spec.CONF_SCHEMA_VERSION`) — older SDKs then refuse the
  build instead of launching a degraded fingerprint.
- `--dry-run` previews the resulting manifest without writing.

## Validate

```bash
python tools/validate_manifest.py            # checks manifest.json
python -m pytest tools/test_manifest_tools.py -q
```

The `validate-manifest` GitHub Action runs both on every PR that touches the
manifest or these tools.
