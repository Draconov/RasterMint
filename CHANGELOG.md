# Changelog

## 0.7.4 - 2026-09-04 — Tonal Map + Dither Edge Treatment

- Added **Tonal Map** as a standalone Color & Tone layer with Mono, Duotone, Tritone, and four-colour Gradient modes.
- Added configurable Shadow, Midtone, Highlight, and Background colours with tonal anchor points, blend softness, and optional source-alpha preservation.
- Added **Edge treatment** controls to the Dither layer: palette-safe Bleed from -10 to +10 px, morphological Rounding from 0–100%, and Native / 2× Supersampled sampling.
- Positive Bleed expands darker/ink-like palette regions while negative Bleed contracts them; Rounding smooths isolated/jagged palette-index structures without inventing colours.
- 2× Supersampled dithering renders the algorithm at double resolution, area-downsamples it, then remaps to the active palette before edge treatment.
- Default Dither settings remain visually identical to 0.7.3.
- Preset files no longer store source crop coordinates, and applying built-in, user, imported, or mutated presets preserves the crop already active on the current source.
- New imports reset to the full image by default; Settings > Import now offers **Preserve cropping position** to carry the current normalized crop position and size across images, GIFs, videos, and clipboard imports.
- Updated all bundled translation catalogs for the new effect and controls.
- Updated the application version to **0.7.4**.

## 0.7.3 - 2026-09-04 — Canvas Crop Tool

- Rebuilt cropping as a non-destructive canvas tool with eight resize handles, move/new-selection gestures, themed outside shading and Rule of Thirds/Grid/Center overlays.
- Added Free, Original, 1:1, 4:3, 3:2, 16:9 and custom aspect ratios with orientation swapping and exact pixel X/Y/Width/Height controls.
- Crop edits are draft-only until Apply, so dragging does not trigger expensive preview renders; Enter applies, Esc cancels and double-click applies.
- Replaced four edge crop percentages with the normalized `crop_x`, `crop_y`, `crop_width`, `crop_height` model and centralized pixel crop rounding for RGB, alpha and raster-size calculations.
- Added full-resolution crop coordinates with a 4096-pixel display proxy for very large sources.
- Added the Crop sidebar page and Edit > Crop Image… (`C`) shortcut using the user-supplied `sidebar-crop.png`.
- Updated built-in preset schema/settings for the new crop model and advanced project schema to the new crop-era format.
- Updated all translation catalogs for the new crop UI.
- Updated the application version to **0.7.3**.

Notable user-facing and engineering changes are recorded here. RasterMint is still in active alpha development, so entries focus on behavior that affects releases, compatibility, or contributor expectations.

## 0.7.1 - 2026-09-02 — Group Fix/Update

### Layer groups

- Group creation now immediately assigns the first unused **Group N** name instead of opening a naming dialog.
- Added drag-to-group behavior for layers and groups, including automatic grouping when one layer is dropped onto another.
- Added nested groups up to **five levels**, one-level ungrouping by dragging a layer out, collapse/enabled state per group, and inline group-name editing by double-click.

### Effects and interface

- Added **Vignette** as a layer effect with strength, size, softness, roundness, centre X/Y, and colour controls.
- Added a **Chroma noise** toggle to Noise for independent RGB noise while preserving monochrome shared-channel noise when disabled.
- Replaced default hover tooltips with theme-aware RasterMint tooltips and removed drag-and-drop instruction text from active-layer hover descriptions.

### Release

- Updated the application version to **0.7.1**.

## 0.7.0 - 2026-09-01 — Pixel Art Cleanup + Preset Mutation

### Pixel Art Cleanup Lab

- Added a non-destructive **Pixel Art Cleanup** layer under **Pixel & Dither** for cleaning machine-dithered and generated pixel art while preserving the existing editable layer workflow.
- Added **orphan-pixel removal**, **cluster cleanup**, **line cleanup**, **staircase correction**, and exact **tiny-island removal** with selectable 4-neighbour or 8-neighbour connectivity.
- Added adjustable **Edge Preservation** so cleanup can avoid meaningful contours while still repairing isolated noise and explicitly targeted tiny components.
- Added **Clean Result**, **Issue Overlay**, and **Cluster Map** visualization modes for inspecting weak clusters and connected pixel regions before finalizing a look.
- Clean Result is palette-safe: replacements are selected from colours already present in the processed image, so cleanup placed after a palette-limited dither does not invent new colours.
- Added bounded run-length connected-component analysis to avoid allocating a Python object per fragmented pixel/run on large dithered images, and routed cleanup through RasterMint's adaptive preview budget.

