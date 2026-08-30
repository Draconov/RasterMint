# RasterMint Architecture

RasterMint separates the desktop interface from the processing engine while keeping **one shared rendering pipeline** for preview and export. This document describes the current runtime architecture and the invariants that should remain stable as the project grows.

## Design goals

1. **One processing truth** — preview and export should differ only in resolution/performance policy, not image-processing logic.
2. **Responsive UI** — expensive image/media work runs away from the QML event loop.
3. **Fast startup** — Qt can create the first window without eagerly importing NumPy, Pillow, FFmpeg/media helpers, or the complete render pipeline.
4. **Data-driven features** — palettes, themes, translations, presets, hardware profiles, effect schemas, and algorithm metadata should not require UI-specific branching.
5. **Deterministic exports** — final output should not inherit preview-only shortcuts.

## Runtime overview

```text
launcher.py
    ↓
rastermint.app
    ↓
QGuiApplication + QML engine
    ↓
qmlui backend / models / image provider
    ↓
worker jobs
    ↓
core processing pipeline
    ↓
preview image provider or export writer
```

The GUI and CLI both rely on `src/rastermint/core/`. Qt-specific state belongs under `qmlui/`; processing code should not require a Qt application.

## Startup path

GUI startup is intentionally split into a lightweight phase and an on-demand processing phase.

```text
Python
  ↓
minimal PySide6 modules
  ↓
QGuiApplication
  ↓
lightweight QML backend + theme + localization + image provider
  ↓
Main.qml becomes visible
  ↓
heavy processing/media imports only when needed
```

`rastermint.app` imports the QML backend only after `QGuiApplication` exists. The backend and worker modules avoid top-level imports of heavy processing modules. NumPy, Pillow, media/FFmpeg helpers, and the render stack are loaded inside the operations that need them.

This boundary is protected by `tests/test_startup_optimization.py`.

## Processing pipeline

The conceptual still/frame path is:

```text
source image / decoded RGB frame
    ↓
source transforms
(crop · flip · rotate · mirror)
    ↓
target raster placement
(Fit · Fill · Stretch)
    ↓
reorderable effect stack
    ↓
hardware graphics constraints (optional)
    ↓
logical framebuffer
    ↓
pixel-aspect correction (optional)
    ↓
display treatment (optional)
    ↓
preview / still export / animation frame / video frame / batch output
```

The same `ProcessingSettings` model and core functions are used across workflows. Preview may use a smaller source/proxy; final export must use the requested output dimensions and full processing rules.

## Core modules

The main responsibilities under `src/rastermint/core/` are:

| Module | Responsibility |
| --- | --- |
| `settings.py` | Serializable processing state and normalization |
| `processor.py` | Main image-processing pipeline orchestration |
| `effect_schema.py` | Lightweight effect definitions/metadata |
| `effect_stack.py` | Effect rendering and stack execution |
| `dither_metadata.py` | Lightweight dithering metadata |
| `dither.py` | Dithering/quantization implementations |
| `palette.py` | Palette extraction/import/export helpers |
| `palette_library.py` | Built-in palette catalog and interpolation |
| `gradient_presets.py` | Built-in gradient preset definitions |
| `hardware_profiles.py` | Lightweight profile loading/metadata |
| `hardware.py` | Hardware constraints and display processing |
| `animation.py` | Multi-keyframe track evaluation, easing, and modulators |
| `animation_presets.py` | Built-in motion presets |
| `audio.py` | Audio-amplitude envelope analysis for modulation |
| `palette_lab.py` | Palette analysis, ramps, distances, reduction suggestions |
| `project.py` | `.rastermint` project serialization |
| `render_cache.py` | Bounded cumulative per-layer render cache |
| `benchmark.py` | Current-stack processing benchmark |
| `extensions.py` | Safe manifest/data-asset extension discovery |
| `media.py` | FFmpeg-backed media probing/decoding/export |
| `gif_export.py` | GIF-specific export helpers |
| `batch.py` | Sequential batch processing |
| `svg_export.py` | Vectorization of normal processed raster output |
| `print_lab.py` | AM-halftone separation generation, print compositing, individual-screen preview, and true-vector separation SVG export |
| `history.py` | Undo/redo state history |
| `lospec.py` | Lospec slug/URL parsing and palette fetch |

Lightweight metadata modules exist separately from render-heavy modules specifically to avoid pulling the full processing stack into application startup.

## Effect stack contract

Effects are represented as serializable nodes with stable IDs, an enabled state, a type, and validated parameters.

A new effect should:

