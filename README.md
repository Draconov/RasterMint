<p align="center">
  <img src="docs/assets/rastermint-icon.png" width="120" alt="RasterMint icon">
</p>

<h1 align="center">RasterMint</h1>

<p align="center">
  A cross-platform desktop editor for dithering, palettes, retro display looks, image effects, animation, and media processing.
</p>

<p align="center">
  <a href="https://github.com/Draconov/RasterMint/actions/workflows/ci.yml"><img alt="Tests" src="https://github.com/Draconov/RasterMint/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/Draconov/RasterMint/releases/latest"><img alt="Latest release" src="https://img.shields.io/github/v/release/Draconov/RasterMint?display_name=tag&sort=semver"></a>
  <img alt="Python 3.10+" src="https://img.shields.io/badge/Python-3.10%2B-3776AB">
  <img alt="Qt Quick / QML" src="https://img.shields.io/badge/UI-Qt%20Quick%20%2F%20QML-41CD52">
</p>

RasterMint is built around a single processing pipeline: the live preview, still-image export, animation, video, presets, hardware profiles, and batch processing all use the same core rendering logic. The desktop interface is written with **PySide6 + Qt Quick/QML**, while the processing core stays independent from the UI where practical.

> **Status:** RasterMint is under active development. Project files, presets, and behavior may continue to evolve between releases.

## RasterMint 0.7.0 — Pixel Art Cleanup + Preset Mutation

RasterMint 0.7.0 adds two workflow-focused systems on top of the existing Print Lab, Modulated Diffusion, animation, palette, hardware, and display toolset:

- **Pixel Art Cleanup Lab:** a non-destructive cleanup layer with orphan-pixel removal, cluster cleanup, line repair, staircase correction, exact tiny-island removal, edge preservation, selectable 4/8-neighbour connectivity, and Clean Result / Issue Overlay / Cluster Map inspection modes. Clean output only reuses colours already present in the processed image.
- **Preset Mutation:** generate 6–12 controlled variations from any built-in, user, or extension preset, with adjustable mutation amount and current-image thumbnails. Mutations preserve the full editable layer structure, masks, blend modes, animation tracks, raster settings, and locked palette colours.

RasterMint 0.6.0 features remain part of the current release:

- **Print Lab:** non-destructive Monochrome, CMYK, RGB, and 1–8 Spot Color AM halftone screening with independent ink angles/registration/phase/opacity, dot gain, black generation, print imperfections, paper/overprint controls, individual separation preview, real vector SVG separations, raster proofs, and composite export.
- **New raster styles:** Pop Tone, Hexa-Poly, Penta-Poly, Tri-Poly, Low-Poly, and Beehive.
- **Modulated Diffusion:** the existing single **Modulation** dither now exposes 14 compact modes—Smooth Diffuse, directional/uniform modulation, Waveform variants, Ordered Modulation, Stucki/Atkinson variants, contrast-aware X/Y, Displace Contour, and Sine Wave Modulation—without cluttering the main algorithm list.
- **Modulation looks:** new Smooth Diffuse Bloom, Circuit Cyan Lines, Stucki Wire Glow, Contour Bend Glow, Waveform Scan Bloom, and animated **Particle / Star Field** presets. The star-field look is deliberately composed from RasterMint's existing Noise, Threshold, Temporal Pattern, glow/bloom, and flicker layers instead of adding a separate particle engine.
- **Display Lab:** CRT/LCD/OLED/composite/RF/VHS effects and reusable display/tape presets.
- **Layer System 2.0:** opacity, blend modes, masks, groups, solo, duplicate/reset, copy/paste and multi-selection.
- **Palette & Dither Lab:** usage analysis, sorting, ramps, near-duplicates, reduction suggestions and custom dither matrices.
- **Motion Studio:** multi-keyframe tracks, Bezier easing, reusable clips and procedural/audio modulators.
- **Projects:** `.rastermint` project files plus A/B snapshots and split comparison.
- **Performance:** per-layer render caching, safe large-image tiling and built-in stack benchmarking.
- **Extensions:** data-only packs can add palettes, themes, translations, hardware profiles and presets without modifying the application install.

## Download

Prebuilt releases are published from the `main` branch:

