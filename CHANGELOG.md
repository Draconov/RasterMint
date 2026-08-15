# Changelog

## 0.1.0 - 2026-08-14

RasterMint remains on version **0.1.0** while the initial feature set is being built out.

### Processing and preview

- Added a reorderable effect stack with per-effect enable/bypass, duplicate, remove, and drag-to-reorder controls.
- Added live two-stage preview with a fast draft followed by a refined render.
- Added `Live`, `Still`, and `Full` preview modes.
- Added adaptive preview budgets for expensive algorithms and large palettes.
- Added source/settings revision guards so stale background jobs cannot replace newer results.
- Kept export processing independent from preview resolution so exports still use the selected output size.
- Added exact target raster controls (plus legacy ÷1…÷16 compatibility), source crop/flip/rotate, Fit/Fill/Stretch placement, pixel-aspect-corrected views, and independent preview/export grids.
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
