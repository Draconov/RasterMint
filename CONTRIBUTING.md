# Contributing to RasterMint

Thanks for helping me improve RasterMint (❁´◡`❁)

## Before you start

For substantial code contributions, open an issue or discussion first so implementation direction and contribution terms can be agreed before significant work is done.

Recommended reading:

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/EXTENDING_RASTERMINT.md`](docs/EXTENDING_RASTERMINT.md)
- [`docs/TESTING.md`](docs/TESTING.md)
- [`docs/HARDWARE_PROFILES.md`](docs/HARDWARE_PROFILES.md) when changing hardware profiles

## Development setup

Create and activate a virtual environment, then install the project in editable mode:

```bash
python -m pip install -e ".[dev,build]"
```

Run RasterMint from source:

```bash
python launcher.py
```

Before submitting a change, run:

```bash
python -m pytest
python -m compileall -q src tests
```

Platform packaging changes should also be validated by the corresponding GitHub Actions build.

## Engineering guidelines

### Keep one rendering pipeline

Image/video frame processing belongs in `src/rastermint/core/` whenever practical. Preview, still export, animation, video, batch, presets, and hardware processing should call the same core behavior rather than maintaining separate implementations.

### Keep GUI startup lightweight

Do not add heavy top-level imports to the QML backend/startup path. NumPy, Pillow, FFmpeg/media code, and expensive render modules should remain lazy until processing/export needs them.

### Keep QML data-driven

Prefer shared components and schema/model data over one-off controls. New QML must compile in the offscreen smoke suite and should use RasterMint's themed controls where an equivalent component exists.

### Effects and dithering

New stack effects should be defined through the effect schema and rendered through the shared effect stack. Numeric parameters intended for the timeline should be explicitly animatable; spatial parameters should participate correctly in preview scaling.

For classic error-diffusion algorithms, add the kernel/divisor to the existing algorithm model. Other dithering families should follow the extension guide and preserve deterministic behavior where expected.

### Data files

Themes, palettes, presets, and hardware profiles should use stable IDs and normal human-readable JSON. Do not encode UI behavior in filenames when an explicit data field can represent it.

### External research

Do not copy source code from external projects simply because they implement a similar feature. Research behavior and ideas, verify licensing, and implement RasterMint functionality independently. See [`docs/FEATURE_RESEARCH.md`](docs/FEATURE_RESEARCH.md).

## Tests

Add the smallest test that protects the behavior being changed.

Prefer, in order:

1. a core behavioral test;
2. a QML runtime/compile test for actual Qt behavior;
3. a focused source-contract regression test only when runtime coverage would be impractical.

Avoid duplicating the same invariant across several files. Historical regression tests should be removed once a stronger general test fully covers the failure class.

See [`docs/TESTING.md`](docs/TESTING.md) for the full test strategy.

## Pull requests

Keep pull requests scoped and explain:

- what changed;
- why it changed;
- what user-visible behavior is affected;
- what tests were added or updated;
- whether packaging or cross-platform behavior changed.

Do not include generated build output, virtual environments, caches, or unrelated formatting churn.

## Licensing of contributions

To keep commercial licensing possible, external code contributions are not accepted unless the contributor and Draconov, the project owner, have agreed to appropriate contributor terms in writing before the contribution is merged. Bug reports, feature requests, testing feedback, and other non-code suggestions are welcome.

Do not submit third-party code that you do not have the right to contribute.
