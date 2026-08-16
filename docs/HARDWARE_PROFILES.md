# Hardware Profiles

RasterMint hardware profiles are data-driven bundles for converting a still image or decoded media frame toward the graphics and display characteristics of a retro platform.

They are **not emulators**. RasterMint does not emulate a CPU, PPU/GPU, video encoder, electrical signal path, sprite scheduler, or game engine. Strict mode applies image-space constraints that are meaningful for an already-rendered frame.

## Pipeline position

```text
source image / decoded frame
    ↓
crop · flip · rotate
    ↓
target framebuffer raster
    ↓
reorderable effect stack
    ↓
hardware graphics constraints (Strict mode)
    ↓
raw framebuffer
    ↓
pixel-aspect correction (optional)
    ↓
display treatment (optional)
    ↓
preview / export
```

The framebuffer and display view stay separate. A 320×200 framebuffer can therefore remain 320×200 internally while the viewport shows pixel-aspect-corrected output.

## Visual vs Strict

### Visual

Visual mode applies selected profile metadata such as:

- target raster;
- palette when the platform has a useful fixed palette;
- pixel aspect ratio;
- recommended dither;
- CRT/LCD-style display treatment.

It intentionally prioritizes a recognizable creative result rather than enforcing every historical graphics rule.

### Strict

Strict mode can additionally enforce the image-space constraints described by the profile, for example:

- fixed-palette mapping;
- RGB channel bit depth;
- global color count;
- per-tile/attribute-region color count;
- grouped attribute palettes.

A profile declares whether RasterMint currently has a meaningful Strict implementation. Unsupported strict behavior falls back to visual processing rather than pretending to emulate behavior that is not implemented.

## Selective application

The Hardware Profile panel has independent switches for:

```text
Raster   Palette   PAR   Limits   Display
```

That means a profile is not an all-or-nothing preset. For example, you can take only the palette and pixel aspect ratio while keeping your current target resolution and effect stack.

## Built-in profiles

Current data files live in:

```text
src/rastermint/data/hardware_profiles/
```

The initial set includes profiles for handhelds, consoles, and home/PC graphics modes, including Game Boy-family systems, NES/SNES, Mega Drive/Genesis, ZX Spectrum, CGA/EGA, Commodore 64, Amiga OCS, and Apple II high-resolution graphics.

Some profiles use fixed palettes. Others describe a native/master color depth instead; those are represented with channel-depth constraints rather than inventing one universal game palette.

## Profile JSON

A profile is normal JSON. A simplified example:

```json
{
  "id": "example-system",
  "name": "Example System",
  "category": "Console",
  "summary": "Example still-image graphics profile.",
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

Custom profile JSON can be loaded from the Hardware Profile panel without recompiling RasterMint.

## Constraint keys

The generic constraint engine currently understands:

```text
fixed_palette
global max_colors_global
channel_bits
tile_width
tile_height
tile_max_colors
tile_palette_groups
```

Keep constraints generic. A new profile should not require a profile-name-specific branch in QML or `qmlui/backend.py`.

## Pixel aspect ratio

`pixel_aspect` is stored as pixel **width : height**.

RasterMint keeps the raw framebuffer unchanged and applies aspect correction only when the selected view is `Corrected pixels` or `Display simulation`.

This is important for export reproducibility: a project can save both the logical framebuffer size and the way those pixels should be presented.

## Display treatment

The current lightweight display stage supports:

- gamma;
- horizontal color bleed approximation;
- Gaussian blur;
- scanline darkening;
- LCD grid darkening.

These are creative display treatments, not analog signal emulation. More sophisticated display models should stay separate from the hardware graphics constraint engine so users can eventually mix a framebuffer profile with a different display profile.

## Adding a profile

1. Add a JSON file under `src/rastermint/data/hardware_profiles/`.
2. Give it a unique stable `id`.
3. Use only constraints supported by `core/hardware.py`.
4. Be conservative about `strict.supported`.
5. Add a test for raster, palette/depth, and any unusual constraint.
6. Run `pytest` and `python -m compileall -q src tests`.

When historical behavior is ambiguous or depends on analog output, document the approximation instead of presenting one conversion as universally exact.