### Preset Mutation

- Added **Preset Mutation** to the Presets page. Any built-in, user, or extension preset can generate **6–12 controlled nearby variations**.
- Added adjustable mutation amount and current-image mutation thumbnails so variations can be compared before applying them. Mutation now runs from one dedicated **Preset Mutation** panel for the currently selected preset instead of placing a Mutate button on every preset card.
- Mutation preserves the complete editable structure of the source look: layer IDs/order/types, enable state, masks, blend modes, animation tracks, target raster, and locked palette colours remain intact.
- Numeric effect parameters, layer opacity, and unlocked palette colours receive bounded deterministic perturbations; algorithm choices, seeds, fonts, text, JSON payloads, profile identifiers, and custom matrices are intentionally left alone.
- Generated mutations are collected in a dynamic **Mutations** category after the normal preset categories; they apply as ordinary RasterMint settings and can immediately be edited, reordered, animated, saved to the preset library, or stored in a project.

### Localization

- Added 10 new complete bundled translations: **Simplified Chinese, Hindi, Bengali, Indonesian, Urdu, Punjabi, Japanese, Vietnamese, Turkish, and Korean**, bringing RasterMint to **22 runtime languages** including English.
- Added coverage and placeholder validation for the new dictionaries and kept automatic system-language selection compatible with their standard locale IDs.

### Layer browser UX

- Reorganized the add-layer catalogue into smaller workflow-focused groups so CRT, analog-signal, tape/compression, and glitch effects no longer sit inside oversized 20+ item categories.
- Added a concise hover description for every visible layer effect in both the add-layer menu and active layer cards, matching the discoverability already used by hardware profiles and presets.

### Documentation and release

- Added dedicated **Pixel Art Cleanup** and **Preset Mutation** workflow documentation and updated architecture/extension guidance for the new systems.
- Updated the application version to **0.7.0**.

## 0.6.0 - 2026-08-30 — Print Lab + Modulated Diffusion

### Print Lab / AM halftone

- Added a dedicated, non-destructive **Print Lab** with independent **Monochrome, CMYK, RGB, and 1–8 Spot Color** separation workflows while keeping the existing ordinary Halftone dither separate.
- Added true AM screen geometry with editable cell size, Round/Ellipse/Square/Diamond/Line dots, per-ink angles, per-ink X/Y registration, phase offsets, opacity, paper color, and subtractive overprint mixing.
- Added CMYK under-color removal / **Black Generation**, conventional editable 15°/75°/0°/45° defaults, and individual separation inspection in the live layer pipeline.
- Added print imperfections including dot gain, automatic registration error, screen roughness, missing/weak ink, irregular ink spread, paper-grain interaction, and squeegee/coverage artifacts; clean output remains available by leaving these at zero.
- Added palette-assisted Spot Color setup so the active RasterMint palette can seed up to eight editable spot inks.
- Added dedicated separation export that writes **real vector SVG screen geometry**, raster separation proofs, and a composite PNG. Transparent source regions correctly remain unprinted in generated separations.
- Added eight editable Print Lab presets: **Clean CMYK Print, Vintage Screen Print, 2-Color Poster, 3-Color Risograph, Newspaper CMYK, Misregistered Print, Cheap T-Shirt Print,** and **Heavy Dot Gain**.

### New dithering / structural raster effects

- Added **Pop Tone** with scale, density, and variation controls for manga/pop-art clustered-dot rendering that remains bounded to the active palette.
- Added the polygon family **Hexa-Poly, Penta-Poly, Tri-Poly,** and **Low-Poly**, rebuilding the image from actual filled polygon cells instead of placing a polygon texture over pixelation.
- Added **Beehive**, an actual honeycomb-cell renderer with scale, luminance-threshold, and cell-size controls for monochrome or colored palettes.

### Modulated Diffusion Update

