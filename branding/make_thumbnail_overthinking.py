#!/usr/bin/env python3
"""Thumbnail for 'How to Stop Overthinking': a big, visibly stressed face
caught in a swirl of scribbles + question marks, plus a bold, high-contrast
headline. Run: python branding/make_thumbnail_overthinking.py
"""
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumbnail_kit import W, H, big_face, highlight_bar, prop_icon, radial_bg, stroke_text  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from faceless.render import _font  # noqa: E402

INK = (18, 14, 26)
WHITE = (255, 255, 255)
MUTED = (220, 210, 230)
HOT = (120, 70, 220)
COOL = (8, 9, 18)
ACCENT = (255, 64, 96)
OUT = Path(__file__).resolve().parent / "thumbnail_stop_overthinking.png"


def thumbnail():
    img = radial_bg(W, H, HOT, COOL, center=(0.28, 0.55))

    # big stressed/worried face, lower-left
    big_face(img, W * 0.26, H * 0.96, H * 0.58, pose="think", face="worried",
              color=INK, lw=15, wobble=4)

    # tangled "overthinking" storm clustered just above the head
    sk_rng = random.Random(3)
    d = ImageDraw.Draw(img)
    cx, cy = W * 0.27, H * 0.30
    for _ in range(10):
        ox, oy = sk_rng.uniform(-0.12, 0.13) * W, sk_rng.uniform(-0.14, 0.13) * H
        r = sk_rng.uniform(0.035, 0.075) * W
        col = WHITE if sk_rng.random() < 0.5 else ACCENT
        w = int(sk_rng.uniform(4, 7))
        d.ellipse([cx + ox - r, cy + oy - r, cx + ox + r, cy + oy + r], outline=col + (235,), width=w)

    for (qx, qy, s) in [(0.16, 0.18, 78), (0.35, 0.13, 60), (0.32, 0.40, 54)]:
        stroke_text(d, (qx * W, qy * H), "?", _font(s), ACCENT, stroke_width=max(3, s // 9), anchor="mm")

    # headline (right): STOP / OVERTHINKING with a highlight bar + subtitle
    x0 = W * 0.43
    max_w = W * 0.975 - x0

    s_stop = 150
    f_stop = _font(s_stop)
    pad = s_stop * 0.16
    y_stop = H * 0.255
    highlight_bar(d, x0 - pad, y_stop - pad * 0.6, x0 + f_stop.getlength("STOP") + pad,
                  y_stop + s_stop * 0.78, ACCENT, radius=20)
    stroke_text(d, (x0, y_stop), "STOP", f_stop, WHITE, stroke_width=14, anchor="la")

    s_over = 132
    f_over = _font(s_over)
    while f_over.getlength("OVERTHINKING") > max_w and s_over > 56:
        s_over -= 3
        f_over = _font(s_over)
    y_over = y_stop + s_stop * 0.98
    stroke_text(d, (x0, y_over), "OVERTHINKING", f_over, WHITE, stroke_width=14, anchor="la")

    sub = "5 tricks that actually work"
    ss = 46
    while ss > 28 and _font(ss).getlength(sub) > max_w:
        ss -= 2
    y_sub = y_over + s_over * 1.05
    stroke_text(d, (x0 + 4, y_sub), sub, _font(ss), MUTED, stroke_width=5, anchor="la")

    # relatable colourful prop, clear of the subtitle text
    prop_icon(img, "brain", x0 + 44, y_sub + ss * 1.7, 44, (167, 139, 250))

    img.convert("RGB").save(OUT)
    print("wrote", OUT, "->", Image.open(OUT).size)


if __name__ == "__main__":
    thumbnail()
