# Extending RasterMint

This guide describes the preferred path for adding features without splitting RasterMint into multiple processing implementations or making GUI startup heavier.

## Before adding code

Identify which layer owns the feature:

| Feature | Preferred location |
| --- | --- |
| Image processing | `src/rastermint/core/` |
| Dithering metadata | `core/dither_metadata.py` |
| Dithering implementation | `core/dither.py` |
| Effect schema | `core/effect_schema.py` |
| Effect rendering | `core/effect_stack.py` |
| Palette logic | `core/palette*.py` |
| Gradient definitions | `core/gradient_presets.py` |
| Hardware metadata | `core/hardware_profiles.py` |
| Hardware rendering | `core/hardware.py` |
| QML-facing state/actions | `src/rastermint/qmlui/` |
| Interface | `src/rastermint/qml/` |
| Theme definitions | `src/rastermint/data/themes/` |
| Translation dictionaries | `src/rastermint/data/translations/` |
| Sidebar/application artwork | `src/rastermint/data/icons/` |
| Other static built-in data | `src/rastermint/data/` |

Avoid putting processing logic directly in QML or duplicating a core algorithm inside an export path.

## The shared-pipeline rule

A feature that affects pixels should normally work through the same processing path for:

- live preview;
- still export;
- batch processing;
- animation frames;
- decoded video/GIF frames.

Preview may reduce source resolution for responsiveness, but it should not use a different visual algorithm.

## Adding an effect

### 1. Define the effect schema

Add the effect to `core/effect_schema.py` with:

- a stable type/id;
- display label/category;
- default parameters;
- value ranges/choices;
- `animatable` metadata for suitable numeric parameters;
- `pixel_scaled` metadata for parameters measured in image pixels.

### 2. Implement rendering

Add the implementation to the effect renderer used by `apply_effect_stack()`.

Prefer functions that:

- accept a PIL RGB image and normalized parameters;
- do not read the source file directly;
- preserve dimensions unless geometry change is intentional;
- are deterministic unless randomness/time is explicitly part of the effect.

### 3. Test behavior

Add a focused core test for the behavior itself. If QML is generated from schema metadata, do not add a source-text UI test merely to prove the label exists.

## Adding a dithering algorithm

### Error diffusion

Classic error-diffusion algorithms should use the shared kernel/divisor machinery when possible. Add metadata to the lightweight metadata layer and the kernel/implementation to `core/dither.py`.

Keep the all-algorithm tests passing:

- output uses palette colors only;
- deterministic algorithms remain deterministic;
- optimized paths match their reference behavior where tested.

### Ordered/pattern dithering

Reusable threshold matrices should live with the ordered-dither implementation rather than in QML.

### New algorithm families

A fundamentally different algorithm can have its own function, but it should still accept the same normalized palette/settings inputs and return the same image contract.

## Adding a built-in palette

Built-in palette JSON belongs under the appropriate `src/rastermint/data/palettes/` category.

Use:

- a stable unique ID;
- a clean human-readable name;
- valid HEX colors;
- useful category/description/source metadata where applicable.

Do not add numeric filename prefixes merely to force ordering. If curated ordering is needed, preserve it explicitly in the loader/library.

## Adding a gradient preset

Gradient presets live in `core/gradient_presets.py` and should define useful anchor colors and interpolation behavior.

A gradient preset must ultimately produce the same active palette state as the custom gradient generator. Selecting the preset should apply that generated palette to the current image rather than acting as a disconnected visual preview.

Keep large preset browsers lazy/collapsed so the application does not instantiate hundreds of delegates during startup.

## Palette import/export

File parsing belongs in `core/palette.py`, not in QML file-dialog handlers.

Current palette file support includes:

- HEX/text;
- GIMP `.gpl`;
- JASC `.pal`.

QML should only normalize the selected URL/path and call the backend.

## Lospec integration

Responsibilities are separated as follows:

```text
core/lospec.py             slug/URL validation, fetch, JSON parsing
qmlui/backend.py           QML-facing action and status/error handling
qml/pages/PalettePage.qml  user controls
```

Use Lospec's documented per-palette JSON endpoint rather than scraping the Palette List HTML.

## Adding a hardware profile

Prefer a new JSON profile over profile-name branches in Python/QML.

1. Add a JSON file under `src/rastermint/data/hardware_profiles/`.
2. Give it a stable unique `id`.
3. Use existing generic constraints where possible.
4. Only mark `strict.supported` when RasterMint can meaningfully enforce the stated image-space behavior.
5. Add tests for unusual raster/palette/constraint behavior.

See [`HARDWARE_PROFILES.md`](HARDWARE_PROFILES.md).

## Adding animation support

Most numeric effect parameters become animation-compatible through schema metadata.

Do not create a second animation renderer. Animation should:

1. copy base settings;
2. evaluate tracks at time `t`;
3. apply evaluated values;
4. call the normal processor.

Identity values and random seeds should generally not be animatable unless the effect explicitly defines meaningful interpolation.

## Temporal effects

Time-dependent effects receive a frame/time context from the shared processing path. They should be deterministic for the same source/settings/time unless intentional nondeterminism is part of the feature.

Export and rendered-preview behavior must agree for the same frame context.

## Video-compatible processing

An effect is naturally video-compatible when it processes one RGB frame without depending on the source file container.

Keep:

- decoding/encoding in `core/media.py` / media helpers;
- frame image processing in the normal core pipeline.

Do not invoke FFmpeg from individual effects.

## Preview performance

Before introducing native acceleration or another dependency:

1. benchmark the actual hot path;
2. reduce allocations/copies;
3. use vectorization where it preserves behavior;
4. keep a deterministic reference test where practical;
5. only then consider a dependency.

