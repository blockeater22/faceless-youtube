"""Command-line entry point.

    python -m faceless build stories/my_story.json
    python -m faceless build stories/my_story.json --formats 9:16
    python -m faceless poses        # render a pose cheatsheet for authoring
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .model import RESOLUTIONS


def _build(args) -> int:
    from .render import build
    fmts = [f.strip() for f in args.formats.split(",")] if args.formats else None
    if fmts:
        bad = [f for f in fmts if f not in RESOLUTIONS]
        if bad:
            print(f"unknown format(s): {bad}; choose from {list(RESOLUTIONS)}")
            return 2
    outputs = build(args.story, formats=fmts, outroot=args.out)
    print("\nFinished:")
    for p in outputs:
        print(f"  {p}  ({p.stat().st_size/1e6:.1f} MB)")
    return 0


def _poses(args) -> int:
    """Render every named pose to a single PNG - handy when writing stories."""
    from PIL import Image, ImageDraw, ImageFont
    from .draw import Sketcher
    from .figures import POSES, draw_figure

    cols, cell = 5, 340
    rows = (len(POSES) + cols - 1) // cols
    size = (cols * cell, rows * cell)
    sheet = Image.new("RGBA", size, (14, 19, 32, 255))
    sk = Sketcher(size, (242, 237, 225), 6, 1.4, 3)
    for i, (name, pose) in enumerate(POSES.items()):
        cx, cy = (i % cols) * cell, (i // cols) * cell
        draw_figure(sk, (cx + cell / 2, cy + cell * 0.58), 170, pose, color=(242, 237, 225))
    sk.composite_onto(sheet)
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
    except Exception:
        font = ImageFont.load_default(24)
    for i, name in enumerate(POSES):
        cx, cy = (i % cols) * cell, (i // cols) * cell
        d.text((cx + cell / 2, cy + cell - 26), name, font=font, anchor="mm", fill=(255, 180, 84, 255))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    sheet.convert("RGB").save(args.out)
    print(f"pose sheet -> {args.out}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="faceless", description="stick-figure story video engine")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="render a story JSON to video(s)")
    b.add_argument("story", help="path to a story .json")
    b.add_argument("--formats", help="comma list: 9:16,16:9,1:1 (default both 9:16 & 16:9)")
    b.add_argument("--out", default="output", help="output root dir")
    b.set_defaults(fn=_build)

    s = sub.add_parser("poses", help="render a pose cheatsheet")
    s.add_argument("--out", default="output/_pose_sheet.png")
    s.set_defaults(fn=_poses)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
