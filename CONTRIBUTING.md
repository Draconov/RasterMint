# Contributing

1. Create a virtual environment.
2. Install with `pip install -e '.[dev,build]'`.
3. Add or update tests for processing changes.
4. Run `pytest` before opening a pull request.
5. Keep image-processing code in `src/rastermint/core/` independent from Qt when practical.

For a new error-diffusion algorithm, add its kernel and divisor to `ERROR_DIFFUSION_KERNELS` and add a regression test that verifies all output colors belong to the selected palette.
