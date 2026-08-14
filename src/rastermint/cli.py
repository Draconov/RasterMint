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
    p = argparse.ArgumentParser(description="RasterMint command-line image processor")
    p.add_argument("input", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--algorithm", choices=ALGORITHMS, default="Floyd-Steinberg")
    p.add_argument("--palette", choices=BUILTIN_PALETTES.keys(), default="Ink")
    p.add_argument("--colors", nargs="+", help="Custom palette as hex colors, e.g. #000000 #FFFFFF")
    p.add_argument("--brightness", type=int, default=0)
    p.add_argument("--contrast", type=int, default=0)
    p.add_argument("--saturation", type=int, default=0)
    p.add_argument("--gamma", type=float, default=1.0)
    p.add_argument("--strength", type=float, default=1.0)
    p.add_argument("--pixel-size", type=int, default=1)
    p.add_argument("--no-serpentine", action="store_true")
    return p


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
        serpentine=not args.no_serpentine,
        palette=list(palette),
    )
    with Image.open(args.input) as source:
        result = process_image(source.convert("RGB"), settings)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.save(args.output)
    print(f"Saved {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
