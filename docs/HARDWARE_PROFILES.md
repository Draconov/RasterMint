# Hardware Profiles

RasterMint hardware profiles are data-driven descriptions for transforming a still image or decoded media frame toward the graphics and display characteristics of a retro platform.

They are **not emulators**. RasterMint does not reproduce CPU/GPU/PPU timing, sprite scheduling, game logic, electrical video signals, or analog hardware circuitry.

## Pipeline position

```text
source image / decoded frame
    ↓
source transforms
    ↓
target framebuffer raster
    ↓
reorderable effect stack
    ↓
hardware graphics constraints (Strict, when enabled/supported)
    ↓
logical framebuffer
    ↓
pixel-aspect correction (optional)
    ↓
display treatment (optional)
    ↓
preview / export
```

Framebuffer geometry and display presentation remain separate. A logical 320×200 frame can stay 320×200 while the corrected/display view uses non-square pixels.

## Visual and Strict modes

### Visual

Visual mode applies selected profile guidance such as:

- target raster;
- palette or channel-depth characteristics;
- recommended dithering;
- pixel aspect ratio;
- lightweight CRT/LCD-style display treatment.

Its purpose is a recognizable, useful creative result rather than complete hardware enforcement.

### Strict

Strict mode can additionally enforce supported image-space constraints, for example:

- fixed palette mapping;
- per-channel bit depth;
- global color count;
- per-tile/per-attribute-region color limits;
- grouped attribute palettes.

Each profile explicitly declares whether RasterMint has a meaningful Strict implementation. Unsupported behavior must not be presented as exact emulation.

## Selective application

A hardware profile is not all-or-nothing. The UI exposes independent profile components:

```text
Raster   Palette   PAR   Limits   Display
```

This allows, for example, using a machine's palette and pixel aspect ratio while keeping the current output raster/effect stack.

## Built-in profiles

Profile JSON files live in:

```text
src/rastermint/data/hardware_profiles/
```

The built-in set covers handhelds, consoles, home computers, PC graphics modes, and display treatments. Some machines have a useful fixed palette; others are better represented by master color depth/constraint metadata rather than an invented universal palette.

## JSON format

A profile is normal JSON. Simplified example:

```json
{
  "id": "example-system",
  "name": "Example System",
  "category": "Console",
  "summary": "Example image-space hardware profile.",
  "raster": {
    "width": 320,
    "height": 200,
    "pixel_aspect": [5, 6],
    "tile": [8, 8],
    "fit_mode": "fit"
  },
  "palette": {
    "type": "fixed",
    "name": "Example 4",
    "colors": ["#000000", "#55FFFF", "#FF55FF", "#FFFFFF"]
  },
  "recommended_dither": "Bayer 4x4",
  "visual": {
    "display": {
      "kind": "crt",
      "gamma": 1.05,
      "blur": 0.4,
      "color_bleed": 0.7,
      "scanlines": 0.12,
      "lcd_grid": 0.0
    }
  },
  "strict": {
    "supported": true,
    "constraints": {
      "fixed_palette": ["#000000", "#55FFFF", "#FF55FF", "#FFFFFF"],
      "max_colors_global": 4
    }
  }
}
```

Custom profile JSON can be loaded by RasterMint without recompiling the application.

## Main fields

### Identity and presentation

- `id` — stable machine/profile identifier;
- `name` — human-readable display name;
- `category` — grouping in the UI;
- `summary` — concise description suitable for UI help/tooltip text.

### Raster

Typical raster fields include:

- `width` / `height`;
- `pixel_aspect` as pixel width:height;
- `tile` dimensions when relevant;
- `fit_mode`.

### Palette

Profiles may provide a fixed palette or describe a broader color-depth model. Do not force a fixed palette onto hardware that historically allowed many game/application-specific subsets.

### Recommended dither

`recommended_dither` is guidance and does not imply that a historical machine implemented that software algorithm internally.

### Visual display treatment

The lightweight display stage can model creative approximations such as:

- gamma;
- horizontal color bleed;
- blur;
- scanline darkening;
- LCD grid darkening.

These are presentation effects, not analog signal emulation.

## Strict constraint keys

The generic constraint engine supports image-space rules including:

```text
fixed_palette
max_colors_global
channel_bits
tile_width
tile_height
tile_max_colors
tile_palette_groups
```

Keep constraints generic. A new profile should not require branching on a specific profile name inside QML or the QML backend.

## Pixel aspect ratio

`pixel_aspect` represents pixel **width : height**.

RasterMint keeps the logical framebuffer unchanged and applies aspect correction only in corrected/display presentation modes. This preserves reproducible logical raster dimensions for project settings and export.

## Adding a profile

1. Add a JSON file under `src/rastermint/data/hardware_profiles/`.
2. Use a unique, stable `id`.
3. Provide a concise `summary`.
4. Use existing generic constraints whenever possible.
5. Be conservative with `strict.supported`.
6. Add tests for unusual raster, palette/depth, or constraint behavior.
7. Run:

```bash
python -m pytest
python -m compileall -q src tests
```

When historical behavior is ambiguous, application-specific, or strongly dependent on analog output, document the approximation instead of presenting one conversion as universally exact.
