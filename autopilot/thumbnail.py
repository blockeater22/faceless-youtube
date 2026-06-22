"""Auto-generate a high-CTR thumbnail for any video.

Four layouts keyed by `kind`:
  bigface  — one big well-lit face + red circle (how-to)
  split    — two figures, dim vs bright + red arrow/circle (comparison)
  bubbles  — figure + thought-bubbles + red ring (what-if)
  stars    — figure gazing up at stars + red circle (reflection)
Headline text is the (short) hook, wrapped, last line in accent.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from faceless.draw import Sketcher                  # noqa: E402
from faceless.figures import draw_figure, get_pose   # noqa: E402
from faceless.render import _background, _font       # noqa: E402

BG = (14, 19, 32)
INK = (242, 237, 225)
ACCENT = (255, 180, 84)
WHITE = (255, 255, 255)
MUTED = (110, 119, 145)
RED = (240, 46, 46)


def _wrap(text, size, max_w):
    words, lines, cur = text.split(), [], []
    for w in words:
        if _font(size).getlength(" ".join(cur + [w])) > max_w and cur:
            lines.append(" ".join(cur)); cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(" ".join(cur))
    return lines


def _headline(d, hook, x0, y0, max_w, big=104):
    """Wrapped uppercase headline; last line in accent."""
    size = big
    while size > 54 and (len(_wrap(hook.upper(), size, max_w)) > 3
                         or max(_font(size).getlength(l) for l in _wrap(hook.upper(), size, max_w)) > max_w):
        size -= 4
    lines = _wrap(hook.upper(), size, max_w)
    lh = int(size * 1.06)
    y = y0
    for i, line in enumerate(lines):
        fill = ACCENT if i == len(lines) - 1 else WHITE
        d.text((x0, y), line, font=_font(size), anchor="lm", fill=fill + (255,),
               stroke_width=max(8, size // 11), stroke_fill=(0, 0, 0, 255))
        y += lh
    return size


def _ring(d, cx, cy, rx, ry):
    d.ellipse([cx - rx - 3, cy - ry - 3, cx + rx + 3, cy + ry + 3], outline=(0, 0, 0, 255), width=16)
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], outline=RED + (255,), width=10)


def _arrow(d, p1, p2, width=12, head=34):
    import math
    d.line([p1, p2], fill=RED + (255,), width=width)
    ang = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
    for da in (math.radians(150), math.radians(-150)):
        d.line([p2, (p2[0] + head * math.cos(ang + da), p2[1] + head * math.sin(ang + da))],
               fill=RED + (255,), width=width)


def _glow(img, cx, cy, r):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 210, 140, 80))
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(44)))


def make_thumbnail(hook: str, kind: str, out_path: str | Path) -> Path:
    w, h = 1280, 720
    img = _background((w, h), BG, 0.5).copy()
    out_path = Path(out_path)

    if kind == "split":
        panels = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        pd = ImageDraw.Draw(panels)
        pd.rectangle([0, 0, w // 2, h], fill=(0, 0, 0, 95))
        pd.rectangle([w // 2, 0, w, h], fill=(255, 210, 150, 24))
        img.alpha_composite(panels)
        _glow(img, int(w * 0.74), int(h * 0.5), int(h * 0.3))
        ImageDraw.Draw(img).line([(w // 2, 0), (w // 2, h)], fill=MUTED + (160,), width=4)
        sk = Sketcher((w, h), INK, 8, 2.6, 11)
        draw_figure(sk, (w * 0.265, h * 0.86), h * 0.62, get_pose("think"), color=MUTED, face="sad")
        draw_figure(sk, (w * 0.735, h * 0.86), h * 0.64, get_pose("celebrate"), color=INK, face="happy")
        sk.composite_onto(img)
        d = ImageDraw.Draw(img)
        _ring(d, int(w * 0.735), int(h * 0.5), int(w * 0.15), int(h * 0.34))
        _arrow(d, (w * 0.40, h * 0.30), (w * 0.55, h * 0.40))
        _headline(d, hook, w * 0.04, h * 0.13, w * 0.92, big=92)

    elif kind == "bigface":
        unit = h * 1.12
        hx, hy = w * 0.30, h * 1.05
        cx, cy, hr = hx, hy - 0.50 * unit, 0.13 * unit
        _glow(img, cx, cy, hr * 2.1)
        sk = Sketcher((w, h), INK, 10, 2.4, 7)
        draw_figure(sk, (hx, hy), unit, get_pose("stand"), color=INK, face="happy")
        sk.composite_onto(img)
        d = ImageDraw.Draw(img)
        _ring(d, cx, cy, hr * 1.28, hr * 1.28)
        _headline(d, hook, w * 0.5, h * 0.34, w * 0.47, big=120)

    elif kind == "stars":
        unit = h * 0.74
        hx, hy = w * 0.30, h * 0.92
        cx, cy, hr = hx, hy - 0.50 * unit, 0.13 * unit   # head center + radius
        _glow(img, cx, cy, hr * 2.0)
        sk = Sketcher((w, h), INK, 8, 2.6, 7)
        d0 = ImageDraw.Draw(img)
        for (sx, sy, s) in [(0.60, 0.16, 40), (0.74, 0.24, 30), (0.86, 0.15, 34),
                            (0.66, 0.34, 26), (0.92, 0.31, 30)]:
            d0.text((sx * w, sy * h), "*", font=_font(s), anchor="mm", fill=ACCENT + (255,))
        draw_figure(sk, (hx, hy), unit, get_pose("look_up"), color=INK, face="neutral")
        sk.composite_onto(img)
        d = ImageDraw.Draw(img)
        _ring(d, int(cx), int(cy), int(hr * 1.32), int(hr * 1.32))
        _headline(d, hook, w * 0.46, h * 0.30, w * 0.5, big=104)

    else:  # bubbles (what-if default)
        sk = Sketcher((w, h), INK, 8, 2.6, 11)
        draw_figure(sk, (w * 0.26, h * 0.88), h * 0.6, get_pose("think"), color=INK, face="neutral")
        for (cx, cy, r, col) in [(0.14, 0.34, 0.058, ACCENT), (0.30, 0.20, 0.05, MUTED),
                                 (0.40, 0.34, 0.046, INK)]:
            sk.circle((cx * w, cy * h), r * w, color=col, width=6, amp=4.5)
        sk.composite_onto(img)
        d = ImageDraw.Draw(img)
        for (cx, cy, r, sym, col) in [(0.14, 0.34, 0.058, "?", ACCENT), (0.30, 0.20, 0.05, "?", MUTED)]:
            d.text((cx * w, cy * h), sym, font=_font(int(r * w * 1.1)), anchor="mm",
                   fill=col + (255,), stroke_width=3, stroke_fill=(0, 0, 0, 255))
        _ring(d, int(w * 0.26), int(h * 0.55), int(w * 0.11), int(h * 0.17))
        _headline(d, hook, w * 0.46, h * 0.30, w * 0.5, big=104)

    img.convert("RGB").save(out_path)
    return out_path