- Expanded the existing single **Modulation** dither into a full 14-mode modulation-aware diffusion family without adding 14 separate entries to the algorithm chooser: **Smooth Diffuse, Modulated Diffuse X/Y, Uniform Modulation X/Y, Waveform, Waveform Alt, Ordered Modulation, Stucki Diffusion Lines, Atkinson Modulation, Contrast Aware X/Y, Displace Contour,** and **Sine Wave Modulation**.
- Added shared modulation controls for scale, phase, bias, contour detail, deterministic seed, strength, and serpentine traversal. The new implementation biases palette decisions inside error diffusion rather than warping an already-dithered image, and every mode remains strictly bounded to the active palette.
- Preserved older Modulation projects/presets by mapping mode-less legacy layers to **Sine Wave Modulation**, the closest match to RasterMint's previous sinusoidal Modulation renderer.
- Added five editable modulation presets with different line structures and glow/bloom treatments: **Smooth Diffuse Bloom, Circuit Cyan Lines, Stucki Wire Glow, Contour Bend Glow,** and **Waveform Scan Bloom**.
- Added an animated **Particle / Star Field** preset built only from existing RasterMint primitives—darkening, temporal Noise, Threshold dithering, Noise Drift, Dither Glow, Bloom, and Temporal Flicker—so the look stays fully editable in the normal layer stack and does not introduce a separate particle subsystem.
- Marked Modulation as an expensive interactive-preview algorithm so the existing adaptive preview budget protects responsiveness on large sources.

### Interaction and performance

- Added optional global **Scroll Wheel Control** for sliders using each control's existing smart step/rounding behavior.
- Added optional **Debounce Slider Updates** so expensive controls can wait briefly while dragging and flush immediately when the interaction ends.
- Routed Print Lab separation export through the existing background-worker and render-progress system; the progress overlay retains RasterMint's existing rule of staying hidden for operations predicted to finish in under five seconds.
- Kept Print Lab/new effects on the shared still/animation/video processing stack, existing layer compositing, undo/redo, preset/project serialization, render cache, and safe full-frame fallback for effects that are not mathematically tile-safe.

### Scope

- The existing **Quick / Stable / Full** preview system is unchanged in 0.6.0. No new preview-quality/forced-100% mode was added.
- Animated-preset mode switching and new sRGB/Adobe RGB/Display P3/ICC color-management features are intentionally outside this release.

## 0.5.0 - 2026-08-29 — Singular Lab Update

### Display Lab

- Expanded **Display Effects** into composable CRT/LCD/OLED/composite/RF/VHS building blocks: RGB convergence, aperture-grille/shadow-mask/slot-mask simulation, phosphor glow, beam width, horizontal bloom, scanline variation, curvature/edge distortion, vertical-sync roll, field flicker, LCD inversion, dot crawl, composite noise, RF interference, horizontal tearing, chroma bleed, tracking errors, tape dropout, head-switch noise, temporal jitter, and display persistence.
- Added/expanded display recipes for Consumer CRT, PVM, Arcade CRT, Cheap RF TV, VHS SP/EP, Early LCD, Game Boy LCD, OLED Ghosting, Security Camera, Camcorder, CRT + VHS, DOS VGA, VGA 320×200, Macintosh Monochrome, and SNES S-Video.
- Hardware profiles can now inject normal composable display-effect layers instead of hiding an entire look inside one monolithic display stage.

### Layer System 2.0

- Added per-layer **Opacity**, **Blend Mode**, and procedural **Mask** metadata with shared compositing in the normal effect stack.
- Added solo, duplicate, reset, copy/paste layer settings, multi-selection, and collapsible layer groups while preserving stable layer IDs and serialized settings.

### Palette & Dither Lab

- Added palette analysis for colour usage, luminance/hue/saturation sorting, near-duplicate detection, ramp detection, distance analysis, unused-colour reporting, and palette-reduction suggestions.
- Added a **Dither Matrix Designer** and custom ordered-dither matrices that serialize with normal settings/presets.

### Motion Studio

- Expanded animation tracks to support multiple keyframes, per-key easing/Bezier data, key copy/paste, reusable animation clips, and procedural modulators.
- Added audio-amplitude analysis as a modulation source while keeping frame rendering on the shared processing pipeline.

