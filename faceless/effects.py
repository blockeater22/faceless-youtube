"""Emotion + motion effect glyphs drawn around a figure.

These are the small symbols top stickman creators layer on top of a pose to
make it read as *alive* instead of static: twinkle sparkles on a happy beat, a
sweat bead when a character is stressed, the manga "vein-pop" mark on anger, a
shock burst on surprise, a thought "?" while thinking, and trailing speed lines
on a moving pose.

The whole point is that they're *auto-derived* from a figure's existing
``face`` (and ``pose``), so every story already in the repo gains matching
visual emotion without being re-authored - exactly the "every spoken sentence
has matching visual emotion" goal. An actor can override with ``"fx"``:
a list of glyph names to force, or ``"none"`` to suppress.
"""
from __future__ import annotations

import math

from .draw import Point, Sketcher

# Default glyphs each face emotion summons. Kept deliberately sparse - one or
# two marks reads as intentional; a cloud of them reads as clip-art.
_FACE_FX: dict[str, tuple[str, ...]] = {
    "happy": ("sparkle",),
    "celebrate": ("sparkle", "sparkle2"),
    "surprised": ("shock",),
    "angry": ("anger",),
    "sad": ("sweat",),
    "worried": ("sweat",),
    "think": ("question",),
    "skeptical": ("question",),
}

# Poses that imply travel/force get trailing speed lines.
_MOTION_POSES = {"walk_a", "walk_b", "reach", "celebrate", "wave", "point_r", "point_l"}

# Glyph accent colours that pop on a light background.
_SWEAT = (74, 164, 232)
_ANGER = (228, 74, 74)
_SPARK = (255, 196, 64)


def _twinkle(phase: float, k: float, off: float) -> float:
    """0.6..1.0 shimmer so sparkles/marks breathe over the scene."""
    return 0.6 + 0.4 * (0.5 + 0.5 * math.sin(phase * math.tau * k + off))


def _sparkle(sk: Sketcher, c: Point, r: float, color, lw, phase, off=0.0) -> None:
    """A 4-point star/twinkle: long vertical+horizontal spokes, short diagonals."""
    cx, cy = c
    s = _twinkle(phase, 1.5, off)
    r = r * s
    sk.line((cx - r, cy), (cx + r, cy), color=color, width=lw)
    sk.line((cx, cy - r), (cx, cy + r), color=color, width=lw)
    d = r * 0.42
    thin = max(1, int(lw * 0.55))
    sk.line((cx - d, cy - d), (cx + d, cy + d), color=color, width=thin)
    sk.line((cx - d, cy + d), (cx + d, cy - d), color=color, width=thin)


def _sweat(sk: Sketcher, c: Point, r: float, color, lw, phase) -> None:
    """A teardrop bead that slides down a touch over the scene."""
    cx, cy = c
    cy += r * 0.9 * phase  # drip
    sk.circle((cx, cy), r * 0.55, color=color, width=lw, fill=color, segments=14)
    # little pointed top
    sk.stroke([(cx, cy - r * 1.3), (cx - r * 0.42, cy - r * 0.2),
               (cx + r * 0.42, cy - r * 0.2)], color=color, width=lw)


def _anger(sk: Sketcher, c: Point, r: float, color, lw, phase) -> None:
    """Manga vein-pop mark: three bent spokes meeting at a corner, pulsing."""
    cx, cy = c
    s = _twinkle(phase, 2.2, 0.0)
    r *= s
    for a in (0.0, 1.0, 2.0):
        ang = math.radians(35 + a * 60)
        bx, by = cx + r * math.cos(ang), cy + r * math.sin(ang)
        sk.line((cx, cy), (bx, by), color=color, width=lw)
        # bent tip
        t1 = math.radians(35 + a * 60 - 38)
        sk.line((bx, by), (bx + r * 0.45 * math.cos(t1), by + r * 0.45 * math.sin(t1)),
                color=color, width=lw)


