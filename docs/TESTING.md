# Testing RasterMint

RasterMint's test suite is intentionally small enough to run on every change while still protecting the processing pipeline, QML startup, packaging contracts, and known regression classes.

## Principles

- Test **behavior**, not implementation text, whenever practical.
- Keep one strong test instead of several overlapping weaker tests.
- Use real offscreen QML compilation/runtime checks for Qt behavior.
- Keep focused source-contract tests only for invariants that are difficult or expensive to prove dynamically.
- A historical regression test can be removed when a broader test now covers the entire failure class.

## Running tests

Install development dependencies:

```bash
python -m pip install -e ".[dev]"
```

Run everything:

```bash
python -m pytest
```

Show the slowest tests:

```bash
python -m pytest --durations=20
```

Run a specific area:

```bash
python -m pytest tests/test_palette.py
python -m pytest tests/test_qml_runtime.py
```

## Test layers

### Core behavior

Most tests exercise pure Python processing under `src/rastermint/core/`:

- dithering;
- palettes and extraction;
- effects/effect stack;
- raster/transform behavior;
- hardware constraints;
- presets/history;
- animation/media/batch/export behavior.

These should remain Qt-independent whenever possible.

### QML compile smoke test

`tests/test_qml_runtime.py` compiles **every packaged QML file** in an offscreen Qt environment. Each component is reported independently, which makes CI failures easy to locate.

This catches errors such as:

- invalid QML syntax;
- unavailable component types;
- invalid property assignments resolved at compile time;
- missing imported local components.

### Main-window runtime smoke tests

The same module also loads `Main.qml` in offscreen/software-rendering mode for runtime UI assertions such as:

- application window creation;
- top-menu popup visibility/geometry;
- inspector minimum width;
- popup focus release.

These runtime checks are deliberately stronger than searching QML source for particular strings.

### Startup/packaging contracts

`tests/test_startup_optimization.py` protects startup and frozen-build assumptions, including:

- no eager render-pipeline imports from the GUI backend graph;
- deferred backend import in `app.py`;
- lean FFmpeg selection;
- PyInstaller hook/manifest expectations.

### Focused regression contracts

Files such as `test_ui_regressions.py` and `test_startup_regressions.py` exist for bugs that are not yet fully expressed by a general behavioral test.

Do not keep adding string assertions for every UI bug. Prefer moving coverage into the real QML runtime suite when possible.

## QML in CI

GitHub Actions runs QML tests on Linux with:

```text
QT_QPA_PLATFORM=offscreen
QSG_RHI_BACKEND=software
```

The workflow installs the EGL/OpenGL/XKB/XCB runtime libraries required by QtGui/Qt Quick even without a visible display.

Local environments without PySide6 will skip the QML runtime module; official CI installs the project dependencies and must run it.

## Test optimization policy

Do not remove coverage just to reduce the test count.

A test is a good removal/consolidation candidate when:

- another test exercises the same invariant more directly;
- a static source-text check duplicates a real runtime QML check;
- a parametrized test repeats expensive application setup that can be shared safely;
- it protects obsolete migration history rather than current behavior.

When optimizing test setup, preserve clear failure messages. For example, the QML compilation test aggregates failures by filename instead of hiding which component failed.

## Before release-oriented changes

Run:

```bash
python -m pytest
python -m compileall -q src tests
```

For packaging changes, also allow GitHub Actions to build all affected platforms. A successful Python/QML test run does not prove that a PyInstaller/Qt plugin change is safe on Windows or macOS.