### Projects and workflow

- Added `.rastermint` project files for processing state, source references, playback/UI state, export state, layer selection, and A/B snapshots.
- Added A/B snapshot capture/apply and draggable split comparison in the preview.
- Expanded the preset library with search, favourites, recent presets, user categories, rename/duplicate actions, and preset-pack import/export foundations.

### Performance

- Added bounded per-layer intermediate caching so editing a later layer can reuse unchanged earlier results.
- Added exact-safe tiled processing for very large images when the active stack can be processed tile-by-tile without changing output.
- Added configurable cache memory/tile size controls and a current-stack benchmark action in Settings.

### Extensions and localization

- Added manifest-based, read-only extension discovery for palettes, themes, translations, hardware profiles, and effect presets under the user extension directory. Built-in IDs win collisions and extension paths are contained to their package directory.
- Localized all new singular-update UI/effect labels across the current 11 non-English dictionaries while preserving English source strings and the existing system-language-first fallback behavior.

## 0.2.4 - 2026-08-26

### Inspector and navigation

- Replaced the text-only inspector category rail with a compact 32×32 icon-based sidebar while preserving translated category names as hover tooltips.
- Regrouped the sidebar into the final navigation order: Randomize; Presets/Hardware/Palette/Layers; Source/Preview/Raster; Animation/Media Playback, separated by visual dividers.
- Kept the uploaded monochrome PNG artwork as alpha/shape masks and tinted the nine static sidebar icons from the active theme. Inactive icons use `theme.textColor`; the active icon uses `theme.accentColor`.
- Removed the redundant active-page indicator stripe after active-icon accent tinting made the selected state clear.
- Kept Palette as a special live four-swatch icon driven directly by current theme colors rather than a fixed PNG.

### Themes

- Added five built-in themes: **Studio Gray**, **Midnight**, **Violet**, **Amber**, and **Hacker**, bringing the built-in theme set to 14.
- Kept theme ordering explicit in `qmlui/theme.py` so the Settings chooser is stable instead of depending on filename sorting.
- Made the icon-only sidebar react to theme changes automatically, including active/inactive icon colors and Palette swatches.

### Localization

- Added runtime **English and Ukrainian** localization using `LocalizationManager`, `QTranslator`, JSON translation dictionaries, and `QQmlEngine.retranslate()`; no `.qm` build step is required.
- Marked user-facing QML strings for translation and added the packaged Ukrainian dictionary under `data/translations/uk.json`.
- Added live language switching in Settings with the selected language persisted through `QSettings`.
- Made **English** the explicit default/fallback language, removed the old “System default” choice, and migrated the legacy `system` preference to English.
- Reworked the language chooser so the active language appears first, followed by a separator and the remaining available languages.
- Kept the **RasterMint** product name literal/non-translatable in window and About branding.

### Cross-platform reliability

- Replaced the initial `Qt5Compat.GraphicalEffects` / `ColorOverlay` icon-tint implementation after Linux CI showed that compatibility module was unavailable.
- Reimplemented sidebar mask tinting with pure QtQuick `Canvas` composition (`source-in`), keeping theme-aware icons without adding a new Qt runtime dependency.
- Kept offscreen QML compilation/runtime coverage for the sidebar and localization integration while removing theme-order-only test clutter.

### Documentation

- Synchronized the README, icon documentation, architecture guide, extension guide, and contributor guidance with the 0.2.4 sidebar, themes, localization, and clipboard workflow.

## 0.2.3 - 2026-08-26

### Performance and memory

- Removed duplicate effect-stack normalization from the main processor and preview scaling paths while keeping the public effect-stack API safe for arbitrary stacks.
- Reworked K-Means palette extraction to use bounded-memory center assignment and incremental farthest-point initialization, avoiding large pixel×center and colour×center temporary arrays.
- Reduced strict hardware tile-limit work by mapping each unique tile colour once and weighting reconstruction error by occurrence count instead of repeatedly remapping every pixel.
- Added a lightweight settings clone path for previews and animation-frame evaluation instead of serializing settings through `to_dict()` / `from_dict()` on every refresh/frame.

### Hardware pipeline cleanup

