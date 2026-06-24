#!/usr/bin/env python3
"""Generate a 1280x720 YouTube thumbnail with the faceless engine.

High-CTR layout: a big shocked face (the strongest single CTR lever), a bold
circular hero-number badge, a vivid radial-gradient background instead of a
flat panel, and a short, high-contrast headline with a highlight bar behind
the punchiest word.

Edit the constants and re-run:  python branding/make_thumbnail.py
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumbnail_kit import (W, H, badge, big_face, fit_size, highlight_bar,  # noqa: E402
                            prop_icon, radial_bg, stroke_text)

INK = (18, 14, 26)
WHITE = (255, 255, 255)
HOT = (255, 110, 40)
COOL = (10, 11, 22)
BADGE_BG = (230, 32, 56)

BIG_NUMBER = "7"
LINES = [                       # (text, colour, highlight_or_None) per line
    [("THOUGHTS", WHITE, None)],
    [("THAT CHANGE", WHITE, None)],
    [("EVERYTHING", WHITE, BADGE_BG)],
]
OUT = Path(__file__).resolve().parent / "thumbnail_seven_thoughts.png"


def thumbnail():
    img = radial_bg(W, H, HOT, COOL, center=(0.27, 0.58))

    # big shocked face, lower-left - the single highest-leverage CTR element
    big_face(img, W * 0.25, H * 0.92, H * 0.56, pose="arms_up", face="surprised",
              color=INK, lw=15, wobble=4)

    # bold hero-number badge, upper-left
    badge(img, W * 0.135, H * 0.165, 78, BADGE_BG, BIG_NUMBER, ring=WHITE)

    d = ImageDraw.Draw(img)
    # stacked, auto-fit headline (right side), with a highlight bar behind the
    # punchiest word so the eye lands there first
    from faceless.render import _font  # noqa: E402
    x0 = W * 0.40
    max_w = W * 0.965 - x0
    size = 128
    while size > 56:
        f = _font(size)
        widest = max(sum(f.getlength(t) for t, _, _ in segs) for segs in LINES)
        if widest <= max_w:
            break
        size -= 3
    f = _font(size)
    lh = int(size * 1.18)
    stroke = max(8, size // 9)
    y = H * 0.5 - lh * len(LINES) / 2

    for segs in LINES:
        x = x0
        for text, color, hl in segs:
            tw = f.getlength(text)
            if hl:
                pad = size * 0.14
                highlight_bar(d, x - pad, y - pad * 0.5, x + tw + pad, y + lh - pad * 0.9, hl, radius=18)
            stroke_text(d, (x, y), text, f, color, stroke_width=stroke, anchor="la")
            x += tw
        y += lh

    # relatable colourful prop, tucked beside the headline
    prop_icon(img, "lightbulb", W * 0.40, H * 0.86, 56, (255, 212, 63))

    img.convert("RGB").save(OUT)
    print("wrote", OUT, "->", Image.open(OUT).size)


if __name__ == "__main__":
    thumbnail()
