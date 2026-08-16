# Changelog

## 0.1.0 - 2026-08-14

- Widened the QML two-column inspector and fixed ScrollView content sizing so Animation, Layers, Raster, Hardware, Source, and Preview controls no longer clip horizontally.
- Added full-width themed sliders with larger handles for smoother, more precise parameter editing.
- Added application edit history with Ctrl+Z Undo and Ctrl+Y Redo for processing settings, layers, transforms, palettes, hardware/presets, animation tracks, randomization, and audio-export state. Continuous slider and mirror-axis drags are grouped into one undo step.
- Turned the bottom-left status bubble into a single last-action indicator; parameter changes report their layer/parameter/value, and Undo/Redo report exactly what was restored.

- Fixed QML parsing in the animation track editor by removing invalid semicolons between sibling child objects.
- Fixed the same compact grouped-property separator pattern in the Settings dialog.
- Expanded the offscreen QML smoke suite to compile every packaged QML component individually, so CI reports all QML parse/type errors in one run.

- Migrated the desktop frontend from Qt Widgets to **PySide6 + Qt Quick/QML** while keeping the Python processing core and release pipeline.
- Added JSON-driven application themes with **RasterMint Dark** as the default and a live selector under **Edit → Settings… → Appearance → Theme**.
- Added **Solarized Dark** and **Solarized Light** application themes using Ethan Schoonover's canonical Solarized palette.
- Removed the obsolete `src/rastermint/ui/` QWidget frontend instead of shipping two parallel interfaces.
- Added controllable **Bloom** layer with highlight threshold, soft knee, radius, intensity, Screen/Add blending, and animation support.
- Fixed Linux GitHub Actions QML test startup by installing the required EGL/OpenGL/Qt runtime libraries before importing `PySide6.QtGui`.
- Fixed the QML Preview mode selector so Quick / Stable / Full use a supported selected-state property instead of assigning through `background.color`, which prevented `Main.qml` from loading on Linux CI.
- Fixed Qt Quick top-menu interaction after packaging by explicitly keeping customized menus/popups in the Qt Quick scene instead of allowing platform/style-dependent native popup promotion.
- Normalized QML file/folder-dialog URLs before passing them to Python slots, fixed mirror-axis dragging so it no longer breaks declarative position bindings, and forced custom ComboBox/layer/dialog popups to use the same reliable scene popup mode.
- Moved the empty “Open or drop…” prompt to the true center of the preview canvas and reserved the bottom status overlay for messages after a source is loaded.

RasterMint remains on version **0.1.0** while the initial feature set is being built out.

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
