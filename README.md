# RasterMint

**Author:** [Draconov](https://github.com/Draconov)

RasterMint is a desktop image-processing playground focused on palette reduction, classic dithering, pixel scaling, and fast visual experimentation.

## Current feature set

- Native desktop GUI with PySide6 / Qt 6.
- Drag-and-drop directly onto the preview plus file-dialog loading.
- Single processed preview with pan, zoom, and fit-to-view; the app does not waste time drawing a second original viewport.
- Debounced, serialized background previews capped at 640 px on the longest side.
- Full-size background export when output size is set to Original.
- Output downscale control from Original through `÷16`; scaling happens before processing for large speed gains.
- Optimized exact scalar error-diffusion engine for the remaining kernels.
- 16 processing modes:
  - Nearest Palette
  - Threshold
  - Random
  - Bayer 2×2
  - Bayer 4×4
  - Bayer 8×8
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
- Arbitrary 1–32 color palettes.
- Built-in palettes and editable swatches.
- Palette extraction from the loaded image using median-cut quantization.
- Brightness, contrast, saturation, gamma, dither strength, pixel size, and optional serpentine scan.
- Save/load `.rmpreset` JSON presets.
- PNG, JPEG, WebP, BMP, and TIFF export.
- Command-line processor for automation.
- Single-file Windows release build.

## Requirements

- Python 3.10 or newer for source development.
- Windows 10/11 for the current GitHub binary release.

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

You can also run the module directly:

```bash
python -m rastermint
```

## CLI

```bash
rastermint-cli input.png output.png \
  --algorithm "Atkinson" \
  --palette "Graphite 4" \
  --pixel-size 2 \
  --downscale 2 \
  --strength 1.0
```

`--downscale 1` preserves the input dimensions. `--downscale 2` outputs half the width and height, `3` outputs one third, and so on through `16`.

Custom palette:

```bash
rastermint-cli input.png output.png \
  --algorithm "Floyd-Steinberg" \
  --colors "#111827" "#F59E0B" "#F9FAFB"
```

Serpentine error diffusion is optional:

```bash
rastermint-cli input.png output.png --serpentine
```

Serpentine scanning remains enabled by default for compatibility with previous RasterMint output.

## Tests

```bash
pytest
```

The core tests do not require opening a GUI window.

## Local Windows release build

```powershell
.\scripts\build_windows.ps1
```

The result is exactly:

```text
release/RasterMint.exe
```

PyInstaller one-file builds temporarily unpack their embedded dependencies when the program starts, so a single EXE can start a little more slowly than the old EXE + `_internal` folder layout. Rendering performance after startup is independent of that packaging choice.

## Manual GitHub release

`.github/workflows/ci.yml` runs one test job on normal pushes and pull requests.

Releases are manual:

1. Open **Actions** in the repository.
2. Select **Release**.
3. Click **Run workflow**.
4. Enter `v0.1.0` (the application version remains 0.1.0).
5. Run the workflow.

The release workflow runs on Windows, verifies the tests, builds a one-file PyInstaller executable, and uploads **only `RasterMint.exe`** as the custom GitHub Release asset. GitHub itself also shows its automatic `Source code (zip)` / `Source code (tar.gz)` links for tagged releases; those are not extra build artifacts from RasterMint.

## Project layout

```text
RasterMint/
├─ .github/workflows/       CI and manual Windows release
├─ build/                   PyInstaller one-file spec
├─ scripts/                 local setup/build scripts
├─ src/rastermint/
│  ├─ core/                 algorithms, palettes, presets, processing
│  ├─ ui/                   Qt widgets and worker jobs
│  ├─ app.py                GUI entry point
│  └─ cli.py                CLI entry point
├─ tests/                   core regression tests
├─ launcher.py              PyInstaller launcher
├─ pyproject.toml
└─ README.md
```

## License

RasterMint is **source-available for noncommercial use** under the
[PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0).
Commercial use outside the permissions of that license requires a separate commercial license from Draconov.

Copyright © 2026 Draconov. See `LICENSE` and `COMMERCIAL-LICENSE.md`.
