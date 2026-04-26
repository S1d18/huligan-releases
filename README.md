# Huligan Chrome Binary Mirror

Distribution mirror for the patched Chromium binary used by
[huligan-sdk](https://github.com/S1d18/huligan-sdk). This repository
holds release archives only — there is no source code here.

The SDK auto-downloads the matching build on first `Browser()` call and
caches it at `~/.huligan/chrome/{version}/`, so end users normally never
visit this repo manually.

## Manual download

Each tagged release exposes:

| File | Purpose |
|------|---------|
| `huligan-chrome-{version}-win64.zip` | Chromium build (~180 MB) |
| `huligan-chrome-{version}-win64.zip.sha256` | SHA-256 checksum |

Verify before extracting:

```bash
sha256sum -c huligan-chrome-147.0.7727.56-win64.zip.sha256
```

## Manifest

`manifest.json` lists known versions, their assets, and checksums.
Useful for tools that pin or audit binaries without parsing the GitHub
API.

## Source

The Chromium patch set that produces these binaries is not public.
The Python SDK that drives the browser is at
[huligan-sdk](https://github.com/S1d18/huligan-sdk).
