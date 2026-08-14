# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

from rastermint.core.dither import ALGORITHMS
from rastermint.core.palette import BUILTIN_PALETTES
from rastermint.core.processor import process_image
from rastermint.core.settings import ProcessingSettings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RasterMint command-line image processor")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--algorithm", choices=ALGORITHMS, default="Floyd-Steinberg")
    parser.add_argument("--palette", choices=BUILTIN_PALETTES.keys(), default="Ink")
    parser.add_argument("--colors", nargs="+", help="Custom palette as hex colors, e.g. #000000 #FFFFFF")
    parser.add_argument("--brightness", type=int, default=0)
    parser.add_argument("--contrast", type=int, default=0)
    parser.add_argument("--saturation", type=int, default=0)
    parser.add_argument("--gamma", type=float, default=1.0)
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


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    palette = args.colors if args.colors else BUILTIN_PALETTES[args.palette]
    settings = ProcessingSettings(
        algorithm=args.algorithm,
        brightness=args.brightness,
        contrast=args.contrast,
        saturation=args.saturation,
        gamma=args.gamma,
        dither_strength=args.strength,
        pixel_size=args.pixel_size,
        serpentine=args.serpentine,
        output_divisor=args.downscale,
        palette=list(palette),
    )
    with Image.open(args.input) as source:
        result = process_image(source.convert("RGB"), settings)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.save(args.output)
    print(f"Saved {args.output} ({result.width}x{result.height})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
