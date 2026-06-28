"""2D geometry primitives.

Angle convention (used everywhere in the engine):
    degrees, measured CLOCKWISE from straight up, in image space (y grows down).
        0   -> up        (0, -1)
        90  -> right      (1,  0)
        180 -> down       (0,  1)
        270 -> left      (-1,  0)

This convention is chosen so that a stickman's spine "pointing up" is angle 0,
which makes hand-authored poses read naturally.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Vec2:
    """An immutable 2D point/vector with the usual arithmetic."""

    x: float
    y: float

    # -- arithmetic ------------------------------------------------------- #
    def __add__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, k: float) -> "Vec2":
        return Vec2(self.x * k, self.y * k)

    __rmul__ = __mul__

    def __truediv__(self, k: float) -> "Vec2":
        return Vec2(self.x / k, self.y / k)

    def __iter__(self):
        yield self.x
        yield self.y

    # -- queries ---------------------------------------------------------- #
    def length(self) -> float:
        return math.hypot(self.x, self.y)

    def normalized(self) -> "Vec2":
        n = self.length()
        return self if n == 0 else Vec2(self.x / n, self.y / n)

    def rotated(self, deg: float, around: "Vec2 | None" = None) -> "Vec2":
        """Rotate clockwise (image space) by ``deg`` degrees around a pivot."""
        pivot = around or Vec2(0.0, 0.0)
        r = math.radians(deg)
        c, s = math.cos(r), math.sin(r)
        dx, dy = self.x - pivot.x, self.y - pivot.y
        # clockwise in y-down space:
        return Vec2(pivot.x + dx * c - dy * s, pivot.y + dx * s + dy * c)

    def lerp(self, other: "Vec2", t: float) -> "Vec2":
        return Vec2(self.x + (other.x - self.x) * t,
                    self.y + (other.y - self.y) * t)

    def as_tuple(self) -> tuple[float, float]:
        return (self.x, self.y)


def polar(origin: Vec2, length: float, angle_deg: float) -> Vec2:
    """Point ``length`` away from ``origin`` in direction ``angle_deg``.

    Uses the engine angle convention (0 = up, clockwise positive, y-down).
    """
    r = math.radians(angle_deg)
    return Vec2(origin.x + length * math.sin(r),
                origin.y - length * math.cos(r))


def angle_between(a: Vec2, b: Vec2) -> float:
    """Engine-convention angle of the vector from ``a`` to ``b`` (degrees)."""
    dx, dy = b.x - a.x, b.y - a.y
    # invert dy because y grows downward; result in [0, 360)
    return math.degrees(math.atan2(dx, -dy)) % 360.0
