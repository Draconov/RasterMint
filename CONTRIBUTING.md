# Contributing

1. Create a virtual environment.
2. Install with `pip install -e '.[dev,build]'`.
3. Read [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and [`docs/EXTENDING_RASTERMINT.md`](docs/EXTENDING_RASTERMINT.md).
4. Keep image/video frame processing in `src/rastermint/core/` independent from Qt when practical.
5. Add or update tests for processing changes.
6. Run `python -m compileall -q src tests` and `pytest` before opening a pull request.

New stack effects should be described in `EFFECT_DEFINITIONS`, validated through the core, and rendered through `apply_effect_stack()` so preview, presets, batch, still export, animation, and video export stay on the same pipeline.

For a new error-diffusion algorithm, add its kernel/divisor to `ERROR_DIFFUSION_KERNELS` and keep the all-algorithms palette/determinism tests passing. For other dithering families, follow the standalone-algorithm checklist in the extension guide.

Do not copy implementation code from external projects merely because they solve a similar problem. Check the source license first and keep research-only references clearly separated from RasterMint code.

## Licensing of contributions

To keep commercial licensing possible, external code contributions are not accepted unless the contributor and Draconov, the project owner, have agreed to appropriate contributor terms in writing before the contribution is merged. Bug reports, feature requests, testing feedback, and other non-code suggestions are welcome.

Do not submit third-party code that you do not have the right to contribute.
