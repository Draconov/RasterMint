# RasterMint

<p align="center">
  <img src="docs/assets/rastermint-icon.png" width="128" alt="RasterMint icon">
</p>

**Author:** [Draconov](https://github.com/Draconov)

RasterMint is a cross-platform desktop image, palette, dithering, and motion-effects playground. It is built around one rule: the live viewport, still export, animation export, video export, presets, and batch processor all use the same processing pipeline.

## Highlights

- Custom app icon bundled for Windows (`.ico`), macOS (`.icns`), Linux/runtime PNG, and the README.

- PySide6 / Qt 6 desktop UI for Windows, Linux, and macOS.
- One **Open File** action plus drag-and-drop for still images, animated GIFs, and videos.
- One processed viewport with pan, zoom, and fit-to-view.
- Three preview behaviors:
  - **Live** — quick draft first, then a refined render after controls settle.
  - **Still** — skips the draft and refreshes after editing pauses.
  - **Full** — renders the selected output resolution in the viewport when you explicitly want maximum preview accuracy.
- Background rendering with serialized preview jobs and stale-frame rejection.
- Adaptive preview budgets for especially expensive algorithms and very large palettes.
- Visual preset carousel with current-image thumbnails for quick look browsing.
- Searchable/categorized palette browser with color-strip previews and hover descriptions.
- 67 built-in retro/hardware palette entries, with representative/approximation labeling where a machine did not have one universal fixed game palette.
- Previous/next palette controls and previous/next controls around choice parameters such as dithering algorithms.
- Palette interpolation generator supporting OKLab, RGB, Linear RGB, HSV, and HSL ramps from 2 to 256 colors.
- Hardware profile details are shown as hover tooltips in the profile selector instead of occupying permanent panel space.
- Reorderable, bypassable, duplicatable **layer stack** for image effects and image-space presentation layers.
- 26 dithering / quantization algorithms across quantization, ordered, error-diffusion, and advanced families.
- Up to 256 palette colors.
- Built-in palettes, editable swatches, per-color locks, shuffle/randomize-unlocked tools, and optimized source-image palette extraction using Median Cut, K-Means, Octree, or Wu-style quantization.
- Lospec fetch results show the actual palette swatches before import.
- **Lospec palette integration** using Lospec's official per-palette JSON endpoint: open the Lospec Palette List, paste a palette slug or URL, and import its colors plus attribution.
- `.hex`, text/HEX, GIMP `.gpl`, and JASC `.pal` palette import; HEX palette export.
- Preset save/load including processing layers, palette metadata/locks, and animation tracks.
- Still-image animation with parameter tracks, per-track timing, easing, enable/bypass, and live timeline preview.
- Animated GIF and video import, scrubbing, quick processed playback, GIF/MP4 export where applicable, and source-audio preservation for normal video when FFmpeg can mux it.
- MP4 and animated GIF export from a still image.
- PNG, JPEG, WebP, BMP, TIFF, and SVG export for current processed frames.
- Batch image processing.
- Single-version-file release system: edit only `VERSION`.
- Rolling GitHub releases on every push to `main` for Windows, Linux, and macOS.

## Interface

RasterMint uses a minimal top menu bar and a two-column inspector on the right. The left inspector column selects a general area such as **Layers**, **Palette**, **Raster**, or **Hardware**; the right column shows the detailed controls for that area. Image mirroring/flipping/rotation is also available under **Edit → Image Manipulation**, and **Edit → Settings** contains application settings plus the final **Reset Settings** action.

Preview quality is intentionally named **Quick**, **Stable**, and **Full** while retaining the existing draft/refine/full rendering behavior.

## Dithering algorithms

### Quantization / threshold

- Nearest Palette
- Threshold
- Random
- Interleaved Gradient Noise
- Blue Noise

### Ordered / pattern

- Bayer 2×2
- Bayer 4×4
- Bayer 8×8
- Bayer 16×16
- Bayer 32×32
- Clustered Dot 4×4
- Clustered Dot 8×8
- Halftone

### Error diffusion

- Floyd–Steinberg
- False Floyd–Steinberg
- Jarvis–Judice–Ninke
- Stucki
- Atkinson
- Burkes
- Sierra
- Sierra Two-Row
- Sierra Lite
- Stevenson–Arce
- Shiau–Fan

### Advanced

- Dot Diffusion
- Riemersma

## Layer stack

Layers are processed top-to-bottom. Reordering image-processing layers changes the output.

Current nodes:

- Adjustments: brightness, contrast, saturation, gamma
- Local Contrast / unsharp-mask enhancement
- Hue Rotate
- Grayscale
- Invert
- Gaussian Blur
- Median Denoise
- Sharpen
- Glow
- JPEG Compression
- Chromatic Shift / RGB Split
- Posterize
- Scanlines / Interlace
- Noise, including frame-varying noise
- Temporal Flicker and **Temporal Pattern** (Pulse, axis/diagonal waves, checker phase, scan sweep, noise drift, alternating frames, radial pulse)
- Pixel Sort, Screen Melt, Block Shuffle, Pixel Scatter, Data Shift, Row/Column Shift, Cellular Automata, Databend-style processing, Channel Swap
- Pixelate
- Pixel Material: Flat, dots, CRT phosphor, LED/LCD, fuse bead, cross stitch, brick, mosaic, halftone, ASCII tile, custom sprite
- Text Overlay
- Dither

Each row can be enabled/disabled, reordered, duplicated, or removed. User-adjustable numeric parameters marked as animatable can be driven by the animation system; while an enabled animation track controls a parameter, its normal effect editor is locked to avoid conflicting input.

## Animation

RasterMint treats motion as parameter animation on the same processing layer stack used by still images. All suitable numeric effect parameters are published to the timeline automatically (identity/random seeds are excluded). A true **Dither Mix** parameter makes 0% the clean pre-dither image and 100% the complete dithered result, so Dither In/Out transitions are real crossfades rather than changes to diffusion error only.

The Animation panel now includes:

- start/end and previous/next-frame transport;
- loop playback;
- track add/update/duplicate/remove;
- From/To, Start/End, easing, and per-track enable;
- **Quick playback** for live low-resolution processing;
- **Rendered playback** that caches preview-resolution frames before smooth playback;
- built-in motion presets: Dither In, Dither Out, Dither In/Out, Glow Pulse, Hue Sweep, CRT Flicker, Pixelate In, Chromatic Pulse, and Temporal Wave.

Sequential tracks can target the same parameter. Between track segments RasterMint holds the previous segment's final value, making multi-stage animations such as in→hold→out predictable.

Export options include MP4, animated GIF, and a numbered **PNG sequence**. Frame-dependent effects receive time/frame context so temporal noise, flicker, and temporal patterns reproduce consistently between preview and export.

## Video

Video support is provided through `imageio-ffmpeg` / FFmpeg. RasterMint keeps media decoding separate from image processing: each decoded RGB frame travels through the same effect/hardware/palette pipeline as a still image.

The Source panel supports:

- frame scrubbing;
- Quick processed playback;
- a **Rendered 5 s Preview** cache for smooth inspection of expensive stacks;
- 0.5× / 1× / 1.5× / 2× preview speed;
- loop on/off;
- optional source-audio preservation for MP4 export;
- processed MP4/GIF paths where applicable;
- full processed PNG-sequence export.

Quick playback intentionally uses a smaller proxy budget. Rendered preview caches a short preview-resolution segment. Final exports and PNG sequences always use the selected output resolution. For broad H.264/yuv420p compatibility, odd output dimensions are padded by one replicated edge pixel to the next even dimension.

## Lospec palettes

Open **Palette → Lospec…** in RasterMint's palette section, click **Browse Lospec**, then paste either:

```text
greyt-bit
```

or:

```text
https://lospec.com/palette-list/greyt-bit
```

RasterMint requests:

```text
https://lospec.com/palette-list/<slug>.json
```

and stores the returned palette name, author, colors, and source URL in the current settings/preset. The integration uses Lospec's documented palette API rather than scraping the website.

Lospec remains a separate service; palette availability and network access are outside RasterMint's control.

## Source transform, target raster, and hardware profiles

RasterMint treats framebuffer geometry as a first-class control. Before the layer stack you can crop, rotate, flip, choose Fit/Fill/Stretch positioning, and select an exact target raster such as 160×144, 240×160, 256×224, 320×200, 320×240, or 640×480.

Pixel aspect ratio is separate from framebuffer resolution. The viewport can show:

```text
Raw framebuffer
Corrected pixels
Display simulation
```

Built-in data-driven hardware profiles can selectively apply raster, palette/color depth, pixel aspect ratio, image-space hardware limits, and display treatment. Profiles support **Visual** and **Strict** modes; Strict mode is a still-image constraint approximation, not console/computer emulation. See [`docs/HARDWARE_PROFILES.md`](docs/HARDWARE_PROFILES.md).

The legacy `÷1 … ÷16` output divisor remains supported by old presets and the CLI, but the desktop UI now prefers exact target raster controls.

## Grid, random exploration, and presets

A pixel grid can be enabled independently for preview and export with minor/major spacing. Creative Randomize has independent locks for palette, dither, effects, raster, and parameters plus Previous/Next history so a good random state is not lost. Presets serialize the complete processing state, including target raster, transforms, hardware snapshot, display settings, effect stack, palette metadata/locks, animation tracks, grid, and random locks.

## Development setup

### Windows PowerShell

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev,build]"
rastermint
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e '.[dev,build]'
rastermint
```

Or:

```bash
python -m rastermint
```

## CLI

Basic processing:

```bash
rastermint-cli input.png output.png \
  --algorithm "Atkinson" \
  --palette "Graphite 4" \
  --pixel-size 2 \
  --downscale 2
