# Architecture

RasterMint is split into a Qt-free processing core and a PySide6 presentation layer.

## Processing flow

```text
PIL input image
   ↓
brightness / contrast / saturation / gamma
   ↓
preview resize or pixel-size downsample
   ↓
NumPy RGB float32 array
   ↓
palette quantization + selected dither
   ↓
uint8 RGB image
   ↓
nearest-neighbor upscale when pixel-size > 1
   ↓
PIL output image
```

## Core

- `core/settings.py`: serializable processing state.
- `core/palette.py`: color conversion, nearest-palette mapping, built-in palettes, palette extraction.
- `core/dither.py`: ordered, stochastic, threshold, nearest, and error-diffusion processing.
- `core/processor.py`: adjustment and processing pipeline.
- `core/presets.py`: versioned JSON preset format.

The core intentionally has no Qt imports. It is used by both the GUI and CLI and can be unit-tested headlessly.

## UI

- `ui/main_window.py`: application state, controls, file IO, export, preset actions.
- `ui/image_view.py`: zoom/pan graphics view.
- `ui/palette_editor.py`: palette swatch editing.
- `ui/worker.py`: background render tasks.
- `ui/style.py`: application stylesheet.

Preview jobs are generation-numbered. If an old preview completes after a newer one, the old result is discarded instead of flashing stale state into the viewport.

## Adding an error-diffusion algorithm

Add a new entry to `ERROR_DIFFUSION_KERNELS` in `core/dither.py`:

```python
"My Algorithm": (
    [(1, 0, 4), (-1, 1, 1), (0, 1, 3)],
    8,
),
```

The tuple is `(kernel, divisor)`. Kernel entries are `(dx, dy, weight)`.

Then run:

```bash
pytest
```

The algorithm will automatically appear in the GUI and CLI because `ALGORITHMS` is built from the registered kernels.

## Adding a built-in palette

Add a named hex-color list to `BUILTIN_PALETTES` in `core/palette.py`. It will automatically become available in the palette drop-down and CLI.
