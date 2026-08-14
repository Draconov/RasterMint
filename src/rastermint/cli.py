# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

from rastermint.core.dither import ALGORITHMS
from rastermint.core.lospec import fetch_lospec_palette
from rastermint.core.palette import BUILTIN_PALETTES, read_palette_file
from rastermint.core.processor import process_image
from rastermint.core.settings import ProcessingSettings
from rastermint.core.svg_export import save_svg


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RasterMint command-line image processor")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--algorithm", choices=ALGORITHMS, default="Floyd-Steinberg")

    palette = parser.add_mutually_exclusive_group()
    palette.add_argument("--palette", choices=BUILTIN_PALETTES.keys(), default="Ink")
    palette.add_argument("--colors", nargs="+", help="Custom palette as hex colors, e.g. #000000 #FFFFFF")
    palette.add_argument("--palette-file", type=Path, help="Import .hex/.txt/.gpl/JASC .pal palette")
    palette.add_argument("--lospec", metavar="SLUG_OR_URL", help="Download a palette from Lospec")

    parser.add_argument("--brightness", type=int, default=0)
    parser.add_argument("--contrast", type=int, default=0)
    parser.add_argument("--saturation", type=int, default=0)
    parser.add_argument("--gamma", type=float, default=1.0)
    parser.add_argument("--grayscale", action="store_true", help="Convert to grayscale before dithering")
    parser.add_argument("--invert", action="store_true", help="Invert RGB values before dithering")
    parser.add_argument("--blur", type=float, default=0.0, metavar="RADIUS", help="Gaussian blur radius (0..20)")
    parser.add_argument("--sharpen", type=float, default=1.0, metavar="AMOUNT", help="Sharpness multiplier (0..4; 1 = unchanged)")
    parser.add_argument("--strength", type=float, default=1.0)
    parser.add_argument("--pixel-size", type=int, default=1)
    parser.add_argument(
        "--downscale",
        type=int,
        choices=range(1, 17),
        default=1,
        metavar="1..16",
        help="Output size divisor; 1 keeps original dimensions, 2 outputs half width/height, etc.",
    )
    scan = parser.add_mutually_exclusive_group()
    scan.add_argument("--serpentine", dest="serpentine", action="store_true")
    scan.add_argument("--no-serpentine", dest="serpentine", action="store_false")
    parser.set_defaults(serpentine=True)
    return parser


def _resolve_palette(args: argparse.Namespace) -> tuple[list[str], str, str, str]:
    if args.colors:
        return list(args.colors), "Custom", "", ""
    if args.palette_file:
        return read_palette_file(args.palette_file), args.palette_file.stem, "", str(args.palette_file.resolve())
    if args.lospec:
        remote = fetch_lospec_palette(args.lospec)
        return remote.colors, remote.name, remote.author, remote.source_url
    name = args.palette or "Ink"
    return BUILTIN_PALETTES[name].copy(), name, "RasterMint built-in", ""


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    colors, palette_name, palette_author, palette_source = _resolve_palette(args)
    settings = ProcessingSettings(
        algorithm=args.algorithm,
        brightness=args.brightness,
        contrast=args.contrast,
        saturation=args.saturation,
        gamma=args.gamma,
        grayscale=args.grayscale,
        invert=args.invert,
        blur_radius=args.blur,
        sharpen=args.sharpen,
        dither_strength=args.strength,
        pixel_size=args.pixel_size,
        serpentine=args.serpentine,
        output_divisor=args.downscale,
        palette=list(colors),
        palette_name=palette_name,
        palette_author=palette_author,
        palette_source=palette_source,
    )
    with Image.open(args.input) as source:
        result = process_image(source.convert("RGB"), settings)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.suffix.lower() == ".svg":
        save_svg(result, args.output)
    else:
        result.save(args.output)
    print(f"Saved {args.output} ({result.width}x{result.height})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
