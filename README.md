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

### Layer-based image processing

RasterMint uses a reorderable effect stack. Layers can be enabled, bypassed, duplicated, reordered, or removed.

Available processing includes color adjustments, local contrast, blur, sharpen, glow, bloom, chromatic effects, posterization, scanlines, temporal effects, glitch processing, pixel sorting, pixel materials, text overlays, pixelation, dithering, and more.

### Raster and retro-hardware workflows

- Exact target raster controls with Fit, Fill, and Stretch placement.
- Crop, flip, rotation, mirror axes, and pixel-aspect handling.
- Data-driven hardware profiles for retro systems and display styles.
- Separate **Visual** and **Strict** profile behavior where meaningful image-space constraints can be represented safely.
- Optional raster, palette, pixel-aspect, limit, and display components per profile.

Hardware profiles are creative image-processing models, **not hardware emulators**.

### Animation and media

- Parameter animation on the same layer stack used for still images.
- Timeline tracks with easing, start/end timing, duplication, enable/bypass, and presets.
- Quick playback and rendered-preview caching for expensive effects.
- Animated GIF and common video input through FFmpeg.
- MP4, GIF, and numbered PNG-sequence export where applicable.
- Optional source-audio preservation for supported video exports.

### Workflow and interface

- Drag-and-drop or normal file opening.
- Pan, zoom, fit-to-view, and automatic high-zoom pixel grid.
- Quick, Stable, and Full preview modes.
- Background rendering with stale-result protection.
- Undo/redo with grouped slider and drag interactions.
- Batch export with format, scaling, overwrite, and per-source sizing controls.
- JSON presets, themes, and data-driven hardware profiles.
- Multiple built-in application themes.

## Supported formats

RasterMint relies on Pillow for still-image formats and FFmpeg for media formats.

**Common input:** PNG, JPEG, WebP, BMP, TIFF, GIF, MP4, MOV, MKV, WebM, AVI, and other formats supported by the bundled decoding stack.

**Still export:** PNG, JPEG, WebP, BMP, TIFF, and SVG.

**Motion export:** MP4, animated GIF, and numbered PNG sequences where supported by the source/workflow.

Exact codec support can vary by platform build. Official Windows releases validate the bundled FFmpeg against RasterMint's required H.264, AAC, RGB-pipe, PNG, and GIF workflows during CI.

## Quick start

1. Download the release for your platform.
2. Open RasterMint.
3. Drop an image, GIF, or video onto the canvas, or use **File → Open**.
4. Choose a palette and dithering algorithm.
5. Add/reorder effects, set a raster or hardware profile, and adjust the preview.
6. Export from the **File** menu.

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
├── data/                  Themes, palettes, presets, icons, hardware profiles
├── qml/                   Qt Quick interface
└── qmlui/                 QML-facing models, backend, workers, image provider

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
| [`docs/EXTENDING_RASTERMINT.md`](docs/EXTENDING_RASTERMINT.md) | How to add effects, dithering, palettes, profiles, animation, and UI features |
| [`docs/HARDWARE_PROFILES.md`](docs/HARDWARE_PROFILES.md) | Hardware-profile format and Visual/Strict behavior |
| [`docs/TESTING.md`](docs/TESTING.md) | Test strategy, QML smoke tests, regression-test policy |
| [`docs/FEATURE_RESEARCH.md`](docs/FEATURE_RESEARCH.md) | External feature research and implementation policy |
| [`docs/ICONS.md`](docs/ICONS.md) | Application icon assets and packaging |
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