- Removed the obsolete hidden `hardware_constraints_enabled` / `hardware_constraints` settings and post-processing fallback. Hardware restrictions now live exclusively in the visible Hardware Limits layer.
- Removed the corresponding dead fields from bundled JSON presets.

### Tests

- Replaced brittle QML source-format assertions for clipboard/menu wording and dialog theming with API-boundary/runtime coverage where stronger QML compilation tests already exist.
- Added regression checks for single-pass stack normalization, settings-clone independence, deterministic chunked K-Means, and pixel-identical optimized hardware tile limiting.

## 0.2.1 - 2026-08-24

### Startup and packaging

- Fixed Windows startup regressions in the Qt Quick/QML path and kept expensive inspector/preset content from being created during initial window construction.
- Deferred heavy processing imports so NumPy, Pillow, media/FFmpeg helpers, and render modules are loaded only when processing or export needs them.
- Added a validated lean Windows FFmpeg build for the single-file release and prevented PyInstaller from bundling both the lean executable and imageio-ffmpeg's full fallback binary.
- Added startup/packaging regression coverage for the lazy-import and FFmpeg contracts.

### Palette and gradient workflow

- Added a built-in gradient preset library and custom multi-anchor gradient generation.
- Gradient presets and custom generation now update the active palette used to process the image.
- Fixed the gradient preset/editor layout and made the preset browser start collapsed.
- Cleaned numeric prefixes from base palette filenames while preserving stable palette IDs, names, colors, and curated ordering.

### Export and workflow

- Added/expanded batch export controls for output format, scaling, overwrite behavior, and source-relative sizing.
- Preserved source filenames more consistently across still, animation, video, and batch export paths.
- Expanded animated GIF/video export workflows while keeping offline FFmpeg support.

### Reliability and tests

- Fixed QML merge/syntax regressions that prevented `Main.qml` / `PalettePage.qml` from compiling in CI.
- Removed obsolete source-text regression checks where stronger QML compile/runtime tests already cover the same failure class.
- Kept the full offscreen QML component compilation and runtime smoke coverage intact.

## 0.1.0 - 2026-08-14

- Added Sunrise, Halloween, and TrueBlack themes and made the chooser order explicit: RasterMint Dark, RasterMint Light, OLED, TrueBlack, Solarized Dark, Solarized Light, Mint, Sunrise, Halloween.
- Added **View → Show Hotkeys** with persistent, platform-formatted shortcut hints in custom menus, plus unique shortcuts for the remaining top-menu actions.
- Switched Show Hotkeys and both mirror toggles to Qt Quick Controls' native check indicators, with the indicator color bound to the active RasterMint theme.
- Fixed top-menu buttons staying visually selected after menus close by removing mouse-focus from the selected-state styling.
- Simplified Settings to a clean Appearance/theme chooser and fixed About/internal themed controls so default Qt style colors no longer leak into alternate themes.
- Added themed menu separators and SpinBoxes, and moved preview/status overlays onto active theme colors.

- Widened the QML two-column inspector and fixed ScrollView content sizing so Animation, Layers, Raster, Hardware, Source, and Preview controls no longer clip horizontally.
- Added full-width themed sliders with larger handles for smoother, more precise parameter editing.
- Added application edit history with Ctrl+Z Undo and Ctrl+Y Redo for processing settings, layers, transforms, palettes, hardware/presets, animation tracks, randomization, and audio-export state. Continuous slider and mirror-axis drags are grouped into one undo step.
- Turned the bottom-left status bubble into a single last-action indicator; parameter changes report their layer/parameter/value, and Undo/Redo report exactly what was restored.

- Fixed QML parsing in the animation track editor by removing invalid semicolons between sibling child objects.
- Fixed the same compact grouped-property separator pattern in the Settings dialog.
- Expanded the offscreen QML smoke suite to compile every packaged QML component individually, so CI reports all QML parse/type errors in one run.

