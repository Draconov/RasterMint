# RasterMint Roadmap

## Current 0.1.x foundation

Implemented:

- live/still/full processed preview modes;
- output proxies and adaptive preview budgets;
- reorderable effect stack;
- 26 dithering/quantization algorithms;
- up-to-256-color palette workflow;
- Lospec per-palette import;
- palette locks/randomization/file import;
- still animation timeline with easing and per-track timing;
- temporal effects;
- video input/scrub/quick playback/export;
- source-audio mux during video export;
- animated GIF and MP4 from still images;
- SVG current-frame export;
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
- before/after split view;
- crop/rotate/canvas nodes;
- optional GPU preview backend with CPU reference renderer;
- installer/signing/notarization and optional OS protocol registration for palette integrations.
