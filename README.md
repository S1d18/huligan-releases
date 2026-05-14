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

## License

The Binary distributed through this repository is governed by the
**custom End-User License Agreement** in [`LICENSE.txt`](LICENSE.txt).
By downloading or using any release artifact, you agree to those terms.

Key points (read `LICENSE.txt` for the full text):

- ✅ Free for personal and commercial use on hardware you control
- ❌ **No redistribution.** You may not mirror, repackage, or re-host
  the Binary, modified or unmodified, anywhere outside this repository
- ❌ **No SaaS bundling.** Building a browser-as-a-service, scraping-
  as-a-service, or similar offering on top of the Binary requires a
  separate commercial license
- ❌ **No reverse engineering** of the patches applied on top of
  Chromium, except where mandatory law allows
- ⚠️  Provided "AS IS" — no warranty of undetectability now or in the
  future; detection-bypass behavior may change without notice

The Huligan **SDK** that drives this binary
([huligan-sdk](https://github.com/S1d18/huligan-sdk)) is a separate
component licensed under **Apache 2.0**. Apache 2.0 does **not**
govern this Binary.

The underlying Chromium upstream is BSD-3-Clause; upstream notices are
preserved in the Binary (visible at `chrome://credits`).

> "Huligan" is an unregistered trademark of the Huligan Project.

**Legal contact:** _to be provided — see [`LEGAL_TODO.md`](LEGAL_TODO.md)._
Until a contact email is published here, written notices to Licensor
are not yet possible; the Licensor will not enforce time-bound notice
requirements (e.g. the 30-day prior notice under Section 3(c) of the
EULA) against any party before this address is published.
