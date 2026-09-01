# Pixel Art Cleanup Lab

RasterMint 0.7.0 adds **Pixel Art Cleanup** as a normal non-destructive layer under **Pixel & Dither**. It runs in the same shared processing stack as still previews, exports, presets, projects, animation, and video.

## Cleanup controls

- **Orphan-pixel removal** replaces isolated pixels that have almost no same-colour support.
- **Cluster cleanup** conservatively smooths weak local clusters over 1–4 passes.
- **Line cleanup** repairs one-pixel breaks and protrusions along horizontal, vertical, and diagonal lines.
- **Staircase correction** removes common 2×2 three-against-one stair-step burrs.
- **Tiny-island maximum** removes connected colour islands up to the selected pixel count. Set it to 0 to disable island removal.
- **Edge preservation** protects meaningful local contours during line, stair, and cluster cleanup. True orphan pixels and explicitly targeted tiny islands are still eligible for removal.
- **Cluster connectivity** selects 4-neighbour or 8-neighbour component grouping.

Clean Result never invents a new colour: replacements are selected from colours already present in neighbouring pixels, so a cleanup layer placed after a palette-limited dither remains palette-safe.

## Visualization

**Visualization** has three views:

- **Clean Result** — normal editable cleanup output.
- **Issue Overlay** — diagnostic colours mark weak clusters, line issues, staircase candidates, tiny islands, and orphan pixels.
- **Cluster Map** — each connected colour cluster receives a deterministic diagnostic colour for inspection.

The diagnostic views are intended for analysis; unlike Clean Result they deliberately use colours outside the source palette.

## Workflow

A common stack is:

```text
Dither
Pixel Art Cleanup
Dither Glow / Display Effects
```

Because cleanup is a normal layer it supports RasterMint's layer opacity, blend mode, masks, enable/bypass, reorder, duplicate/reset, undo/redo, preset saving, and project serialization without a destructive Apply command.
