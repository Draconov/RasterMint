# Extending RasterMint

RasterMint is split into a Qt-free core and a PySide6 UI. New rendering behavior should normally be implemented and tested in `src/rastermint/core/` first, then exposed to the UI through the existing schemas/settings.

## Current pipeline

```text
input image / decoded GIF/video frame
   ↓
source transform + exact target framebuffer
   ↓
ordered effect stack
   ↓
optional hardware constraints
   ↓
pixel-aspect/display/grid presentation
   ↓
preview / still export / SVG / animation / video / batch
```

The stack, not `main_window.py`, defines rendering order.

## Adding an error-diffusion algorithm

Edit `src/rastermint/core/dither.py` and add an entry to `ERROR_DIFFUSION_KERNELS`:

```python
"My Diffusion": (
    [
        (1, 0, 4),
        (-1, 1, 1),
        (0, 1, 2),
        (1, 1, 1),
    ],
    8,
),
```

Each kernel entry is `(dx, dy, weight)` and the second tuple value is the divisor. Error-diffusion names are included in the public algorithm list automatically.

Then run:

```bash
pytest tests/test_dither.py
```

The regression suite verifies that every public algorithm emits only selected palette colors and that the optimized classic diffusion engine matches its simple reference implementation.

## Adding an ordered matrix

Add the matrix to `BAYER_MATRICES` or `CLUSTERED_MATRICES`. Public ordered algorithms are derived from these registries, so the Dither effect's algorithm choice updates automatically.

```python
BAYER_MATRICES["My Ordered 4x4"] = np.array(..., dtype=np.float32)
```

## Adding a standalone dithering family

For a method that is not a diffusion kernel or ordered matrix:

1. write a pure core function taking an RGB NumPy image and palette array;
2. return an `H×W×3` array;
3. ensure final values are selected palette colors when the algorithm is advertised as palette dithering;
4. add the name to the appropriate `ALGORITHM_GROUPS` category;
5. dispatch it from `apply_dither()`;
6. run the all-algorithms tests.

Do not put Qt code in `dither.py`.

## Adding an effect-stack node

Effects are described in `EFFECT_DEFINITIONS` inside `core/effect_stack.py`.

Example:

```python
"My Effect": {
    "params": {
        "amount": {
            "type": "float",
            "label": "Amount",
            "default": 0.5,
            "min": 0.0,
            "max": 1.0,
            "step": 0.05,
            "decimals": 2,
            "animatable": True,
        }
    }
}
```

Supported schema types are currently:

```text
int
float
bool
choice
text
color
file
```

Useful flags:

- `animatable: True` — makes the numeric parameter available in the animation target list.
- `pixel_scaled: True` — scales spatial values for reduced preview proxies so blur/offset/pixel spacing looks proportionally similar to export.

Then add the processing branch in `apply_effect_stack()`.

The UI parameter editor is generated from this schema; you should **not** create a second hard-coded form in `main_window.py` for normal stack effects.

## Animation compatibility

Animation targets use:

```text
effect:<effect-id>:<param>
```

If a numeric effect parameter has `animatable: True`, `animatable_targets()` publishes it automatically. The animation panel can then create From/To tracks with Start/End times and easing.

When adding an animatable parameter:

- choose meaningful min/max ranges;
- make sure fractional animation into integer values is safe (`settings_at_time()` rounds integer parameters);
- do not animate booleans/choice values through numeric tracks;
- test a mid-animation value.

## Adding a temporal effect

Temporal effects receive:

```python
frame_time
frame_index
```

through `apply_effect_stack()`. A deterministic temporal effect should derive its changing state from one or both values rather than global random state. This makes a given frame reproducible during preview and export.

## Adding a built-in palette

Add a hex RGB list to `BUILTIN_PALETTES` in `core/palette.py`:

```python
"My Palette": ["#101820", "#F2AA4C", "#F7F7F7"]
```

The GUI and CLI built-in selectors consume that registry.

## Palette file support

`read_palette_file()` currently understands:

