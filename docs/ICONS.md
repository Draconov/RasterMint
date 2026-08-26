# RasterMint Icons

RasterMint keeps both platform application artwork and inspector/sidebar artwork under:

```text
src/rastermint/data/icons/
```

## Application icons

| Asset | Purpose |
| --- | --- |
| `rastermint.ico` | Windows executable icon |
| `rastermint.icns` | macOS application bundle icon |
| `rastermint.png` | Runtime/window icon and Linux fallback |
| `rastermint-16.png` … `rastermint-1024.png` | Size-specific PNG variants |

The documentation copy used by the README lives at `docs/assets/rastermint-icon.png`.

### Runtime behavior

`rastermint.app` loads `data/icons/rastermint.png` through package resources and sets it as the Qt application/window icon when available.

### Packaging

`build/rastermint.spec` uses:

- `.ico` for the Windows PyInstaller executable;
- `.icns` for the macOS bundle.

Linux desktop environments use the runtime PNG unless a distribution package supplies additional desktop metadata.

## Sidebar icons

RasterMint also packages ten `sidebar-*.png` files. The inspector currently uses nine monochrome PNGs directly as shape masks:

```text
sidebar-random.png
sidebar-presets.png
sidebar-hardware.png
sidebar-layers.png
sidebar-source.png
sidebar-preview.png
sidebar-raster.png
sidebar-animation.png
sidebar-media-playback.png
```

`sidebar-palettes.png` is retained as an artwork/source asset, but the current Palette navigation button is intentionally rendered as four live theme swatches instead of loading that PNG.

### Rendering and theme tinting

Sidebar artwork is intended as **32×32 monochrome pixel-style PNG** imagery. `InspectorNavButton.qml` treats the PNG RGB values as disposable and uses the alpha/shape as a mask. Tinting is performed with pure QtQuick `Canvas` composition using `source-in`:

- inactive static icon → `theme.textColor`;
- active static icon → `theme.accentColor`;
- selected button background → `theme.selectionColor`;
- Palette icon → four live swatches from `panelRaisedColor`, `selectionColor`, `accentColor`, and `textColor`.

This avoids a dependency on `Qt5Compat.GraphicalEffects`, which is not guaranteed to exist in RasterMint's Linux CI/runtime environment.

The visible text labels were removed from the narrow sidebar, but each navigation button keeps its translated label and exposes it as a hover tooltip.

## Updating application artwork

When replacing the application artwork:

1. regenerate all platform/PNG variants from the same source artwork;
2. preserve the existing filenames unless the spec/runtime loader is updated too;
3. verify transparency and edge quality at 16/24/32 px;
4. verify Windows and macOS packaged artifacts, not only the development window;
5. run `tests/test_icon_assets.py` and the normal test suite.

## Updating sidebar artwork

When replacing a sidebar icon:

1. keep the intended artwork at 32×32 and preserve transparent background/alpha;
2. keep it monochrome unless the renderer is deliberately being changed — the active theme supplies the final color;
3. preserve the existing `sidebar-*.png` filename or update the corresponding `Main.qml` `iconSource`;
4. keep the human-readable button text because it is used for localization/accessibility and the hover tooltip;
5. verify both light and dark themes, including the active `theme.accentColor` state;
6. run the QML/runtime tests. `tests/test_ui_regressions.py` currently protects the nine static sidebar asset references and the Canvas tinting contract.

If the Palette button behavior changes, remember that it is currently a generated theme-swatch icon rather than a static image.
