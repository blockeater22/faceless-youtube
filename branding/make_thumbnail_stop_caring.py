#!/usr/bin/env python3
"""High-CTR thumbnail for 'How to Stop Caring What People Think': one big,
well-lit stickman face (~30% of frame) with a red circle drawing the eye, and a
bold headline. Run: python branding/make_thumbnail_stop_caring.py
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
OUT = Path(__file__).resolve().parent / "thumbnail_stop_caring.png"


def thumbnail():
    w, h = 1280, 720
    img = _background((w, h), BG, 0.5).copy()

    # big figure on the left; hip pushed off the bottom so head + torso fill frame
    unit = h * 1.12
    hx, hy = w * 0.30, h * 1.05
    head_cx, head_cy = hx, hy - 0.50 * unit
    head_r = 0.13 * unit

    # soft halo behind the head -> "well-lit" subject
    halo = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    hd = ImageDraw.Draw(halo)
    hd.ellipse([head_cx - head_r * 2.1, head_cy - head_r * 2.1,
                head_cx + head_r * 2.1, head_cy + head_r * 2.1], fill=(255, 210, 140, 90))
    img.alpha_composite(halo.filter(ImageFilter.GaussianBlur(46)))

    sk = Sketcher((w, h), INK, 10, 2.4, 7)
    draw_figure(sk, (hx, hy), unit, get_pose("stand"), color=INK, face="happy")
    sk.composite_onto(img)

    d = ImageDraw.Draw(img)

    # faint, ignored "opinions" drifting near the head (muted, low-contrast)
    for (qx, qy, s) in [(0.055, 0.26, 46), (0.49, 0.30, 40), (0.085, 0.62, 40)]:
        d.text((qx * w, qy * h), "?", font=_font(s), anchor="mm",
               fill=MUTED + (150,), stroke_width=3, stroke_fill=(0, 0, 0, 150))

    # red circle on the calm face = the one opinion that counts (yours)
    rx = head_r * 1.28
    d.ellipse([head_cx - rx - 3, head_cy - rx - 3, head_cx + rx + 3, head_cy + rx + 3],
              outline=(0, 0, 0, 255), width=16)
    d.ellipse([head_cx - rx, head_cy - rx, head_cx + rx, head_cy + rx],
              outline=RED + (255,), width=10)

    # headline (right): STOP / CARING + subtitle
    x0 = w * 0.50
    max_w = w * 0.97 - x0

    def fit(text, start):
        s = start
        while s > 40 and _font(s).getlength(text) > max_w:
            s -= 3
        return s

    def text(x, y, s, size, fill, anchor="lm", stroke=12):
        d.text((x, y), s, font=_font(size), anchor=anchor, fill=fill + (255,),
               stroke_width=stroke, stroke_fill=(0, 0, 0, 255))

    s_stop = fit("STOP", 176)
    text(x0, h * 0.30, "STOP", s_stop, WHITE, stroke=15)
    s_caring = fit("CARING", 176)
    text(x0, h * 0.30 + s_stop * 0.74, "CARING", s_caring, ACCENT, stroke=15)
    sub = "what people think"
    ss = fit(sub, 60)
    text(x0 + 4, h * 0.74, sub, ss, WHITE, stroke=7)

    img.convert("RGB").save(OUT)
    print("wrote", OUT, "->", Image.open(OUT).size)


if __name__ == "__main__":
    thumbnail()