- be described in the effect schema;
- normalize/clamp its parameters;
- render through the shared effect stack;
- preserve RGB image mode and predictable dimensions unless its purpose explicitly changes geometry;
- mark spatial parameters for preview scaling where appropriate;
- mark timeline-compatible numeric parameters as animatable;
- round-trip through presets/settings.

The order of effect nodes is meaningful and must be preserved.

## Layer compositing and caching

Normal effect nodes now also carry layer metadata (`opacity`, `blend_mode`, `mask`, and optional `group_id`). Effect rendering and layer compositing remain separate steps so every effect can benefit from the same opacity/blend/mask behavior.

Interactive preview may use a bounded cumulative per-layer cache. Cache keys include the source signature, stack prefix and processing context; changing layer *N* can therefore reuse a valid result from layers before *N*. Temporal renders and non-zero frame contexts bypass this cache so history-sensitive output cannot leak between frames.

For very large images, `processor.py` may tile the frame only when the complete active stack is explicitly classified as tile-safe. Effects with neighbourhood/global/temporal semantics fall back to full-frame processing. Tiling is an exact-memory policy, not a different visual mode.

## Preview scheduling

RasterMint exposes three user-facing preview modes.

### Quick

Uses a fast interactive proxy while controls are moving, followed by a refined render when interaction settles.

### Stable

Skips the draft stage and schedules a refined preview after the edit settles.

### Full

Uses the requested output resolution when safe. Very large frames may still use a bounded proxy to protect memory and UI responsiveness.

### Stale-result protection

Preview jobs carry source/settings revisions. A result created for an older revision is rejected instead of replacing a newer image. This is critical because worker completion order is not guaranteed.

### Adaptive budgets

Expensive dithering modes and very large palettes may receive smaller interactive proxy budgets. These budgets are preview policy only; they must not silently reduce final export quality.

## Print Lab boundary

`core/print_lab.py` owns print mathematics and file-independent separation generation. A Print Lab layer is normalized through the normal effect schema and rendered by the shared effect stack, so stills, animation frames, decoded media frames, presets, projects, compositing, undo/redo, and cache signatures continue to use the same settings contract.

Dedicated separation export is different from ordinary image SVG export: `PrintSeparationExportWorker` first renders the stack prefix before the active Print Lab layer, then asks `core/print_lab.py` for the actual ink screens. Each separation SVG is built from vector dot/cell geometry rather than embedding a raster image. Raster proofs and the composite PNG are emitted alongside those vector screens.

The Print Lab page is a presentation/control surface only. It must not contain screening mathematics. Long separation exports run in the existing thread pool and report through the same render-progress state as other expensive jobs.

## QML/UI boundary

The desktop interface lives under `src/rastermint/qml/`.

```text
qml/
├── Main.qml
├── ImageCanvas.qml
├── components/       shared themed controls
└── pages/            inspector pages
```

Python-facing Qt code lives under `src/rastermint/qmlui/`:

| Module | Responsibility |
| --- | --- |
| `backend.py` | Core QML-facing application state/actions |
| `preferences_backend.py` | Settings/preferences behavior |
| `export_backend.py` | Export/media-facing extension of the backend |
| `workers.py` | Preview/render worker jobs |
| `batch_worker.py` | Batch worker |
| `models.py` | Qt models exposed to QML |
| `theme.py` | Theme loading, chooser ordering, persistence, and color properties |
| `localization.py` | Runtime language selection, JSON-backed `QTranslator`, persistence, and QML retranslation |
| `image_provider.py` | Processed preview image provider |

QML should call the backend through explicit slots/properties and avoid importing processing implementation details directly.

### Sidebar icon rendering

The narrow inspector rail is icon-based. Ten static 32×32 PNGs under `data/icons/` are loaded by `InspectorNavButton.qml` as alpha/shape masks and recolored with a QtQuick `Canvas`:

- inactive icon: `theme.textColor`;
- active icon: `theme.accentColor`;
- selected button background: `theme.selectionColor`.

The Palette button is generated from four live theme swatches instead of a static PNG. Navigation labels remain attached to the buttons and are shown as translated hover tooltips.

The Canvas implementation deliberately uses `source-in` composition instead of `Qt5Compat.GraphicalEffects` so the sidebar does not require an optional Qt compatibility module on Linux.

### Runtime localization

`rastermint.app` creates `LocalizationManager(engine)` and exposes it to QML as the `localization` context property alongside `backend` and `theme`.