- Migrated the desktop frontend from Qt Widgets to **PySide6 + Qt Quick/QML** while keeping the Python processing core and release pipeline.
- Added JSON-driven application themes with **RasterMint Dark** as the default and a live selector under **Edit → Settings… → Appearance**.
- Added **Solarized Dark** and **Solarized Light** application themes using Ethan Schoonover's canonical Solarized palette.
- Removed the obsolete `src/rastermint/ui/` QWidget frontend instead of shipping two parallel interfaces.
- Added controllable **Bloom** layer with highlight threshold, soft knee, radius, intensity, Screen/Add blending, and animation support.
- Fixed Linux GitHub Actions QML test startup by installing the required EGL/OpenGL/Qt runtime libraries before importing `PySide6.QtGui`.
- Fixed the QML Preview mode selector so Quick / Stable / Full use a supported selected-state property instead of assigning through `background.color`, which prevented `Main.qml` from loading on Linux CI.
- Fixed Qt Quick top-menu interaction after packaging by explicitly keeping customized menus/popups in the Qt Quick scene instead of allowing platform/style-dependent native popup promotion.
- Normalized QML file/folder-dialog URLs before passing them to Python slots, fixed mirror-axis dragging so it no longer breaks declarative position bindings, and forced custom ComboBox/layer/dialog popups to use the same reliable scene popup mode.
- Moved the empty “Open or drop…” prompt to the true center of the preview canvas and reserved the bottom status overlay for messages after a source is loaded.

At this stage, RasterMint remained on version **0.1.0** while the initial feature set was being built out.

### Processing and preview

- Moved flip, mirror and rotation actions directly into Edit; mirror modes now use draggable blue axes in the preview.
- Added the first real application preference to Settings: a live theme selector, with Reset Settings kept at the bottom.
- Switched user presets to normal human-editable `.json` files.
- Replaced the manual pixel-grid setting with an automatic high-zoom viewport grid.
- Made the official repository link clickable in About.
- Hardened preview memory use and shutdown behavior, and added persistent crash logging for frozen GUI builds.
- Rebuilt the desktop interface around the top menu bar plus a two-column text inspector: general categories on the left, detailed controls on the right.
- Removed the old toolbar, live-preview checkbox/hint text, and empty-viewport instruction text.
- Renamed desktop preview modes to Quick, Stable, and Full without changing the underlying renderer behavior.
- Added Edit/View application menus and visible hover highlighting for interactive menu items.
- Reframed the effect editor as a Layer Stack and added a stackable Pixel Aspect Ratio image-space layer alongside existing effects such as Chromatic Shift.

- Added a reorderable effect stack with per-effect enable/bypass, duplicate, remove, and reorder controls.
- Added live two-stage preview with a fast draft followed by a refined render.
- Exposed preview modes as `Quick`, `Stable`, and `Full` while retaining the existing draft/refine/full scheduling logic.
- Added adaptive preview budgets for expensive algorithms and large palettes.
- Added source/settings revision guards so stale background jobs cannot replace newer results.
- Kept export processing independent from preview resolution so exports still use the selected output size.
- Added exact target raster controls (plus legacy ÷1…÷16 compatibility), source crop/flip/rotate, Fit/Fill/Stretch placement, pixel-aspect-corrected views, and an automatic high-zoom viewport pixel grid that is never baked into exports.
- Optimized classic error-diffusion processing while preserving the previous pixel output.

### Effects

- Added Local Contrast plus a broad creative/glitch set: RGB Split, Interlace, Pixel Sort, Screen Melt, Block Shuffle, Pixel Scatter, Data/Row/Column Shift, Cellular Automata, Databend-style processing, Channel Swap, Pixel Material, Text Overlay, and the existing color/spatial/dither nodes.
- Added schema-driven effect parameters so new effects can be exposed in the UI without hard-coding another form in the main window.
- Added preview-aware scaling for pixel-sized effect parameters.

### Dithering

- Expanded the algorithm library to 26 modes.
- Added Bayer 16×16 and 32×32, Clustered Dot 4×4 and 8×8, Halftone, Interleaved Gradient Noise, Blue Noise, Dot Diffusion, Riemersma, and Shiau–Fan alongside the existing classic algorithms.
- Added grouped algorithm metadata for quantization, ordered, error-diffusion, and advanced families.

### Palettes