- `.hex` / generic text containing six-digit hex colors;
- GIMP `.gpl`;
- JASC `.pal`.

Add format parsing in `core/palette.py`, not in the Qt file dialog.

## Lospec integration

The core parser is in `core/lospec.py`; the asynchronous Qt request dialog is in `ui/lospec_dialog.py`.

Keep these responsibilities separate:

```text
core/lospec.py       URL/slug validation + JSON parsing + optional synchronous fetch
ui/lospec_dialog.py  non-blocking QNetworkAccessManager request + user feedback
```

Do not scrape Lospec's Palette List HTML when the official per-palette JSON endpoint can be used.

## Preview performance

Every effect automatically participates in preview because preview calls the same `process_image()` function with a reduced source.

Spatial parameters should use `pixel_scaled: True`. CPU-heavy algorithms can be added to `adaptive_preview_max_side()` so only their interactive proxy is reduced; explicit Full preview and export must remain unchanged.

Before adding a dependency or compiled acceleration layer:

1. benchmark the real hot loop;
2. optimize allocations/vectorization first;
3. keep deterministic CPU output as a reference where practical;
4. add regression tests before changing the implementation.

## Video-compatible effects

An effect is video-compatible if it can process an individual PIL RGB frame without reading the source file itself. That is the preferred design: media decoding stays in `core/media.py`, while frame processing stays in the image core.

## SVG behavior

`core/svg_export.py` vectorizes the already-processed raster result. If you add a different vectorization strategy, keep it separate from dithering so PNG/video output is unaffected.

## Batch behavior

`core/batch.py` processes inputs sequentially using one settings snapshot. If parallel batch processing is added later, use a bounded worker count; multiple full-resolution diffusion jobs can consume significant CPU and RAM.

## Hardware profiles

Hardware profiles live under `src/rastermint/data/hardware_profiles/` and are loaded by `core/hardware.py`. Add new machines as data rather than profile-name branches in Qt code. See [`HARDWARE_PROFILES.md`](HARDWARE_PROFILES.md) for the JSON contract and strict-mode rules.

A custom profile should be conservative about what it labels Strict. Image-space palette, bit-depth, global-color, and tile/attribute limits are appropriate; CPU/PPU scheduling or analog electrical behavior is not implemented by the profile engine.

## GIF compatibility

Animated GIF is treated as timed media. Frame timing/decoding belongs in `core/media.py`; effects continue to process ordinary PIL RGB frames. GIF-to-GIF export preserves per-frame source durations, while still-image animation can also export GIF.

## Checklist

For a new rendering feature:

- [ ] implement in `src/rastermint/core/`;
- [ ] put user state in a serializable effect parameter or `ProcessingSettings` field;
- [ ] validate/clamp values;
- [ ] ensure preset round-trip works;
- [ ] ensure preview and export call the same implementation;
- [ ] mark spatial values `pixel_scaled` where appropriate;
- [ ] mark numeric timeline-compatible values `animatable` where appropriate;
- [ ] add CLI support when useful;
- [ ] add tests;
- [ ] run `python -m compileall -q src tests`;
- [ ] run `pytest`;
- [ ] test all release platforms through GitHub Actions before treating packaging as final.

## Palette library and visual presets

The built-in searchable palette catalog lives in `core/palette_library.py`. Add a `PaletteRecord` with a unique ID/name, category, colors, and a short description. Hardware that does not have one universal fixed palette should be described as a representative/creative subset rather than presented as a strict master palette.

`interpolate_palette()` is the shared 2–256 color ramp generator. The UI currently exposes OKLab, RGB, Linear RGB, HSV, and HSL interpolation.

Visual quick presets live in `core/builtin_presets.py`. Keep them small in number and visually distinct; their thumbnails are rendered from the current source image in low-priority worker jobs.

Hardware profile details belong in the profile JSON `summary`/palette description fields. The GUI surfaces that information through hover tooltips, so profile descriptions should be concise enough to read without a separate information page.