English is the source language. User-facing QML strings use `qsTr(...)`; packaged non-English dictionaries live under `data/translations/`. `LocalizationManager` loads the selected JSON dictionary into a small `QTranslator` implementation, installs it on the application, and calls `QQmlEngine.retranslate()` when the language changes. The preference is persisted through `QSettings`.

On first run/reset, RasterMint resolves the OS language when that language is available and otherwise falls back to English. The chooser still shows a concrete active language first, then a separator and the remaining languages; it does not expose a synthetic “System default” entry. Data extensions may add new translation dictionaries at startup. Product branding such as the literal name **RasterMint** is intentionally not translated.

Backend IDs, effect types, preset/settings keys, and other serialized identifiers must remain language-independent; localization belongs at the presentation boundary.

## Inspector loading

Inspector pages are designed to avoid unnecessary startup work. Expensive page content should not instantiate merely because a page exists in the navigation model. Large preset/data views should stay collapsed or lazy until the user opens them.

This is especially important for delegate-heavy views such as palette/gradient libraries.

## Animation

Animation modifies normal processing parameters over time rather than creating a separate rendering engine.

At a given timestamp:

1. copy the base processing settings;
2. evaluate enabled tracks;
3. write evaluated values into the copied settings;
4. render the frame through the normal processor.

Sequential tracks targeting the same parameter hold the last completed segment value until a later segment becomes active.

## Media and FFmpeg

`core/media.py` separates media decoding/encoding from image processing. Decoded video/GIF frames become ordinary RGB images and flow through the same processor as still images.

Official Windows packaging uses a validated **lean FFmpeg** build containing the codec/features RasterMint needs. The PyInstaller hook for `imageio_ffmpeg` intentionally does not collect a second full FFmpeg executable.

At runtime `core/ffmpeg_runtime.py` selects the packaged FFmpeg and configures `imageio-ffmpeg` to use it.

## Palettes and gradients

Palette data is represented as normal RGB/HEX colors plus metadata. Built-in palette JSON is loaded through the palette library; user palettes and Lospec imports ultimately become the same active palette state.

Gradient presets and custom gradient generation also produce a normal active palette. Selecting a gradient preset is therefore a palette operation, not a separate display effect.

## Hardware profiles

Hardware profiles are JSON data under `src/rastermint/data/hardware_profiles/`. Profile metadata can be loaded without importing the heavy hardware renderer.

RasterMint distinguishes:

- **Visual** behavior for recognizable creative treatment;
- **Strict** image-space constraints when those constraints can be modeled meaningfully.

RasterMint does not emulate CPU/GPU/PPU timing, sprite scheduling, electrical video signals, or game logic.

## Data resources

Package data lives under `src/rastermint/data/`:

```text
data/
├── hardware_profiles/
├── icons/
├── palettes/
├── presets/
├── themes/
└── translations/
```

Stable IDs belong inside data. Filenames should remain readable and should not be used as hidden ordering/state unless there is no better explicit field.

## Packaging

`build/rastermint.spec` is the central PyInstaller configuration.

Important packaging rules:

- keep the Windows distribution as a one-file executable;
- use custom hooks to avoid collecting unused QML/Pillow/FFmpeg payloads;
- exclude Qt feature families RasterMint does not use;
- validate FFmpeg capabilities before a release build;
- preserve package data required by QML and built-in libraries;
- do not "optimize" by deleting Qt plugins without verifying all three platform builds.

## Stability invariants

Changes should preserve these guarantees:

- `Main.qml` must compile and create an `ApplicationWindow` offscreen in CI;
- every packaged QML component must compile;
- top menus must open as themed in-scene popups;
- the render pipeline must remain lazy during GUI import/startup;
- preview results must not overwrite newer revisions;
- final export must not inherit preview-only resolution limits;
- presets/settings must remain serializable;
- built-in JSON assets, including translations, must remain parseable and packaged;
- sidebar icon masks must remain available to QML and tint without optional Qt compatibility modules;
- release builds must contain the resources/codecs required by supported workflows.

See [`TESTING.md`](TESTING.md) for how these contracts are verified.

## Extension packages

RasterMint supports read-only data extensions from the per-user `extensions/` directory. Each extension folder contains `extension.json` with `format: "rastermint-extension"`, `schema_version: 1`, a stable `id`/`name`, and an `assets` mapping. Supported asset directories are `palettes`, `themes`, `translations`, `hardware_profiles`, and `presets`.

The loader rejects path traversal outside the extension package and never lets extension assets silently replace a shipped ID. Python effect code is intentionally not auto-executed by this data-extension path.
