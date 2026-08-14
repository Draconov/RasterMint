# RasterMint

**Author:** [Draconov](https://github.com/Draconov)

RasterMint is a desktop image-processing playground focused on palette reduction, classic dithering, pixel scaling, and fast visual experimentation.

## Current feature set

- Native desktop GUI with PySide6 / Qt 6.
- Drag-and-drop and file-dialog image loading.
- Original and processed views with pan, zoom, and fit-to-view.
- Debounced live preview processed on background worker threads.
- Full-resolution background export.
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
- Brightness, contrast, saturation, gamma, dither strength, pixel size, and serpentine scan controls.
- Save/load `.rmpreset` JSON presets.
- PNG, JPEG, WebP, BMP, and TIFF export.
- Command-line processor for automation.
- Cross-platform PyInstaller build scripts.
- GitHub Actions CI and tagged release workflow.

## Requirements

- Python 3.10 or newer.
- Windows 10/11, a modern Linux desktop, or macOS.

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
  --strength 1.0
```

Custom palette:

```bash
rastermint-cli input.png output.png \
  --algorithm "Floyd-Steinberg" \
  --colors "#111827" "#F59E0B" "#F9FAFB"
```

## Tests

```bash
pytest
```

The core tests do not require opening a GUI window.

## Local release builds

Install build dependencies first:

```bash
pip install -e '.[build]'
```

Then use the platform script:

- Windows: `scripts\build_windows.bat` or `scripts\build_windows.ps1`
- Linux: `./scripts/build_linux.sh`
- macOS: `./scripts/build_macos.sh`

Packaged artifacts are written to `release/`.

## GitHub releases

`.github/workflows/ci.yml` runs tests on pushes and pull requests.

`.github/workflows/release.yml` builds Windows, Linux, and macOS packages whenever a tag matching `v*` is pushed. Example:

```bash
git tag v0.1.0
git push origin v0.1.0
```

The workflow verifies that the git tag matches the version in `pyproject.toml` and `src/rastermint/__init__.py`, uploads the platform packages as workflow artifacts, and creates a GitHub Release for the tag.

## Project layout

```text
RasterMint/
├─ .github/workflows/       CI and release builds
├─ build/                   PyInstaller spec
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

## Notes on performance

Error-diffusion algorithms are inherently sequential because each output pixel affects later pixels. RasterMint therefore uses a reduced preview source for interactive work and processes the original image only for export. Ordered and nearest-palette modes are vectorized with NumPy.

## License

RasterMint is **source-available for noncommercial use** under the
[PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0).
Commercial use outside the permissions of that license requires a separate commercial license from Draconov.

Copyright © 2026 Draconov. See `LICENSE` and `COMMERCIAL-LICENSE.md`.
