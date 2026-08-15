# RasterMint Architecture

RasterMint keeps processing code independent from Qt. The GUI builds immutable-ish `ProcessingSettings` snapshots, then sends those snapshots to worker jobs. Export uses the same core functions as the viewport.

## High-level flow

```text
Image / decoded GIF/video frame
        ↓
Source transform (crop · flip · rotate)
        ↓
Target framebuffer raster (exact size / legacy divisor)
        ↓
Optional interactive mirror axis
        ↓
Reorderable effect stack
        ├─ adjustments / local contrast / color
        ├─ spatial / glitch / material / text effects
        ├─ pixelate
        └─ dither / palette quantization
        ↓
Optional strict hardware constraints
        ↓
Raw framebuffer
        ↓
Pixel-aspect correction / display simulation
        ↓
Processed RGB frame
        ├─ live viewport
        ├─ raster export
        ├─ SVG run-vectorization
        ├─ animation / GIF encoder
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
core/processor.py      source transform, target raster, preview proxies, final orchestration
core/hardware.py       data-driven hardware constraints, pixel aspect, display/grid
core/svg_export.py     horizontal-run SVG conversion
core/batch.py          multi-image processing
core/media.py          GIF + FFmpeg-backed timed-media/still-animation I/O
core/presets.py        human-editable JSON preset serialization
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

Animation targets use stable effect IDs:

```text
effect:<effect-id>:<parameter>
```

`EFFECT_DEFINITIONS` is the capability source. Numeric parameters are timeline-compatible unless they are random/identity seeds; the UI therefore does not maintain a second animation-property list. `settings_at_time()` groups tracks by target, supports sequential segments on one parameter, applies easing, and clamps interpolated values back to the effect schema.

Dither exposes a dedicated `mix` parameter. The renderer skips dithering entirely at mix 0, renders normally at mix 1, and blends the clean/dithered images in between. Built-in motion recipes live in `core/animation_presets.py`; they add missing effects when necessary and generate ordinary tracks, so the result remains serializable in normal RasterMint presets.

Playback has two paths:

```text
Quick
 timeline → current settings_at_time → draft preview worker → viewport

Rendered
 settings + source → background frame-cache worker → cached PIL frames → viewport
```

Timeline movement has its own revision counter so an old asynchronous Quick frame cannot overwrite a newer time without invalidating a valid Rendered cache.

## Video

`core/media.py` speaks to FFmpeg through `imageio-ffmpeg` subprocess pipes rather than making the image core depend on a native video binding. Normal Quick playback background-seeks a frame and sends it through the standard processor. Rendered video preview decodes a short segment sequentially, processes preview proxies, and caches the results.

```text
source video
   ↓ FFmpeg decode
RGB frame bytes
   ↓ same RasterMint processing pipeline
processed RGB frame
   ├─→ cached rendered preview
   ├─→ numbered PNG sequence
   └─→ FFmpeg encode → optional source-audio mux → MP4
```

PNG-sequence export exists for both still-image animation and timed media. It intentionally writes lossless full-resolution processed PNGs and does not share the Rendered Preview resolution cap.

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
ui/lospec_dialog.py        async palette API request + fetched swatch preview
ui/target_raster_widget.py exact raster / PAR / display controls
ui/source_transform_widget.py crop / fill position
ui/hardware_panel.py       data-driven Visual/Strict profile controls
ui/image_view.py           pan/zoom/drop + automatic high-zoom pixel grid + draggable mirror axes
ui/worker.py               QRunnable jobs
```

## Packaging

`VERSION` is the only version source. `pyproject.toml` uses dynamic version metadata from that file. PyInstaller copies RasterMint package metadata and bundles the platform FFmpeg executable supplied by `imageio-ffmpeg` when available.

See `THIRD_PARTY_NOTICES.md` before redistributing binaries.


## Desktop inspector

The desktop UI is intentionally separated from the renderer. The main window contains only the menu bar, central preview, and a two-column inspector. The inspector's left column selects a general area; the right column hosts the existing specialized editor widget. Processing effects are presented to users as **layers** while the core retains the `effect_stack` compatibility field used by presets and older code.

`Pixel Aspect Ratio` is also available as an image-space layer. This is distinct from framebuffer/display pixel-aspect metadata in the Raster and Hardware systems: the layer participates in image processing order, while the framebuffer PAR describes presentation geometry.

## Stability guards

Interactive Full preview is memory-bounded for unusually large rasters; final export remains full resolution. Rendered animation preview caches are capped to avoid retaining hundreds of megabytes to more than a gigabyte of Pillow frames. The main window stops timers, clears queued worker jobs, and briefly waits for running work during shutdown. Frozen GUI builds enable `faulthandler` and write uncaught exceptions/fatal diagnostics to the platform app-data `crash.log`.
