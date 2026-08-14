# Feature Research Notes

This document records external interfaces and architecture ideas researched for RasterMint. It is here so future work has traceable sources without copying third-party implementation code.

## Lospec Palette List

Official pages:

- Palette List: https://lospec.com/palette-list
- Palette API documentation: https://lospec.com/palettes/api

Lospec documents a per-palette JSON endpoint:

```text
https://lospec.com/palette-list/<slug>.json
```

The response contains a palette name, author, and array of hex colors. RasterMint uses that documented endpoint directly. It does **not** scrape the Palette List HTML.

Current RasterMint integration:

1. User opens the Lospec import dialog.
2. **Browse Lospec** opens the Palette List in the default browser.
3. User pastes a slug or full palette URL.
4. RasterMint requests the official JSON endpoint asynchronously through Qt networking.
5. Name, author, source URL, and colors are preserved in current settings/presets.

Lospec also documents an "Open in Software" custom-URI workflow. Portable RasterMint releases do not currently register an OS-wide URI handler because that normally belongs in an installer/package integration step. The core slug importer is intentionally separated so URI registration can be added later without changing palette parsing.

## Independent implementation policy

RasterMint can study public mathematical descriptions, file formats, product behavior, and general software architecture, but implementation code, UI assets, branding, and implementation-specific text from unrelated applications are not copied into this repository. New algorithms and effects are implemented independently and protected by RasterMint-specific regression tests.

## Next research areas

Good future areas to study independently:

- perceptual/Lab palette matching and its performance tradeoffs;
- GPU preview backends that keep CPU output as the reference renderer;
- proxy-frame caches for long video;
- APNG import/export;
- more temporal threshold patterns;
- project files that keep media references, effect stack, palette metadata, and timeline together;
- installer-level Lospec custom-URI registration.