Expensive algorithms can receive smaller interactive preview budgets. Never apply those preview limits to final export.

## GUI startup performance

Do not import heavy render modules at QML/backend module import time.

Avoid top-level imports of:

- NumPy;
- Pillow image modules;
- `core.processor`;
- `core.effect_stack`;
- `core.hardware`;
- `core.media`;
- GIF/batch/export render helpers.

Use lightweight metadata modules or local imports inside worker/operation methods. `tests/test_startup_optimization.py` protects this contract.

## Adding a theme

Built-in themes are JSON files under `src/rastermint/data/themes/`. Use a stable `id`, a human-readable `name`, and the full set of existing theme color keys (`window`, `canvas`, `panel`, `panelRaised`, `panelHover`, `border`, `text`, `textMuted`, `accent`, `accentHover`, `accentText`, `danger`, `selection`, and `mirrorAxis`).

To add a built-in theme:

1. add the JSON file;
2. add its ID to `THEME_ORDER` in `qmlui/theme.py` at the intended chooser position;
3. verify normal text, muted text, selection, danger states, mirror axes, and the icon-only sidebar in both active/inactive states;
4. avoid theme-specific QML branches — controls should consume `ThemeManager` properties.

Unknown third-party theme IDs are still loaded and appended alphabetically after the curated built-in order.

## Adding a language

English is RasterMint's source language. User-visible QML strings should normally be wrapped with `qsTr("...")`. Do not translate stable processing identifiers, effect type IDs, preset/settings keys, serialized enum values, or other backend contracts.

To add a language:

1. add a JSON dictionary under `src/rastermint/data/translations/<language-id>.json` using the same source-string keys used by `qsTr`;
2. register the language ID in `LANGUAGE_ORDER` and its native display name in `LANGUAGE_NAMES` in `qmlui/localization.py`;
3. ensure packaging still includes `data/translations/`;
4. switch languages at runtime and verify menus, dialogs, inspector pages, dynamic labels, and tooltips retranslate without restart;
5. keep the product name **RasterMint** literal/non-translatable where it is branding.

`LocalizationManager` uses a JSON-backed `QTranslator` and `QQmlEngine.retranslate()`. Do not introduce `.qm`/`lrelease` tooling unless the localization architecture is intentionally being replaced. On first run/reset RasterMint selects the supported OS language when available and otherwise falls back to English; an invalid stored language also falls back to English.

## Adding or replacing a sidebar icon

Static inspector icons live under `src/rastermint/data/icons/` and are intended as 32×32 monochrome PNG shape masks. The RGB color in the file is not the final display color: `InspectorNavButton.qml` recolors the mask using the active theme (`textColor` when inactive, `accentColor` when selected).

When adding/replacing one:

1. preserve a transparent background and clean alpha edges;
2. keep the artwork monochrome and readable at 32×32;
3. reference it from the appropriate `InspectorNavButton` in `Main.qml`;
4. keep the button `text` property because it drives translated hover tooltips/accessibility;
5. do not add `Qt5Compat.GraphicalEffects` solely for tinting — the current pure QtQuick Canvas path exists to remain portable in Linux CI.

Palette is intentionally different: its sidebar icon is rendered from four current-theme swatches instead of a static PNG.

## QML changes

Use the shared themed components under `qml/components/` before introducing a raw Qt Quick Controls variant.

For new UI behavior:

- keep custom popups inside the Qt Quick scene when styling depends on QML;
- avoid binding loops and imperative writes that destroy declarative bindings;
- normalize `file:` URLs before Python slots;
- avoid eager creation of large delegate trees;
- let the offscreen QML compile/runtime suite catch real Qt errors.

## Presets and serialization

New user-facing state should round-trip through settings/presets unless it is intentionally session-only UI state.

Stable stored fields should be normalized on load so older presets can continue to open when practical.

## Batch and SVG behavior

Batch processing uses the same processing settings per source and restores source-specific dimensions when required by the chosen batch mode.

SVG export vectorizes the already-processed raster result. Keep vectorization separate from dithering/effects so raster/video output does not change.

## Testing checklist

For a new rendering feature:

- [ ] implementation lives in the appropriate core module;
- [ ] preview and export share the implementation;
- [ ] parameters are validated/clamped;
- [ ] presets/settings round-trip where applicable;
- [ ] spatial parameters scale correctly in preview;
- [ ] animation metadata is correct;
- [ ] a focused behavioral test exists;
- [ ] QML compiles if UI changed;
- [ ] `python -m pytest` passes;
- [ ] `python -m compileall -q src tests` passes;
- [ ] packaging changes are verified on all affected release platforms.

See [`TESTING.md`](TESTING.md) for test placement and regression-test policy.


## Data extension packs

User-installed, read-only data can be packaged without modifying RasterMint's install directory. Create a folder under RasterMint's user-data `extensions/` directory with an `extension.json` manifest:

```json
{
  "format": "rastermint-extension",
  "schema_version": 1,
  "id": "example-pack",
  "name": "Example Pack",
  "version": "1.0",
  "assets": {
    "palettes": "palettes",
    "themes": "themes",
    "translations": "translations",
    "hardware_profiles": "hardware_profiles",
    "presets": "presets"
  }
}
```

Only asset paths inside the extension folder are accepted. Omit asset types the pack does not provide. Files use the same JSON schemas as built-in/user equivalents; shipped IDs take precedence over collisions. Extension presets are read-only library entries, while extension translations can either add a language or augment an existing dictionary.

This mechanism intentionally does **not** execute arbitrary Python. A future Python effect-plugin API should be explicit/opt-in and versioned separately from safe data packs.
