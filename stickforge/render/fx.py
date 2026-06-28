"""Motion & emotion effects — the comic vocabulary from the style guide.

Each effect is a small registered drawer ``fn(cv, center, size, color)`` so the
set grows without engine changes. Used via scene props of ``type: "fx"``.
"""
from __future__ import annotations

import math

from ..core.geometry import Vec2
from ..core.registry import Registry
from .canvas import SvgCanvas

FX: "Registry" = Registry("fx")


def draw_fx(cv: SvgCanvas, name: str, center: Vec2, size: float, color: str) -> None:
    if name in FX:
        FX.get(name)(cv, center, size, color)


def _star(cv, c: Vec2, r: float, color: str, points: int = 4):
    d = ""
    for i in range(points * 2):
        ang = math.pi * i / points
        rad = r if i % 2 == 0 else r * 0.42
        x = c.x + rad * math.sin(ang)
        y = c.y - rad * math.cos(ang)
        d += ("M " if i == 0 else "L ") + f"{x:.1f} {y:.1f} "
    cv.filled_path(d + "Z", color)


@FX.register("speed_lines")
def speed_lines(cv, c, size, color):
    for i in range(4):
        y = c.y - size * 0.4 + i * size * 0.27
        cv.stroke([Vec2(c.x - size * 1.3, y), Vec2(c.x + size * (0.2 - i * 0.1), y)],
                  color, size * 0.08)


@FX.register("impact")
@FX.register("action_burst")
def impact(cv, c, size, color):
    n = 10
    d = ""
    for i in range(n * 2):
        ang = math.pi * i / n
        rad = size if i % 2 == 0 else size * 0.5
        x = c.x + rad * math.sin(ang)
        y = c.y - rad * math.cos(ang)
        d += ("M " if i == 0 else "L ") + f"{x:.1f} {y:.1f} "
    cv.filled_path(d + "Z", color)


@FX.register("vibration")
def vibration(cv, c, size, color):
    for s in (-1, 1):
        cv.stroke([Vec2(c.x + s * size, c.y - size * 0.5),
                   Vec2(c.x + s * size, c.y + size * 0.5)], color, size * 0.08)


@FX.register("sweat")
def sweat(cv, c, size, color="#7ec8ff"):
    tip = Vec2(c.x, c.y - size)
    d = (f"M {tip.x:.1f} {tip.y:.1f} "
         f"Q {c.x + size*0.5:.1f} {c.y - size*0.1:.1f} {c.x:.1f} {c.y + size*0.4:.1f} "
         f"Q {c.x - size*0.5:.1f} {c.y - size*0.1:.1f} {tip.x:.1f} {tip.y:.1f} Z")
    cv.filled_path(d, "#7ec8ff", "#3a86c8", size * 0.06)


@FX.register("question")
def question(cv, c, size, color):
    cv.text(c.x, c.y + size * 0.5, "?", size * 1.6, color)


@FX.register("surprise")
def surprise(cv, c, size, color):
    cv.text(c.x, c.y + size * 0.5, "!", size * 1.6, color)


@FX.register("lightbulb")
def lightbulb(cv, c, size, color="#ffd34d"):
    cv.circle(Vec2(c.x, c.y - size * 0.2), size * 0.6, "#caa12b", size * 0.06,
              fill="#ffd34d")
    cv.rect(c.x - size * 0.22, c.y + size * 0.35, size * 0.44, size * 0.28, "#9a9a9a")
    for i in range(6):
        a = math.radians(i * 60)
        p0 = Vec2(c.x + math.cos(a) * size * 0.8, c.y - size * 0.2 + math.sin(a) * size * 0.8)
        p1 = Vec2(c.x + math.cos(a) * size * 1.15, c.y - size * 0.2 + math.sin(a) * size * 1.15)
        cv.stroke([p0, p1], "#ffd34d", size * 0.07)


@FX.register("stars")
def stars(cv, c, size, color="#ffd34d"):
    for dx, dy, s in ((-0.8, -0.3, 0.5), (0.0, -0.8, 0.7), (0.8, -0.2, 0.45)):
        _star(cv, Vec2(c.x + dx * size, c.y + dy * size), size * s, "#ffd34d", 5)


@FX.register("hearts")
def hearts(cv, c, size, color="#ff5a7a"):
    for dx, dy, s in ((-0.7, 0.0, 0.6), (0.2, -0.6, 0.8)):
        cx, cy, r = c.x + dx * size, c.y + dy * size, size * s
        d = (f"M {cx:.1f} {cy + r*0.3:.1f} "
             f"C {cx - r:.1f} {cy - r*0.5:.1f} {cx - r*0.3:.1f} {cy - r:.1f} {cx:.1f} {cy - r*0.3:.1f} "
             f"C {cx + r*0.3:.1f} {cy - r:.1f} {cx + r:.1f} {cy - r*0.5:.1f} {cx:.1f} {cy + r*0.3:.1f} Z")
        cv.filled_path(d, "#ff5a7a")


@FX.register("anger")
def anger(cv, c, size, color="#e8492b"):
    r = size * 0.7
    for a in (0, 90, 180, 270):
        rad = math.radians(a)
        cx, cy = c.x + math.cos(rad) * r, c.y + math.sin(rad) * r
        d = (f"M {cx - size*0.18:.1f} {cy:.1f} L {cx:.1f} {cy - size*0.28:.1f} "
             f"L {cx + size*0.18:.1f} {cy:.1f} L {cx:.1f} {cy + size*0.10:.1f} Z")
        cv.filled_path(d, "#e8492b")
