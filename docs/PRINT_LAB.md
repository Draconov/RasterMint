# Print Lab

RasterMint 0.6.0 adds **Print Lab → AM Halftone / Screen Print** as a dedicated editable layer and export workflow. It is intentionally separate from RasterMint's ordinary `Halftone` dither: the ordinary dither is a fast visual raster effect, while Print Lab builds independent ink separations and can export those screens as usable vector artwork.

## Modes

| Mode | Separations |
| --- | --- |
| Monochrome | One editable black/spot-style screen |
| CMYK | Cyan, Magenta, Yellow, Black |
| RGB | Red, Green, Blue physical-color screens |
| Spot Colors | 1–8 user-selected inks |

CMYK starts with conventional editable angles: **C 15°, M 75°, Y 0°, K 45°**. Spot Color mode can copy the first eight colors from RasterMint's active palette and remains fully editable afterward.

## Print Setup

- **Cell size / frequency** controls screen scale.
- **Dot shape** supports Round, Ellipse, Square, Diamond, and Line geometry.
- **Paper color** sets the unprinted substrate/background.
- **Dot gain** changes screen coverage instead of applying global image contrast.
- **Black generation / mix** controls how much common CMY darkness is moved into the K separation through under-color removal.
- **Subtractive overprint / ink mixing** uses multiplicative transmittance so overlapping inks darken instead of being averaged together.

## Separations / Inks

Every active separation has its own:

- ink color;
- screen angle;
- opacity;
- X/Y registration offset;
- optional X/Y phase offset.

Spot Color mode generates these controls dynamically for the selected 1–8 ink count.

## Registration and imperfections

Print Lab can stay mathematically clean or deliberately simulate physical printing with:

- automatic registration error;
- screen roughness;
- missing / weak ink patches;
- irregular ink spread;
- paper-grain interaction;
- squeegee / coverage bands.

The random-looking components are deterministic for a given seed/settings so previews and exports remain reproducible.

## Preview

The Print Lab layer can show the normal **Composite** or an individual active screen (Cyan/Magenta/Yellow/Black, RGB, or Spot 1…8). Individual previews are shown as black-on-white stencil proofs for easy inspection.

Print Lab uses RasterMint's existing preview modes. Version 0.6.0 does **not** introduce a separate preview-quality system or a forced-100% preview mode.

## Separation export

**Export Separations…** chooses an output directory and runs off the UI thread. For CMYK with source name `image`, output is:

```text
image_cyan.svg
image_cyan.png
image_magenta.svg
image_magenta.png
image_yellow.svg
image_yellow.png
image_black.svg
image_black.png
image_composite.png
```

Spot Color mode emits the same SVG/PNG pair for each active spot screen. SVG files contain actual vector screen geometry (`circle`, `ellipse`, `rect`, or `polygon` primitives depending on the selected shape); they do not wrap an embedded raster image. Raster separation PNGs are grayscale proofs, and the composite PNG shows the combined print simulation.

Transparent areas of the source are treated as **no ink**, preventing hidden RGB data under transparent pixels from leaking into stencils.

## Built-in Print Lab presets

0.6.0 includes:

- Clean CMYK Print
- Vintage Screen Print
- 2-Color Poster
- 3-Color Risograph
- Newspaper CMYK
- Misregistered Print
- Cheap T-Shirt Print
- Heavy Dot Gain

Each preset creates/configures the same ordinary editable Print Lab layer; there is no hidden preset-only renderer.

## Shared pipeline and serialization

Print Lab participates in the normal effect stack and therefore uses RasterMint's existing layer enable/bypass, opacity/blend/mask compositing, undo/redo, project/preset serialization, animation/video frame pipeline, stale-render protection, and cumulative layer cache where applicable. New settings use defaults when absent, so older settings/presets do not require Print Lab fields to load.

Dedicated separation export renders the stack prefix before Print Lab at full export quality, then generates the screens. The existing render-progress policy is retained: fast jobs do not flash a progress overlay, while operations predicted/observed to exceed roughly five seconds report progress and ETA.
