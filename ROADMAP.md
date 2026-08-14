# RasterMint Roadmap

## Current 0.1.x foundation

Implemented:

- live/still/full processed preview modes;
- output proxies and adaptive preview budgets;
- reorderable effect stack;
- 26 dithering/quantization algorithms;
- up-to-256-color palette workflow;
- Lospec per-palette import with fetched swatch preview;
- palette locks/randomization/file import plus Median Cut/K-Means/Octree/Wu optimization;
- still animation timeline with easing and per-track timing;
- temporal effects;
- GIF/video input, scrub/quick playback/export;
- source-audio mux during video export;
- animated GIF and MP4 from still images;
- SVG current-frame export;
- exact target raster, source crop/rotate/flip, pixel aspect and display/grid views;
- data-driven Visual/Strict hardware profiles and image-space constraints;
- local contrast, glitch family, pixel materials, and text overlay effects;
- randomize locks with previous/next history;
- batch image processing;
- rolling Windows/Linux/macOS releases.

## Next

- project files (`.rmproject`) that preserve source references, stack, timeline, and UI state;
- proxy-frame cache for smoother long-video playback;
- cancelable exports and batch jobs;
- richer keyframe editing (more than one segment per track, graph editor);
- APNG and animated WebP;
- palette search through an officially supported indexed API if/when appropriate credentials/API access are configured;
- additional independently implemented pattern/advanced dithering families;
- perceptual color matching option;
- visual preset thumbnail browser;
- before/after split view;
- optional GPU preview backend with CPU reference renderer;
- installer/signing/notarization and optional OS protocol registration for palette integrations.
