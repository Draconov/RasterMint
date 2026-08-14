# Changelog

## 0.1.0 - 2026-08-14

- Initial public project structure.
- Source-available noncommercial licensing with separate commercial licensing.
- PySide6 desktop GUI.
- 16 dithering / quantization modes.
- Custom and extracted palettes.
- Image adjustments and pixel scaling.
- Drag-and-drop processed preview.
- Removed the redundant original-image viewport.
- Reduced interactive preview source to a 640 px longest-side budget.
- Serialized preview work so obsolete renders no longer run concurrently.
- Added output downscaling from original size through ÷16.
- Optimized generic error-diffusion scalar processing while preserving the previous kernel output.
- Removed unnecessary full source-image copies from worker jobs.
- JSON presets and CLI processing.
- Manual Windows GitHub Release workflow.
- Windows release is now a single `RasterMint.exe` instead of an EXE + `_internal` directory.
