#!/usr/bin/env python3
"""Thumbnail for 'What If You Could Hear What People Really Think of You?':
a figure looking up while mixed thought-bubbles (love / question / judgment)
rise around its head + a bold headline.
Run: python branding/make_thumbnail_hear_thoughts.py
"""
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
OUT = Path(__file__).resolve().parent / "thumbnail_hear_thoughts.png"

# (cx, cy, radius, symbol, color)  -- as fractions of w/h
BUBBLES = [
    (0.135, 0.40, 0.060, "?", ACCENT),
    (0.255, 0.25, 0.052, "♥", ACCENT),   # heart
    (0.395, 0.38, 0.050, "?", INK),
    (0.330, 0.135, 0.040, "!", MUTED),
]


def thumbnail():
    w, h = 1280, 720
    img = _background((w, h), BG, 0.62).copy()
    sk = Sketcher((w, h), INK, 6, 3.0, 11)

    # figure (looking up), lower-left
    hx, hy = w * 0.24, h * 0.86
    draw_figure(sk, (hx, hy), h * 0.46, get_pose("look_up"), color=INK)

    # a thought-bubble "tail" rising from near the head toward the bubbles
    for (tx, ty, tr) in [(0.205, 0.50, 0.012), (0.225, 0.42, 0.016)]:
        sk.circle((tx * w, ty * h), tr * w, color=MUTED, width=4, amp=3.5)

    # the floating bubbles (hand-drawn rings)
    for (cx, cy, r, _sym, col) in BUBBLES:
        sk.circle((cx * w, cy * h), r * w, color=col, width=6, amp=4.5)
    sk.composite_onto(img)

    # symbols inside each bubble
    d = ImageDraw.Draw(img)
    for (cx, cy, r, sym, col) in BUBBLES:
        fs = int(r * w * 1.15)
        d.text((cx * w, cy * h - r * h * 0.04), sym, font=_font(fs), anchor="mm",
               fill=col + (255,), stroke_width=max(2, fs // 12), stroke_fill=(0, 0, 0, 255))

    # headline (right): WHAT THEY / REALLY THINK + subtitle
    x0 = w * 0.46
    max_w = w * 0.975 - x0

    def fit(text, start):
        s = start
        while s > 40 and _font(s).getlength(text) > max_w:
            s -= 3
        return s

    s_what = fit("WHAT THEY", 132)
    d.text((x0, h * 0.30), "WHAT THEY", font=_font(s_what), anchor="lm",
           fill=WHITE + (255,), stroke_width=14, stroke_fill=(0, 0, 0, 255))
    s_think = fit("REALLY THINK", 150)
    d.text((x0, h * 0.30 + s_what * 0.78), "REALLY THINK", font=_font(s_think), anchor="lm",
           fill=ACCENT + (255,), stroke_width=14, stroke_fill=(0, 0, 0, 255))
    sub = "the truth might surprise you"
    ss = 50
    while ss > 28 and _font(ss).getlength(sub) > max_w:
        ss -= 2
    d.text((x0 + 4, h * 0.78), sub, font=_font(ss), anchor="lm",
           fill=MUTED + (255,), stroke_width=5, stroke_fill=(0, 0, 0, 255))

    img.convert("RGB").save(OUT)
    print("wrote", OUT, "->", Image.open(OUT).size)


if __name__ == "__main__":
    thumbnail()
