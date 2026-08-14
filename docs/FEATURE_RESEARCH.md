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

## dither-guy research

Repository researched:

https://github.com/manoelpiovesan/dither-guy

The repository is licensed under **GPL-3.0**. RasterMint's source is under a different licensing model, so no GPL implementation code was copied into RasterMint.

Useful architectural lessons observed at a high level:

- keep dithering kernels separate from GUI code;
- keep worker/media logic separate from the main window;
- handle images and videos through a shared processing concept;
- treat batch processing as a separate workflow;
- isolate palette/preset helpers;
- profile hot loops before adding acceleration layers;
- FFmpeg is useful for preserving/muxing audio after frame processing.

Feature categories that informed RasterMint's own independently written implementation include:

- more than one dithering family rather than only diffusion kernels;
- noise / advanced dithering methods;
- hue, denoise, sharpen/smooth-style processing;
- glow and other post-processing effects;
- image + video workflows;
- batch work;
- background workers;
- audio-preserving video export.

RasterMint implements these ideas through its own `effect_stack`, `animation`, `media`, `batch`, `palette`, and `dither` modules.

## Licensing boundary

Researching public behavior, file/module organization, mathematical algorithms, and public interfaces is different from copying source code. When an external implementation has an incompatible license, RasterMint should:

1. describe the desired behavior independently;
2. implement it from mathematical/public documentation or original reasoning;
3. add RasterMint-specific tests;
4. avoid copying code, comments, constants that are implementation-specific, UI assets, branding, or text;
5. record the research source in this file when it materially informs architecture.

That boundary matters if RasterMint later offers commercial licenses.

## Next research areas

Good future areas to study independently:

- perceptual/Lab palette matching and its performance tradeoffs;
- GPU preview backends that keep CPU output as the reference renderer;
- proxy-frame caches for long video;
- APNG import/export;
- more temporal threshold patterns;
- project files that keep media references, effect stack, palette metadata, and timeline together;
- installer-level Lospec custom-URI registration.
