#!/usr/bin/env python3
"""Create readable contact sheets for human review of every rendered Word page."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--columns", type=int, default=2)
    parser.add_argument("--pattern", default="page-*.png")
    args = parser.parse_args()
    pages = sorted(args.input_dir.glob(args.pattern))
    if not pages:
        raise SystemExit("No page PNGs found")
    thumb_width = 900
    thumbnails = []
    for page in pages:
        image = Image.open(page).convert("RGB")
        height = round(image.height * thumb_width / image.width)
        image.thumbnail((thumb_width, height))
        canvas = Image.new("RGB", (thumb_width + 20, height + 55), "white")
        canvas.paste(image, (10, 35))
        ImageDraw.Draw(canvas).text((10, 10), page.stem, fill="black")
        thumbnails.append(canvas)
    rows = math.ceil(len(thumbnails) / args.columns)
    cell_width = max(image.width for image in thumbnails)
    cell_height = max(image.height for image in thumbnails)
    sheet = Image.new("RGB", (cell_width * args.columns, cell_height * rows), "#D0D0D0")
    for index, image in enumerate(thumbnails):
        sheet.paste(image, ((index % args.columns) * cell_width, (index // args.columns) * cell_height))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.output, quality=90)
    print(args.output)


if __name__ == "__main__":
    main()
