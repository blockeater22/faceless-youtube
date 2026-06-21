#!/usr/bin/env python3
"""Generate a 1280x720 YouTube thumbnail with the faceless engine.

Edit the constants and re-run:  python branding/make_thumbnail.py
"""
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from faceless.draw import Sketcher                 # noqa: E402
from faceless.figures import draw_figure, get_pose  # noqa: E402
from faceless.render import _background, _font      # noqa: E402

BG = (14, 19, 32)
INK = (242, 237, 225)
ACCENT = (255, 180, 84)
WHITE = (255, 255, 255)

BIG_NUMBER = "7"
LINES = [                       # (text, colour) per line, left-aligned
    [("THOUGHTS", WHITE)],
    [("THAT CHANGE", WHITE)],
    [("EVERYTHING", ACCENT)],
]
OUT = Path(__file__).resolve().parent / "thumbnail_seven_thoughts.png"


def _line(d, segs, x0, y, font, stroke):
    x = x0
    for text, color in segs:
        d.text((x, y), text, font=font, fill=color + (255,), anchor="la",
               stroke_width=stroke, stroke_fill=(0, 0, 0, 255))
        x += font.getlength(text)


def thumbnail():
    w, h = 1280, 720
    img = _background((w, h), BG, 0.62).copy()
    sk = Sketcher((w, h), INK, 7, 2.2, 11)

    # starfield across the top
    rng = random.Random(7)
    for _ in range(18):
        x, y = rng.uniform(0.04, 0.98) * w, rng.uniform(0.04, 0.46) * h
        sk.dot((x, y), rng.uniform(2.5, 5.5), color=ACCENT if rng.random() < 0.5 else WHITE)

    # figure gazing up (bottom-left, under the number; feet kept in frame)
    draw_figure(sk, (w * 0.19, h * 0.80), h * 0.38, get_pose("look_up"), color=INK)
    sk.composite_onto(img)

    d = ImageDraw.Draw(img)
    # giant hero number
    d.text((w * 0.15, h * 0.45), BIG_NUMBER, font=_font(400), anchor="mm",
           fill=ACCENT + (255,), stroke_width=18, stroke_fill=(0, 0, 0, 255))

    # stacked headline, auto-fit so the widest line stays inside the frame
    x0 = w * 0.34
    max_w = w * 0.965 - x0
    size = 150
    while size > 48:
        f = _font(size)
        widest = max(sum(f.getlength(t) for t, _ in segs) for segs in LINES)
        if widest <= max_w:
            break
        size -= 3
    line_font = _font(size)
    lh = int(size * 1.14)
    stroke = max(8, size // 9)
    y = (h - lh * len(LINES)) // 2
    for segs in LINES:
        _line(d, segs, x0, y, line_font, stroke=stroke)
        y += lh

    img.convert("RGB").save(OUT)
    print("wrote", OUT, "->", Image.open(OUT).size)


if __name__ == "__main__":
    thumbnail()
