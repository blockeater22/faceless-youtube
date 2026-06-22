#!/usr/bin/env python3
"""High-CTR split-screen thumbnail for 'What If You Met the Person You Could
Have Been?': dim 'you now' (left) vs bright 'the other you' (right), with a red
arrow + red circle drawing the eye to the aspirational version.
Run: python branding/make_thumbnail_other_you.py
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from faceless.draw import Sketcher                 # noqa: E402
from faceless.figures import draw_figure, get_pose  # noqa: E402
from faceless.render import _background, _font      # noqa: E402

BG = (14, 19, 32)
INK = (242, 237, 225)
ACCENT = (255, 180, 84)
WHITE = (255, 255, 255)
MUTED = (110, 119, 145)
RED = (240, 46, 46)
OUT = Path(__file__).resolve().parent / "thumbnail_other_you.png"


def arrow(d, p1, p2, color, width, head=34):
    import math
    d.line([p1, p2], fill=color + (255,), width=width)
    ang = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
    for da in (math.radians(150), math.radians(-150)):
        x = p2[0] + head * math.cos(ang + da)
        y = p2[1] + head * math.sin(ang + da)
        d.line([p2, (x, y)], fill=color + (255,), width=width)


def thumbnail():
    w, h = 1280, 720
    img = _background((w, h), BG, 0.5).copy()

    # --- split panels: dim left, lifted (well-lit) right ---
    panels = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    pd = ImageDraw.Draw(panels)
    pd.rectangle([0, 0, w // 2, h], fill=(0, 0, 0, 95))            # dim the past-you
    pd.rectangle([w // 2, 0, w, h], fill=(255, 210, 150, 26))      # warm light on other-you
    img.alpha_composite(panels)

    # soft halo behind the right (aspirational) figure -> "well-lit"
    halo = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    hd = ImageDraw.Draw(halo)
    hd.ellipse([int(0.60 * w), int(0.20 * h), int(0.86 * w), int(0.78 * h)],
               fill=(255, 200, 120, 70))
    img.alpha_composite(halo.filter(ImageFilter.GaussianBlur(40)))

    # divider
    dd = ImageDraw.Draw(img)
    dd.line([(w // 2, 0), (w // 2, h)], fill=MUTED + (160,), width=4)

    # --- figures (big) ---
    sk = Sketcher((w, h), INK, 8, 2.6, 11)
    draw_figure(sk, (w * 0.265, h * 0.86), h * 0.66, get_pose("think"), color=MUTED, face="sad")
    draw_figure(sk, (w * 0.735, h * 0.86), h * 0.66, get_pose("celebrate"), color=INK, face="happy")
    sk.composite_onto(img)

    d = ImageDraw.Draw(img)

    # red circle around the aspirational version + red arrow pointing to it
    cx, cy, rx, ry = int(w * 0.735), int(h * 0.50), int(w * 0.15), int(h * 0.34)
    d.ellipse([cx - rx - 3, cy - ry - 3, cx + rx + 3, cy + ry + 3], outline=(0, 0, 0, 255), width=16)
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], outline=RED + (255,), width=10)
    arrow(d, (w * 0.40, h * 0.30), (w * 0.55, h * 0.40), RED, 12)

    # headline (top center): THE OTHER YOU
    def text(x, y, s, size, fill, anchor="lm", stroke=12):
        d.text((x, y), s, font=_font(size), anchor=anchor, fill=fill + (255,),
               stroke_width=stroke, stroke_fill=(0, 0, 0, 255))

    text(w * 0.5, h * 0.11, "THE OTHER YOU", 96, WHITE, anchor="mm", stroke=13)

    # labels under each figure
    text(w * 0.265, h * 0.84, "YOU NOW", 44, MUTED, anchor="mm", stroke=6)
    text(w * 0.735, h * 0.84, "YOU?", 72, ACCENT, anchor="mm", stroke=9)

    img.convert("RGB").save(OUT)
    print("wrote", OUT, "->", Image.open(OUT).size)


if __name__ == "__main__":
    thumbnail()
