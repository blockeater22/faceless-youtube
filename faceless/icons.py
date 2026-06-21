"""Flat, clean icon glyphs (no hand-drawn wobble) for kinetic-text scenes.

Unlike :mod:`figures` (boiling-line stick figures for the paper/doodle
style), these are smooth filled shapes meant to sit on a white background
next to colourful animated captions.
"""
from __future__ import annotations

import math

from PIL import ImageDraw

Color = tuple


def _star_points(cx: float, cy: float, r_outer: float, r_inner: float, n: int = 5, rot: float = -90):
    pts = []
    for i in range(n * 2):
        r = r_outer if i % 2 == 0 else r_inner
        a = math.radians(rot + i * 180 / n)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def check(d: ImageDraw.ImageDraw, cx: float, cy: float, r: float, color: Color) -> None:
    w = max(2, int(r * 0.22))
    pts = [(cx - r * 0.55, cy + r * 0.05), (cx - r * 0.12, cy + r * 0.45), (cx + r * 0.6, cy - r * 0.45)]
    d.line(pts, fill=color, width=w, joint="curve")
    for p in (pts[0], pts[-1]):
        d.ellipse([p[0] - w / 2, p[1] - w / 2, p[0] + w / 2, p[1] + w / 2], fill=color)


def star(d: ImageDraw.ImageDraw, cx: float, cy: float, r: float, color: Color) -> None:
    d.polygon(_star_points(cx, cy, r, r * 0.42), fill=color)


def heart(d: ImageDraw.ImageDraw, cx: float, cy: float, r: float, color: Color) -> None:
    lr = r * 0.5
    d.ellipse([cx - lr * 2, cy - lr * 1.1, cx, cy + lr * 0.9], fill=color)
    d.ellipse([cx, cy - lr * 1.1, cx + lr * 2, cy + lr * 0.9], fill=color)
    d.polygon([(cx - lr * 1.9, cy + lr * 0.25), (cx + lr * 1.9, cy + lr * 0.25), (cx, cy + lr * 2.3)], fill=color)


def lightbulb(d: ImageDraw.ImageDraw, cx: float, cy: float, r: float, color: Color) -> None:
    d.ellipse([cx - r * 0.62, cy - r * 0.9, cx + r * 0.62, cy + r * 0.34], fill=color)
    d.rectangle([cx - r * 0.26, cy + r * 0.18, cx + r * 0.26, cy + r * 0.5], fill=color)
    w = max(2, int(r * 0.1))
    for i in range(3):
        yy = cy + r * 0.58 + i * r * 0.16
        d.line([(cx - r * 0.3, yy), (cx + r * 0.3, yy)], fill=color, width=w)


def brain(d: ImageDraw.ImageDraw, cx: float, cy: float, r: float, color: Color) -> None:
    # cloud-lobed silhouette (overlapping bumps), not two "eye" ovals.
    lobes = [(-0.55, -0.4, 0.46), (0.55, -0.4, 0.46), (-0.82, 0.1, 0.4), (0.82, 0.1, 0.4),
             (-0.42, 0.52, 0.4), (0.42, 0.52, 0.4), (0, -0.6, 0.38), (0, 0.62, 0.34)]
    for bx, by, brr in lobes:
        rr = brr * r
        d.ellipse([cx + bx * r - rr, cy + by * r - rr, cx + bx * r + rr, cy + by * r + rr], fill=color)
    d.ellipse([cx - r * 0.8, cy - r * 0.58, cx + r * 0.8, cy + r * 0.6], fill=color)
    w = max(2, int(r * 0.09))
    bg = (255, 255, 255, color[3] if len(color) > 3 else 255)
    d.line([(cx, cy - r * 0.5), (cx, cy + r * 0.55)], fill=bg, width=w)
    for sx in (-1, 1):
        for dy in (-0.22, 0.18):
            x0 = cx + sx * r * 0.14
            x1 = cx + sx * r * 0.58
            y0, y1 = cy + r * dy - r * 0.14, cy + r * dy + r * 0.14
            a0, a1 = (200, 340) if sx > 0 else (20, 160)
            d.arc([min(x0, x1), y0, max(x0, x1), y1], a0, a1, fill=bg, width=w)


def arrow_up(d: ImageDraw.ImageDraw, cx: float, cy: float, r: float, color: Color) -> None:
    d.polygon([(cx - r * 0.5, cy - r * 0.05), (cx + r * 0.5, cy - r * 0.05), (cx, cy - r * 0.75)], fill=color)
    d.rectangle([cx - r * 0.18, cy - r * 0.1, cx + r * 0.18, cy + r * 0.75], fill=color)


def arrow_down(d: ImageDraw.ImageDraw, cx: float, cy: float, r: float, color: Color) -> None:
    d.polygon([(cx - r * 0.5, cy + r * 0.05), (cx + r * 0.5, cy + r * 0.05), (cx, cy + r * 0.75)], fill=color)
    d.rectangle([cx - r * 0.18, cy - r * 0.75, cx + r * 0.18, cy + r * 0.1], fill=color)


def chat(d: ImageDraw.ImageDraw, cx: float, cy: float, r: float, color: Color) -> None:
    d.rounded_rectangle([cx - r, cy - r * 0.7, cx + r, cy + r * 0.5], radius=r * 0.32, fill=color)
    d.polygon([(cx - r * 0.45, cy + r * 0.42), (cx - r * 0.05, cy + r * 0.42), (cx - r * 0.35, cy + r * 0.95)],
              fill=color)


def clock(d: ImageDraw.ImageDraw, cx: float, cy: float, r: float, color: Color) -> None:
    w = max(2, int(r * 0.12))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=w)
    d.line([(cx, cy), (cx, cy - r * 0.55)], fill=color, width=w)
    d.line([(cx, cy), (cx + r * 0.4, cy + r * 0.25)], fill=color, width=w)
    d.ellipse([cx - w * 0.6, cy - w * 0.6, cx + w * 0.6, cy + w * 0.6], fill=color)


def warning(d: ImageDraw.ImageDraw, cx: float, cy: float, r: float, color: Color) -> None:
    d.polygon([(cx, cy - r), (cx - r * 0.92, cy + r * 0.75), (cx + r * 0.92, cy + r * 0.75)], fill=color)
    bg = (255, 255, 255, color[3] if len(color) > 3 else 255)
    w = max(2, int(r * 0.13))
    d.line([(cx, cy - r * 0.35), (cx, cy + r * 0.18)], fill=bg, width=w)
    d.ellipse([cx - w * 0.55, cy + r * 0.42, cx + w * 0.55, cy + r * 0.42 + w * 1.1], fill=bg)


ICONS = {
    "check": check, "star": star, "heart": heart, "lightbulb": lightbulb,
    "brain": brain, "arrow_up": arrow_up, "arrow_down": arrow_down,
    "chat": chat, "clock": clock, "warning": warning,
}


def draw_icon(d: ImageDraw.ImageDraw, name: str, cx: float, cy: float, r: float, color: Color) -> None:
    fn = ICONS.get(name)
    if fn is not None:
        fn(d, cx, cy, r, color)