def _shock(sk: Sketcher, c: Point, r: float, color, lw, phase) -> None:
    """Radiating burst of short emphasis lines around the head (surprise)."""
    cx, cy = c
    s = 0.85 + 0.15 * math.sin(phase * math.tau * 3)
    for i in range(7):
        ang = i / 7 * math.tau + 0.3
        x0, y0 = cx + r * 1.18 * math.cos(ang), cy + r * 1.18 * math.sin(ang)
        x1, y1 = cx + r * (1.18 + 0.42 * s) * math.cos(ang), cy + r * (1.18 + 0.42 * s) * math.sin(ang)
        sk.line((x0, y0), (x1, y1), color=color, width=lw)


def _question(sk: Sketcher, c: Point, r: float, color, lw, phase) -> None:
    """A small bobbing thought '?'."""
    cx, cy = c
    cy += math.sin(phase * math.tau * 1.2) * r * 0.12  # bob
    sk.arc((cx, cy - r * 0.2), r * 0.5, 150, 410, color=color, width=lw)
    sk.line((cx + r * 0.0, cy + r * 0.3), (cx + r * 0.0, cy + r * 0.55), color=color, width=lw)
    sk.dot((cx, cy + r * 0.95), max(1.0, lw * 0.8), color=color)


def _motion_lines(sk: Sketcher, hip: Point, unit: float, color, lw, lean: float) -> None:
    """Short trailing speed lines behind a moving figure (trailing = opposite
    the lean direction)."""
    hx, hy = hip
    side = -1 if lean >= 0 else 1   # trail behind the direction of travel
    for i, fy in enumerate((-0.62, -0.40, -0.18)):
        y = hy + unit * fy
        x0 = hx + side * unit * 0.42
        x1 = x0 + side * unit * (0.26 + 0.05 * i)
        sk.line((x0, y), (x1, y), color=color, width=max(1, int(lw * 0.7)))


_GLYPHS = {"sparkle": _sparkle, "sparkle2": _sparkle, "sweat": _sweat,
           "anger": _anger, "shock": _shock, "question": _question}


def draw_effects(sk: Sketcher, head_c: Point, hr: float, hip: Point, unit: float,
                 face: str, pose_name, fx, accent, ink, phase: float) -> None:
    """Render emotion + motion glyphs around a figure.

    ``fx`` overrides the auto-derived set: a list of glyph names, or "none"."""
    if fx == "none":
        names: tuple[str, ...] = ()
    elif isinstance(fx, (list, tuple)) and fx:
        names = tuple(fx)
    else:
        names = _FACE_FX.get(face, ())

    cx, cy = head_c
    lw = max(1, int(sk.width * 0.8))

    # emotion glyphs, placed around the head so they never cover the face
    spark_slots = [(-1.35, -1.15, 0.0), (1.35, -1.25, 1.7)]
    si = 0
    for name in names:
        if name in ("sparkle", "sparkle2"):
            ox, oy, off = spark_slots[si % len(spark_slots)]
            si += 1
            _sparkle(sk, (cx + hr * ox, cy + hr * oy), hr * 0.5, _SPARK, lw, phase, off)
        elif name == "sweat":
            _sweat(sk, (cx + hr * 1.0, cy - hr * 0.35), hr * 0.42, _SWEAT, lw, phase)
        elif name == "anger":
            _anger(sk, (cx + hr * 1.2, cy - hr * 1.15), hr * 0.55, _ANGER, lw, phase)
        elif name == "shock":
            _shock(sk, head_c, hr, ink, lw, phase)
        elif name == "question":
            _question(sk, (cx + hr * 1.35, cy - hr * 1.35), hr * 0.7, accent, lw, phase)

    if (isinstance(fx, (list, tuple)) and "motion" in fx) or \
            (fx not in ("none",) and pose_name in _MOTION_POSES):
        from .figures import get_pose
        lean = get_pose(pose_name).get("lean", 0) if isinstance(pose_name, str) else 0
        _motion_lines(sk, hip, unit, ink, lw, lean)
