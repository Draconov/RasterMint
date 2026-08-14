# Architecture

RasterMint is split into a Qt-free processing core and a PySide6 presentation layer.

## Processing flow

```text
PIL input image
   ↓
optional output downscale (÷1 … ÷16)
   ↓
brightness / contrast / saturation / gamma
   ↓
optional pixel-size downsample
   ↓
selected dithering / palette quantization
   ↓
nearest-neighbor pixel upscale when pixel-size > 1
   ↓
PIL output image
```

Interactive previews represent the selected final output size and are capped at 640 pixels on the longest side. The preview source is cached per output divisor; the full input image is retained for export and palette extraction.

## Performance design

RasterMint deliberately avoids rendering a second copy of the original image in the GUI. The viewport contains only the processed preview.

Preview jobs are debounced and serialized: at most one preview render is actively consuming CPU. If settings change while a preview is running, RasterMint remembers only the newest pending state and renders that next instead of filling the thread pool with obsolete work.

All error-diffusion kernels use an optimized exact engine with nearest-palette math on a flat float buffer, avoiding tiny NumPy allocations inside the per-pixel loop while preserving the previous diffusion output.

Output downscaling happens before adjustments and dithering. Choosing `÷2` processes one quarter as many final pixels; `÷4` processes one sixteenth as many final pixels.

## Core

- `core/settings.py`: serializable processing state, including output divisor.
- `core/palette.py`: color conversion, nearest-palette mapping, built-in palettes, palette extraction.
- `core/dither.py`: ordered, stochastic, threshold, nearest, and optimized error-diffusion processing.
- `core/processor.py`: output resizing, adjustments, preview sizing, and processing pipeline.
- `core/presets.py`: versioned JSON preset format.

The core intentionally has no Qt imports. It is used by both the GUI and CLI and can be unit-tested headlessly.

## UI

- `ui/main_window.py`: application state, controls, drag/drop, file IO, export, preset actions, preview scheduling.
- `ui/image_view.py`: processed preview with drop target, zoom, pan, and fit-to-view.
- `ui/palette_editor.py`: palette swatch editing.
- `ui/worker.py`: background render tasks without unnecessary source-image copies.
- `ui/style.py`: application stylesheet.

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

The algorithm automatically appears in the GUI and CLI because `ALGORITHMS` is built from the registered kernels.

## Adding a built-in palette

Add a named hex-color list to `BUILTIN_PALETTES` in `core/palette.py`. It automatically becomes available in the palette drop-down and CLI.
