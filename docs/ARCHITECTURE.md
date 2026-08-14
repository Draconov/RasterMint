# RasterMint Architecture

RasterMint keeps processing code independent from Qt. The GUI builds immutable-ish `ProcessingSettings` snapshots, then sends those snapshots to worker jobs. Export uses the same core functions as the viewport.

## High-level flow

```text
Image / decoded video frame
        ↓
Output resize (÷1 … ÷16)
        ↓
Reorderable effect stack
        ├─ adjustments / color
        ├─ spatial filters
        ├─ glitch / display effects
        ├─ pixelate
        └─ dither / palette quantization
        ↓
Processed RGB frame
        ├─ live viewport
        ├─ raster export
        ├─ SVG run-vectorization
        ├─ animation encoder
        ├─ video encoder
        └─ batch output
```

## Core modules

```text
core/settings.py       serialized project/preset state
core/dither.py         dithering algorithms and diffusion kernels
core/effect_stack.py   effect definitions, validation, ordering, execution
core/animation.py      track validation, easing, parameter interpolation
core/palette.py        palette parsing, extraction, mapping, file I/O
core/lospec.py         official Lospec per-palette JSON integration
core/processor.py      output scaling and preview proxy sizing
core/svg_export.py     horizontal-run SVG conversion
core/batch.py          multi-image processing
core/media.py          FFmpeg-backed video/still-animation I/O
core/presets.py        .rmpreset serialization
```

## Effect stack contract

An effect is plain serializable data:

```json
{
  "id": "dither",
  "kind": "Dither",
  "enabled": true,
  "params": {
    "algorithm": "Floyd-Steinberg",
    "strength": 1.0,
    "threshold": 0.5,
    "serpentine": true
  }
}
```

`EFFECT_DEFINITIONS` in `core/effect_stack.py` is the schema consumed by both the core validator and the dynamic Qt parameter form. That prevents the UI and renderer from having separate definitions of parameter ranges/defaults.

The processing order is literally list order. Dragging a row changes that list order. Disabled rows remain in presets but are bypassed at render time.

## Live preview

RasterMint has three UI preview behaviors:

### Live

```text
control change
   ↓ short debounce
fast draft proxy (normally ≤320 px)
   ↓ once editing settles
refined proxy (normally ≤640 px)
```

### Still

The draft is skipped. A refined proxy is generated after input settles.

### Full

The viewport processes the selected output resolution. This is intentionally optional because full-resolution error diffusion or video frames can be expensive.

### Adaptive budgets

`adaptive_preview_max_side()` further reduces only the interactive proxy for particularly expensive algorithms such as Dot Diffusion/Riemersma and for large palettes combined with per-pixel diffusion. It never changes export resolution and never reduces an explicit Full request.

### Stale result protection

Only one preview render is active at a time. If controls change during a render, RasterMint records the newest pending quality request instead of filling the thread pool with obsolete jobs.

Each worker also carries:

- source revision;
- settings revision;
- preview quality/budget.

If a worker finishes after its source/settings revision became obsolete, its result is discarded.

## Animation

Animation tracks target effect parameters by stable effect ID:

```text
effect:<effect-id>:<parameter>
```

Example:

```text
effect:glow:intensity
```

A track contains:

```json
{
  "target": "effect:glow:intensity",
  "from": 0.1,
  "to": 0.8,
  "start": 0.5,
  "end": 3.0,
  "easing": "Ease In Out",
  "enabled": true
}
```

`settings_at_time()` clones settings and applies all enabled tracks for a requested time. Preview/export therefore share the same interpolation logic. Numeric parameters under enabled tracks are disabled in the normal effect editor while animated.

## Video

`core/media.py` intentionally speaks to FFmpeg through `imageio-ffmpeg` subprocess pipes rather than making the image core depend on a native video binding.

```text
source video
   ↓ FFmpeg decode
RGB frame bytes
   ↓ PIL / RasterMint pipeline
processed RGB frame
   ↓ FFmpeg encode
video-only MP4
   ↓ optional audio mux from source
final MP4
```

The viewport seeks frames in background workers. Quick playback is capped to a practical preview frame rate and uses draft proxies; final video export processes every decoded frame at the selected output size.

## Palettes

RasterMint stores palettes as hex RGB strings and allows up to 256 entries. `quantize_nearest()` uses chunked matrix algebra to avoid allocating an enormous height×width×palette×RGB tensor for larger palettes.

Lospec integration stores both colors and attribution metadata:

```text
palette_name
palette_author
palette_source
```

These fields survive presets.

## SVG export

Current SVG export vectorizes horizontal runs of identical output pixels into `<rect>` elements with `shape-rendering="crispEdges"`. It is exact for the processed raster appearance, not an attempt to reconstruct semantic vector shapes from the original photo.

## Batch

Batch processing clones one settings snapshot across multiple input images. It currently writes PNG outputs sequentially; this avoids multiple full-resolution diffusion jobs competing for memory/CPU.

## UI layer

```text
ui/main_window.py          application coordination and worker scheduler
ui/effect_stack_widget.py  reorder/bypass/duplicate + dynamic parameter editor
ui/animation_panel.py      timeline and parameter-track editing
ui/palette_editor.py       swatches, locks, shuffle/randomization
ui/lospec_dialog.py        async palette API request
ui/image_view.py           pan/zoom/drop viewport
ui/worker.py               QRunnable jobs
```

## Packaging

`VERSION` is the only version source. `pyproject.toml` uses dynamic version metadata from that file. PyInstaller copies RasterMint package metadata and bundles the platform FFmpeg executable supplied by `imageio-ffmpeg` when available.

See `THIRD_PARTY_NOTICES.md` before redistributing binaries.