- Expanded palettes to as many as 256 swatches.
- Added palette swatch locking, shuffle-unlocked, and randomize-unlocked tools.
- Added GIMP GPL, JASC PAL, HEX, and text palette import.
- Added palette export to HEX.
- Added Lospec palette import by slug or palette URL using Lospec's documented palette JSON endpoint, including a fetched swatch preview before import.
- Added Median Cut, deterministic K-Means, Octree, and Wu-style optimized palette extraction up to 256 colors.
- Added palette name, author, and source metadata to settings and presets.

### Animation and video

- Added a true animatable Dither Mix control plus Dither In, Dither Out, and Dither In/Out motion presets.
- Made suitable numeric effect parameters automatically available to the timeline, excluding identity/random seeds.
- Added sequential same-parameter track evaluation, track update/duplicate controls, frame-step/start/end transport, and loop playback.
- Added Quick vs Rendered animation playback with a background preview-frame cache.
- Added Temporal Pattern modes: Pulse, X/Y/diagonal wave, checker phase, scan sweep, deterministic noise drift, alternating, and radial pulse.
- Added motion presets for Glow Pulse, Hue Sweep, CRT Flicker, Pixelate In, Chromatic Pulse, and Temporal Wave.
- Added Rendered 5-second video-segment preview, preview speed controls, loop control, and an explicit preserve-audio option.
- Added full-resolution numbered PNG-sequence export for still animation, GIF, and normal video.
- Added animation tracks with From/To values, start/end times, easing, duration, FPS, and per-track enable/bypass.
- Added timeline preview/playback for animatable effect parameters.
- Animated effect controls are locked while an enabled animation track owns that parameter.
- Added temporal noise and temporal flicker behavior.
- Added video and animated-GIF input, background frame seeking, processed timed-media preview, GIF/MP4 export paths, and MP4 export for normal video.
- Added still-image animation export to MP4 and animated GIF.
- Added optional source-audio preservation when exporting processed video.
- Added `imageio-ffmpeg` integration and PyInstaller bundling for the platform FFmpeg executable.

### Target raster and hardware profiles

- Added first-class exact target width/height controls with common retro raster presets.
- Added framebuffer pixel-aspect ratios with Raw, Corrected, and Display Simulation views.
- Added data-driven Visual/Strict hardware profiles for 12 initial handheld/console/computer targets.
- Added generic fixed-palette, channel-depth, global-color, per-tile color, and grouped attribute-palette constraints.
- Added separate display treatment for gamma, bleed, blur, scanlines, and LCD grid.
- Added selective profile application switches for raster, palette, PAR, limits, and display.
- Added Creative Randomize locks plus Previous/Next history.

### Export and batch

- Added exact-color SVG export using horizontal vector runs.
- Added batch processing for multiple images.
- Kept raster export for PNG, JPEG, WebP, BMP, and TIFF.

### Developer and repository

- Added `docs/EXTENDING_RASTERMINT.md` with concrete extension instructions.
- Added `docs/HARDWARE_PROFILES.md` with the profile JSON schema, Visual/Strict behavior, framebuffer/display separation, and extension rules.
- Added `docs/FEATURE_RESEARCH.md` describing the Lospec integration and external-project research boundaries.
- Updated `docs/ARCHITECTURE.md` for the effect-stack, animation, palette, media, batch, and export architecture.
- Added `THIRD_PARTY_NOTICES.md`.
- Kept `VERSION` as the single version source for package metadata, the app, builds, and rolling GitHub releases.
- Rolling GitHub release workflow builds Windows, Linux, and macOS on each push to `main` and refreshes the same `v<VERSION>` release assets.
- Windows ships as `RasterMint.exe`, Linux as `RasterMint-linux-x86_64.tar.gz`, and macOS as `RasterMint-macOS.zip` containing `RasterMint.app`.
- Source-available noncommercial licensing with separate commercial licensing remains in place.

### QML top-menu interaction fix

- Replaced the fragile automatic `MenuBar`/`MenuBarItem` popup path with an explicit themed QML header.
- File, Edit and View now open their menus through `Menu.popup(button, 0, button.height)` and have concrete popup widths.
- Added explicit implicit widths to customized menu items/backgrounds so a popup cannot open at zero width.
- Added click-state highlighting and hover-to-switch behavior while a top menu is open.
- Positioned the Add Layer popup relative to its button instead of relying on an implicit popup origin.
- Kept the empty drop prompt centered in the preview canvas.
