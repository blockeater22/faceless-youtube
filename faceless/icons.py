"""Hand-drawn object icons, so the visuals can *illustrate* the narration
(a phone, a door, a heart, rain) instead of a figure standing in a void.

Each icon is a list of primitive elements in a unit square (-1..1, y-down),
drawn through the same wobbly Sketcher as the figures so the style matches.
Render with :func:`draw_icon`; unknown names fall back to a soft circle.
"""
from __future__ import annotations

import math

from .draw import Sketcher

# element forms:  ("poly", [(x,y), ...])  |  ("circle", x, y, r)  |  ("arc", x, y, r, a0, a1)


def _star_pts(n=5, r1=0.95, r2=0.42):
    pts = []
    for i in range(n * 2 + 1):
        ang = -math.pi / 2 + i * math.pi / n
        r = r1 if i % 2 == 0 else r2
        pts.append((r * math.cos(ang), r * math.sin(ang)))
    return pts


def _spiral_pts(turns=2.6, n=70, r=0.95):
    return [((r * (1 - i / n)) * math.cos(i / n * turns * math.tau),
             (r * (1 - i / n)) * math.sin(i / n * turns * math.tau)) for i in range(n + 1)]


def _ray_polys(r0=0.5, r1=0.95, n=8):
    out = []
    for i in range(n):
        a = i / n * math.tau
        out.append(("poly", [(r0 * math.cos(a), r0 * math.sin(a)),
                             (r1 * math.cos(a), r1 * math.sin(a))]))
    return out


ICONS: dict[str, list] = {
    "heart": [("poly", [(0, 0.75), (-0.55, 0.0), (-0.7, -0.35), (-0.45, -0.6),
                        (-0.15, -0.45), (0, -0.2), (0.15, -0.45), (0.45, -0.6),
                        (0.7, -0.35), (0.55, 0.0), (0, 0.75)])],
    "speech": [("poly", [(-0.8, -0.6), (0.8, -0.6), (0.8, 0.35), (-0.2, 0.35),
                         (-0.4, 0.75), (-0.45, 0.35), (-0.8, 0.35), (-0.8, -0.6)])],
    "thought": [("circle", -0.35, -0.1, 0.36), ("circle", 0.3, -0.18, 0.34),
                ("circle", 0.05, 0.2, 0.36), ("circle", -0.5, 0.6, 0.12),
                ("circle", -0.68, 0.85, 0.07)],
    "cloud": [("circle", -0.4, 0.05, 0.34), ("circle", 0.05, -0.15, 0.42),
              ("circle", 0.5, 0.08, 0.3), ("poly", [(-0.7, 0.34), (0.78, 0.34)])],
    "rain": [("circle", -0.4, -0.2, 0.3), ("circle", 0.05, -0.4, 0.38),
             ("circle", 0.5, -0.18, 0.28), ("poly", [(-0.72, 0.08), (0.78, 0.08)]),
             ("poly", [(-0.35, 0.25), (-0.5, 0.7)]), ("poly", [(0.05, 0.25), (-0.1, 0.7)]),
             ("poly", [(0.45, 0.25), (0.3, 0.7)])],
    "door": [("poly", [(-0.5, -0.85), (0.5, -0.85), (0.5, 0.85), (-0.5, 0.85), (-0.5, -0.85)]),
             ("circle", 0.32, 0.05, 0.07)],
    "phone": [("poly", [(-0.42, -0.8), (0.42, -0.8), (0.42, 0.8), (-0.42, 0.8), (-0.42, -0.8)]),
              ("poly", [(-0.16, -0.62), (0.16, -0.62)]), ("circle", 0, 0.6, 0.06)],
    "sun": [("circle", 0, 0, 0.42)] + _ray_polys(),
    "moon": [("arc", 0.15, 0, 0.85, 60, 300), ("arc", -0.2, 0, 0.7, 65, 295)],
    "star": [("poly", _star_pts())],
    "clock": [("circle", 0, 0, 0.85), ("poly", [(0, 0), (0, -0.5)]), ("poly", [(0, 0), (0.34, 0.12)])],
    "gift": [("poly", [(-0.6, -0.35), (0.6, -0.35), (0.6, 0.7), (-0.6, 0.7), (-0.6, -0.35)]),
             ("poly", [(0, -0.35), (0, 0.7)]), ("circle", -0.18, -0.5, 0.16),
             ("circle", 0.18, -0.5, 0.16)],
    "spiral": [("poly", _spiral_pts())],
    "bulb": [("circle", 0, -0.2, 0.5), ("poly", [(-0.22, 0.28), (0.22, 0.28)]),
             ("poly", [(-0.18, 0.45), (0.18, 0.45)]), ("poly", [(-0.12, 0.62), (0.12, 0.62)])],
    "eye": [("poly", [(-0.8, 0), (0, -0.42), (0.8, 0), (0, 0.42), (-0.8, 0)]),
            ("circle", 0, 0, 0.2)],
}


def draw_icon(sk: Sketcher, name: str, center, size: float, color=None,
              width: float | None = None, draw: float = 1.0) -> None:
    cx, cy = center
    elems = ICONS.get(name)
    if not elems:
        sk.circle(center, size * 0.5, color=color, width=width, draw=draw)
        return
    for e in elems:
        if e[0] == "poly":
            sk.stroke([(cx + x * size, cy + y * size) for x, y in e[1]],
                      color=color, width=width, draw=draw)
        elif e[0] == "circle":
            _, x, y, r = e
            sk.circle((cx + x * size, cy + y * size), r * size, color=color, width=width, draw=draw)
        elif e[0] == "arc":
            _, x, y, r, a0, a1 = e
            sk.arc((cx + x * size, cy + y * size), r * size, a0, a1, color=color, width=width)