**[Download the latest RasterMint release](https://github.com/Draconov/RasterMint/releases/latest)**

| Platform | Release format |
| --- | --- |
| Windows | Single portable `RasterMint.exe` |
| Linux | `RasterMint-linux-x86_64.tar.gz` |
| macOS | `RasterMint-macOS.zip` |

The Windows release intentionally remains a **single executable**. The build uses a trimmed PyInstaller payload, a lean FFmpeg build, and lazy loading of the heavy image-processing stack to reduce startup overhead while preserving offline media support.

## What RasterMint does

### Dithering and palettes

- Quantization, ordered, error-diffusion, and advanced dithering families.
- Built-in palette library with searchable categories and palette metadata.
- Editable colors, locks, shuffle/randomize tools, and source-image palette extraction.
- Palette extraction with Median Cut, K-Means, Octree, and Wu-style quantization.
- Palette import from HEX/text, GIMP `.gpl`, and JASC `.pal` files.
- Lospec palette import by slug or URL using the documented palette JSON endpoint.
- Custom gradient generation using **RGB, Linear RGB, OKLab, HSV, and HSL** interpolation.
- Built-in gradient presets that can be applied directly as the active image palette.
- **Pop Tone**, polygon-cell (**Hexa/Penta/Tri/Low-Poly**), and **Beehive** structural raster effects for palette-bounded stylization beyond ordinary ordered/error-diffusion dithering.
- A single **Modulation** algorithm with 14 modulation-aware diffusion modes and shared Strength, Scale, Phase, Bias, Contour Detail, Seed, and Serpentine controls. Modulation stays palette-bounded and its numeric controls can be animated through Motion Studio.
- **Pixel Art Cleanup** for orphan pixels, weak clusters, broken lines, stair-step burrs, tiny connected islands, and edge-preserving cleanup, plus diagnostic issue/cluster visualization.

### Preset exploration

**Preset Mutation** can generate 6–12 nearby editable variations from any preset. It keeps the source stack structure intact while making bounded changes to suitable numeric parameters, layer opacity, and unlocked palette colours. Generated variants use the current source image for thumbnails and can be applied, edited, animated, or saved like any normal RasterMint settings.

See [`docs/PIXEL_ART_CLEANUP.md`](docs/PIXEL_ART_CLEANUP.md) and [`docs/PRESET_MUTATION.md`](docs/PRESET_MUTATION.md) for the detailed workflows.

### Layer-based image processing

RasterMint uses a reorderable effect stack. Layers can be enabled, bypassed, duplicated, reordered, grouped, soloed, or removed. Each layer can use opacity, a blend mode, and a procedural mask.

Available processing includes color adjustments, local contrast, blur, sharpen, glow, bloom, chromatic effects, posterization, dithering, text/pixel effects, and a dedicated **Display Effects** lab for CRT/LCD/OLED/composite/RF/VHS simulation including temporal persistence.

### Print Lab

RasterMint's ordinary Halftone algorithm remains available for fast aesthetic dithering. **Print Lab** is a separate editable layer/workflow for real color-separation screening.

- Monochrome, CMYK, RGB, and 1–8 Spot Color modes.
- Independent ink color, screen angle, X/Y registration, phase, and opacity.
- Round, ellipse, square, diamond, and line screen geometry.
- Dot gain, black generation, registration error, roughness, weak ink, spread, paper grain, and squeegee artifacts.
- Paper color plus subtractive overprint/ink mixing.
- Composite or individual-separation inspection.
- Dedicated export of actual vector SVG screens, grayscale raster proofs, and a composite PNG.

See [`docs/PRINT_LAB.md`](docs/PRINT_LAB.md) for the workflow and export details.

### Raster and retro-hardware workflows

- Exact target raster controls with Fit, Fill, and Stretch placement.
- Crop, flip, rotation, mirror axes, and pixel-aspect handling.
- Data-driven hardware profiles for retro systems and display styles.
- Separate **Visual** and **Strict** profile behavior where meaningful image-space constraints can be represented safely.
- Optional raster, palette, pixel-aspect, limit, and display components per profile.

Hardware profiles are creative image-processing models, **not hardware emulators**.

### Animation and media

- Parameter animation on the same layer stack used for still images.
- Multi-keyframe tracks with easing/Bezier curves, reusable clips, and procedural/audio modulators.
- Quick playback and rendered-preview caching for expensive effects.
- Animated GIF and common video input through FFmpeg.
- MP4, GIF, and numbered PNG-sequence export where applicable.
- Optional source-audio preservation for supported video exports.

### Workflow and interface

- Drag-and-drop, normal file opening, or **Paste Image from Clipboard** / Ctrl+V.
- Pan, zoom, fit-to-view, and automatic high-zoom pixel grid.
- Quick, Stable, and Full preview modes.
- Background rendering with stale-result protection.
- Undo/redo with grouped slider and drag interactions.
- Optional mouse-wheel slider control and render-debounced slider updates for expensive stacks.
- Batch export with format, scaling, overwrite, and per-source sizing controls.
- Direct **Export to Clipboard** for pasting the processed image into another application without a temporary file.
- Compact icon-based inspector navigation with grouped sections and translated hover labels.
- `.rastermint` project files, A/B snapshots/split comparison, searchable preset library, themes, translations, and data-driven hardware profiles.
- **14 built-in application themes**, including Studio Gray, Midnight, Violet, Amber, and Hacker.
- Runtime localization for **12 languages** (English plus Ukrainian, French, German, Spanish, Portuguese, Italian, Hebrew, Arabic, Polish, Irish, and Latvian) with live switching. First run/reset follows the supported system language and otherwise falls back to English.

## Supported formats

RasterMint relies on Pillow for still-image formats and FFmpeg for media formats.

**Common input:** PNG, JPEG, WebP, BMP, TIFF, GIF, MP4, MOV, MKV, WebM, AVI, and other formats supported by the bundled decoding stack.

**Still export:** PNG, JPEG, WebP, BMP, TIFF, and SVG.

**Print Lab separation export:** vector SVG per ink, grayscale PNG proof per ink, plus composite PNG.

**Motion export:** MP4, animated GIF, and numbered PNG sequences where supported by the source/workflow.

Exact codec support can vary by platform build. Official Windows releases validate the bundled FFmpeg against RasterMint's required H.264, AAC, RGB-pipe, PNG, and GIF workflows during CI.

## Quick start

1. Download the release for your platform.
2. Open RasterMint.
3. Drop an image, GIF, or video onto the canvas, or use **File → Open**.
4. Choose a palette and dithering algorithm.
5. Add/reorder effects, set a raster or hardware profile, open Print Lab when making separations, and adjust the preview.
6. Export normal media from the **File** menu, or use **Print Lab → Output → Export Separations…** for individual ink screens.

RasterMint does not require an online account. Network access is only needed for features that explicitly fetch remote content, such as Lospec palette import.

## Development

### Requirements

- Python **3.10+**
- Git
- Platform build tools when creating packaged releases

### Setup

```bash
git clone https://github.com/Draconov/RasterMint.git
cd RasterMint
python -m venv .venv
```

Activate the environment, then install development dependencies:

```bash
python -m pip install -e ".[dev,build]"
```

Run the desktop app:

```bash
python launcher.py
```

Run the test suite:

```bash
python -m pytest
```

Run a syntax/bytecode sanity check:

```bash
python -m compileall -q src tests
```

Convenience setup/run scripts are available under `scripts/` for Windows, Linux, and macOS.

## Command-line interface

Installing the project exposes `rastermint-cli`.

```bash
rastermint-cli input.png output.png --palette Ink --algorithm Floyd-Steinberg
```

Example with a target raster and hardware profile:

```bash
rastermint-cli input.png output.png \
  --hardware-profile game-boy \
  --hardware-mode strict \
  --width 160 --height 144
```

Run `rastermint-cli --help` for the complete option list.

## Project structure

```text
src/rastermint/
├── app.py                 Qt application bootstrap
├── cli.py                 Command-line entry point
├── core/                  Processing, media, palettes, animation, hardware
├── data/                  Themes, translations, palettes, presets, icons, hardware profiles
├── qml/                   Qt Quick interface
└── qmlui/                 QML-facing models, backend, theme/localization, workers, image provider

build/                     PyInstaller specification and packaging hooks
docs/                      Developer and architecture documentation
scripts/                   Development/build/validation scripts
tests/                     Core, regression, packaging, and QML smoke tests
```

The GUI startup path is intentionally lightweight. NumPy, Pillow, the render pipeline, and media modules are deferred until processing or export actually needs them.

## Documentation

| Document | Purpose |
| --- | --- |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Runtime architecture, processing pipeline, UI boundary, workers, packaging |
| [`docs/PRINT_LAB.md`](docs/PRINT_LAB.md) | AM-halftone modes, ink controls, separation preview/export, and implementation boundaries |
| [`docs/EXTENDING_RASTERMINT.md`](docs/EXTENDING_RASTERMINT.md) | How to add effects, dithering, palettes, profiles, animation, and UI features |
| [`docs/HARDWARE_PROFILES.md`](docs/HARDWARE_PROFILES.md) | Hardware-profile format and Visual/Strict behavior |
| [`docs/TESTING.md`](docs/TESTING.md) | Test strategy, QML smoke tests, regression-test policy |
| [`docs/FEATURE_RESEARCH.md`](docs/FEATURE_RESEARCH.md) | External feature research and implementation policy |
| [`docs/ICONS.md`](docs/ICONS.md) | Application and sidebar icon assets, tinting, and packaging |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Contribution workflow and project expectations |
| [`CHANGELOG.md`](CHANGELOG.md) | Release history |

## Builds and releases

GitHub Actions builds Windows, Linux, and macOS artifacts from `main`. Tests run on Linux with Qt in offscreen/software-rendering mode before the release job is allowed to complete.

The version is stored in the root [`VERSION`](VERSION) file and exposed through the Python package/build metadata.

Windows packaging uses PyInstaller one-file mode. RasterMint's custom packaging hooks intentionally exclude unused Qt feature families and prevent the stock `imageio-ffmpeg` hook from bundling a second FFmpeg executable.

## Contributing

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) before proposing code changes. Processing changes should preserve the shared-pipeline contract and include focused tests. UI changes should pass the real offscreen QML compile/runtime suite rather than relying only on source-text checks.

## Third-party software

Third-party components and notices are documented in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## License

RasterMint is available for noncommercial use under the terms in [`LICENSE`](LICENSE). Commercial licensing information is available in [`COMMERCIAL-LICENSE.md`](COMMERCIAL-LICENSE.md).

Copyright © 2026 Draconov.

