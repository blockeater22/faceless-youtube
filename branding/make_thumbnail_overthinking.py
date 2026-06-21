#!/usr/bin/env python3
"""Thumbnail for 'How to Stop Overthinking': a figure with a tangled scribble
storm around its head + bold headline. Run: python branding/make_thumbnail_overthinking.py
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
MUTED = (138, 147, 166)
OUT = Path(__file__).resolve().parent / "thumbnail_stop_overthinking.png"


def thumbnail():
    w, h = 1280, 720
    img = _background((w, h), BG, 0.62).copy()
    sk = Sketcher((w, h), INK, 6, 3.0, 11)

    # figure (thinking), lower-left
    hx, hy = w * 0.26, h * 0.80
    draw_figure(sk, (hx, hy), h * 0.40, get_pose("think"), color=INK)

    # tangled "overthinking" storm clustered just above the head
    rng = random.Random(3)
    cx, cy = w * 0.25, h * 0.33
    for _ in range(9):
        ox, oy = rng.uniform(-0.10, 0.11) * w, rng.uniform(-0.13, 0.12) * h
        r = rng.uniform(0.03, 0.065) * w
        col = MUTED if rng.random() < 0.55 else INK
        sk.circle((cx + ox, cy + oy), r, color=col, width=rng.uniform(4, 7), amp=4.5)
    sk.composite_onto(img)

    # a few question marks in the storm
    d = ImageDraw.Draw(img)
    for (qx, qy, s) in [(0.17, 0.20, 70), (0.33, 0.16, 56), (0.30, 0.40, 50)]:
        d.text((qx * w, qy * h), "?", font=_font(s), anchor="mm",
               fill=ACCENT + (255,), stroke_width=max(2, s // 12), stroke_fill=(0, 0, 0, 255))

    # headline (right): STOP / OVERTHINKING + subtitle
    x0 = w * 0.45
    max_w = w * 0.975 - x0

    def fit(text, start):
        s = start
        while s > 40 and _font(s).getlength(text) > max_w:
            s -= 3
        return s

    s_stop = 168
    d.text((x0, h * 0.30), "STOP", font=_font(s_stop), anchor="lm",
           fill=WHITE + (255,), stroke_width=16, stroke_fill=(0, 0, 0, 255))
    s_over = fit("OVERTHINKING", 150)
    d.text((x0, h * 0.30 + s_stop * 0.62), "OVERTHINKING", font=_font(s_over), anchor="lm",
           fill=ACCENT + (255,), stroke_width=14, stroke_fill=(0, 0, 0, 255))
    sub = "5 tricks that actually work"
    ss = 48
    while ss > 28 and _font(ss).getlength(sub) > max_w:
        ss -= 2
    d.text((x0 + 4, h * 0.80), sub, font=_font(ss), anchor="lm",
           fill=MUTED + (255,), stroke_width=5, stroke_fill=(0, 0, 0, 255))

    img.convert("RGB").save(OUT)
    print("wrote", OUT, "->", Image.open(OUT).size)


if __name__ == "__main__":
    thumbnail()