```

Custom colors:

```bash
rastermint-cli input.png output.png \
  --colors "#111827" "#F59E0B" "#F9FAFB"
```

Palette file:

```bash
rastermint-cli input.png output.png --palette-file palette.gpl
```

Lospec palette:

```bash
rastermint-cli input.png output.png --lospec greyt-bit
```

Exact raster / hardware profile example:

```bash
rastermint-cli input.png output.png --width 320 --height 200 --fit fill --pixel-aspect 5:6 --display corrected
rastermint-cli input.png output.png --hardware-profile game-boy --hardware-mode strict
```

SVG current-frame export also works from the CLI by using an `.svg` output name.

## Developer documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — current processing, preview, animation, and media architecture.
- [`docs/EXTENDING_RASTERMINT.md`](docs/EXTENDING_RASTERMINT.md) — adding algorithms, effects, palettes, animation parameters, and tests.
- [`docs/HARDWARE_PROFILES.md`](docs/HARDWARE_PROFILES.md) — profile schema, Visual/Strict modes, pixel aspect, constraints, and display treatment.
- [`docs/FEATURE_RESEARCH.md`](docs/FEATURE_RESEARCH.md) — Lospec API notes and RasterMint's independent-implementation policy.

## Tests

```bash
pytest
```

Core tests do not require opening a Qt window. Media tests automatically skip only when no FFmpeg executable is available.

## Versioning

`VERSION` is the single source of truth:

```text
0.1.0
```

To publish a different version, edit **only** that file. Package metadata, the runtime application version, macOS bundle metadata, and the rolling release workflow derive from it.

## Builds and rolling GitHub releases

Local builds:

```powershell
.\scripts\build_windows.ps1
```

```bash
bash scripts/build_linux.sh
bash scripts/build_macos.sh
```

Release assets:

```text
RasterMint.exe
RasterMint-linux-x86_64.tar.gz
RasterMint-macOS.zip
```

`.github/workflows/release.yml` builds all three platforms on every push to `main`. After all builds succeed, the workflow creates or refreshes `v<VERSION>`, moves that version tag to the successful commit, and replaces the existing application assets. Manual **Run workflow** is kept as a rebuild fallback and follows the same behavior.

## Third-party software

RasterMint's own source license does not replace the licenses of its dependencies. See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md), especially before commercial binary distribution.

## License

RasterMint is source-available for noncommercial use under the [PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0). Commercial use outside the permissions of that license requires a separate commercial license from Draconov.

Copyright © 2026 Draconov. See `LICENSE` and `COMMERCIAL-LICENSE.md`.
