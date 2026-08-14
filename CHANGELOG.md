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
- Added output downscaling from original size through ÷16.
- Optimized classic error-diffusion processing while preserving the previous pixel output.

### Effects

- Added Adjustments, Hue Rotate, Grayscale, Invert, Gaussian Blur, Median Denoise, Sharpen, Glow, JPEG Compression, Chromatic Shift, Posterize, Scanlines, Noise, Temporal Flicker, Pixelate, and Dither stack nodes.
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
- Added Lospec palette import by slug or palette URL using Lospec's documented palette JSON endpoint.
- Added palette name, author, and source metadata to settings and presets.

### Animation and video

- Added animation tracks with From/To values, start/end times, easing, duration, FPS, and per-track enable/bypass.
- Added timeline preview/playback for animatable effect parameters.
- Animated effect controls are locked while an enabled animation track owns that parameter.
- Added temporal noise and temporal flicker behavior.
- Added video input, background frame seeking, processed video preview, and MP4 export.
- Added still-image animation export to MP4 and animated GIF.
- Added optional source-audio preservation when exporting processed video.
- Added `imageio-ffmpeg` integration and PyInstaller bundling for the platform FFmpeg executable.

### Export and batch

- Added exact-color SVG export using horizontal vector runs.
- Added batch processing for multiple images.
- Kept raster export for PNG, JPEG, WebP, BMP, and TIFF.

### Developer and repository

- Added `docs/EXTENDING_RASTERMINT.md` with concrete extension instructions.
- Added `docs/FEATURE_RESEARCH.md` describing the Lospec integration and external-project research boundaries.
- Updated `docs/ARCHITECTURE.md` for the effect-stack, animation, palette, media, batch, and export architecture.
- Added `THIRD_PARTY_NOTICES.md`.
- Kept `VERSION` as the single version source for package metadata, the app, builds, and rolling GitHub releases.
- Rolling GitHub release workflow builds Windows, Linux, and macOS on each push to `main` and refreshes the same `v<VERSION>` release assets.
- Windows ships as `RasterMint.exe`, Linux as `RasterMint-linux-x86_64.tar.gz`, and macOS as `RasterMint-macOS.zip` containing `RasterMint.app`.
- Source-available noncommercial licensing with separate commercial licensing remains in place.
