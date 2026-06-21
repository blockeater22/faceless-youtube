"""Flat, multi-colour "scene" props - everyday objects (armchair, mug, books,
a door, ...) that ground kinetic-text scenes in a relatable setting, the way
illustrated explainer channels surround their character with a couch, a
laptop, a doorway, etc. Each object draws several flat shapes in a sensible
default palette; pass ``tint`` to recolour the primary shape.
"""
from __future__ import annotations

import math

from PIL import ImageDraw

Color = tuple


def _shade(c: Color, f: float) -> Color:
    r, g, b = c[:3]
    if f >= 1:
        r, g, b = (r + (255 - r) * (f - 1), g + (255 - g) * (f - 1), b + (255 - b) * (f - 1))
    else:
        r, g, b = r * f, g * f, b * f
    return tuple(max(0, min(255, int(v))) for v in (r, g, b))


def armchair(d: ImageDraw.ImageDraw, cx: float, cy: float, s: float, tint: Color | None = None) -> None:
    base = tint or (235, 126, 53)
    dark = _shade(base, 0.75)
    d.rounded_rectangle([cx - 0.46 * s, cy - 0.95 * s, cx + 0.46 * s, cy - 0.05 * s], radius=0.14 * s, fill=base)
    d.rounded_rectangle([cx - 0.5 * s, cy - 0.22 * s, cx + 0.5 * s, cy + 0.18 * s], radius=0.12 * s, fill=base)
    d.rounded_rectangle([cx - 0.62 * s, cy - 0.55 * s, cx - 0.38 * s, cy + 0.12 * s], radius=0.1 * s, fill=dark)
    d.rounded_rectangle([cx + 0.38 * s, cy - 0.55 * s, cx + 0.62 * s, cy + 0.12 * s], radius=0.1 * s, fill=dark)
    for sx in (-1, 1):
        d.rectangle([cx + sx * 0.42 * s - 0.03 * s, cy + 0.16 * s, cx + sx * 0.42 * s + 0.03 * s, cy + 0.26 * s],
                    fill=dark)


def mug(d: ImageDraw.ImageDraw, cx: float, cy: float, s: float, tint: Color | None = None) -> None:
    base = tint or (250, 250, 250)
    d.rounded_rectangle([cx - 0.32 * s, cy - 0.32 * s, cx + 0.32 * s, cy + 0.36 * s], radius=0.08 * s, fill=base)
    w = max(2, int(0.08 * s))
    d.arc([cx + 0.18 * s, cy - 0.12 * s, cx + 0.62 * s, cy + 0.22 * s], -90, 90, fill=base, width=w)
    steam = (180, 180, 180, 160)
    for dx in (-0.12, 0.0, 0.12):
        x = cx + dx * s
        d.line([(x, cy - 0.4 * s), (x - 0.05 * s, cy - 0.58 * s), (x + 0.05 * s, cy - 0.76 * s),
                (x, cy - 0.95 * s)], fill=steam, width=max(2, int(0.025 * s)), joint="curve")


def clock(d: ImageDraw.ImageDraw, cx: float, cy: float, s: float, tint: Color | None = None) -> None:
    rim = tint or (230, 178, 46)
    face = (255, 255, 255)
    d.ellipse([cx - 0.5 * s, cy - 0.5 * s, cx + 0.5 * s, cy + 0.5 * s], fill=rim)
    d.ellipse([cx - 0.4 * s, cy - 0.4 * s, cx + 0.4 * s, cy + 0.4 * s], fill=face)
    w = max(2, int(0.05 * s))
    for ang in range(0, 360, 90):
        a = math.radians(ang)
        x0, y0 = cx + 0.3 * s * math.sin(a), cy - 0.3 * s * math.cos(a)
        x1, y1 = cx + 0.36 * s * math.sin(a), cy - 0.36 * s * math.cos(a)
        d.line([(x0, y0), (x1, y1)], fill=rim, width=w)
    ink = (40, 40, 40)
    d.line([(cx, cy), (cx, cy - 0.22 * s)], fill=ink, width=w)
    d.line([(cx, cy), (cx + 0.16 * s, cy + 0.08 * s)], fill=ink, width=w)
    d.ellipse([cx - w * 0.6, cy - w * 0.6, cx + w * 0.6, cy + w * 0.6], fill=ink)


def blanket(d: ImageDraw.ImageDraw, cx: float, cy: float, s: float, tint: Color | None = None) -> None:
    base = tint or (90, 170, 170)
    dark = _shade(base, 0.85)
    left, right = cx - 0.55 * s, cx + 0.55 * s
    top, body_bottom = cy - 0.35 * s, cy + 0.25 * s
    d.rounded_rectangle([left, top, right, body_bottom], radius=0.08 * s, fill=base)
    n, fringe_h = 6, 0.12 * s
    for i in range(n):
        x0 = left + (right - left) * i / n
        x1 = left + (right - left) * (i + 1) / n
        if i % 2 == 0:
            d.polygon([(x0, body_bottom), (x1, body_bottom), ((x0 + x1) / 2, body_bottom + fringe_h)], fill=base)
    for i in range(1, 4):
        x = left + (right - left) * i / 4
        d.line([(x, top + 0.06 * s), (x, body_bottom - 0.04 * s)], fill=dark, width=max(2, int(0.018 * s)))


def books(d: ImageDraw.ImageDraw, cx: float, cy: float, s: float, tint: Color | None = None) -> None:
    palette = [tint, (60, 120, 200), (220, 90, 90)] if tint else [(70, 150, 110), (60, 120, 200), (220, 90, 90)]
    widths = [0.95, 0.78, 0.6]
    h = 0.15 * s
    y = cy + 0.28 * s
    for wf, col in zip(widths, palette):
        top = y - h
        d.rounded_rectangle([cx - wf * 0.5 * s, top, cx + wf * 0.5 * s, y], radius=0.025 * s, fill=col)
        y = top - 0.02 * s


def laptop(d: ImageDraw.ImageDraw, cx: float, cy: float, s: float, tint: Color | None = None) -> None:
    base = tint or (90, 90, 100)
    screen = (130, 190, 230)
    d.polygon([(cx - 0.55 * s, cy + 0.3 * s), (cx + 0.55 * s, cy + 0.3 * s),
               (cx + 0.42 * s, cy + 0.42 * s), (cx - 0.42 * s, cy + 0.42 * s)], fill=base)
    d.rounded_rectangle([cx - 0.48 * s, cy - 0.45 * s, cx + 0.48 * s, cy + 0.3 * s], radius=0.04 * s,
                         fill=_shade(base, 0.85))
    d.rounded_rectangle([cx - 0.4 * s, cy - 0.38 * s, cx + 0.4 * s, cy + 0.22 * s], radius=0.02 * s, fill=screen)


def table(d: ImageDraw.ImageDraw, cx: float, cy: float, s: float, tint: Color | None = None) -> None:
    base = tint or (160, 110, 70)
    dark = _shade(base, 0.8)
    d.rounded_rectangle([cx - 0.6 * s, cy - 0.08 * s, cx + 0.6 * s, cy + 0.08 * s], radius=0.04 * s, fill=base)
    for sx in (-1, 1):
        d.rectangle([cx + sx * 0.5 * s - 0.04 * s, cy + 0.08 * s, cx + sx * 0.5 * s + 0.04 * s, cy + 0.5 * s],
                    fill=dark)


def door(d: ImageDraw.ImageDraw, cx: float, cy: float, s: float, tint: Color | None = None) -> None:
    base = tint or (60, 170, 160)
    glow = (255, 230, 140)
    gold = (220, 180, 60)
    d.rectangle([cx - 0.05 * s, cy - 0.9 * s, cx + 0.55 * s, cy + 0.9 * s], fill=glow)
    d.rounded_rectangle([cx - 0.5 * s, cy - 0.9 * s, cx + 0.15 * s, cy + 0.9 * s], radius=0.05 * s, fill=base)
    r = 0.05 * s
    d.ellipse([cx - 0.02 * s - r, cy - r, cx - 0.02 * s + r, cy + r], fill=gold)
    d.ellipse([cx + 0.08 * s - r * 0.7, cy - r * 0.7, cx + 0.08 * s + r * 0.7, cy + r * 0.7], fill=gold)


OBJECTS = {
    "armchair": armchair, "mug": mug, "clock": clock, "blanket": blanket,
    "books": books, "laptop": laptop, "table": table, "door": door,
}


def draw_object(d: ImageDraw.ImageDraw, name: str, cx: float, cy: float, s: float, tint: Color | None = None) -> None:
    fn = OBJECTS.get(name)
    if fn is not None:
        fn(d, cx, cy, s, tint)
