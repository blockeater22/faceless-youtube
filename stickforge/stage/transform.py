"""Transform2D — a 2D affine transform (the composable unit of the scene graph).

Stored as a 2x3 matrix [[a, c, e], [b, d, f]] mapping a point (x, y) to
(a*x + c*y + e, b*x + d*y + f). Transforms compose with ``@`` (parent @ child),
so a node's world transform is the product of its ancestors' locals. Rotation is
clockwise in image space (consistent with the engine's angle convention).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from ..core.geometry import Vec2


@dataclass(frozen=True)
class Transform2D:
    a: float = 1.0
    b: float = 0.0
    c: float = 0.0
    d: float = 1.0
    e: float = 0.0
    f: float = 0.0

    # -- constructors ----------------------------------------------------- #
    @staticmethod
    def identity() -> "Transform2D":
        return Transform2D()

    @staticmethod
    def translate(tx: float, ty: float) -> "Transform2D":
        return Transform2D(1, 0, 0, 1, tx, ty)

    @staticmethod
    def scale(sx: float, sy: float | None = None) -> "Transform2D":
        return Transform2D(sx, 0, 0, sx if sy is None else sy, 0, 0)

    @staticmethod
    def rotate(deg: float) -> "Transform2D":
        r = math.radians(deg)
        cos, sin = math.cos(r), math.sin(r)
        return Transform2D(cos, sin, -sin, cos, 0, 0)

    # -- algebra ---------------------------------------------------------- #
    def __matmul__(self, other: "Transform2D") -> "Transform2D":
        """self @ other: apply ``other`` first, then ``self``."""
        return Transform2D(
            self.a * other.a + self.c * other.b,
            self.b * other.a + self.d * other.b,
            self.a * other.c + self.c * other.d,
            self.b * other.c + self.d * other.d,
            self.a * other.e + self.c * other.f + self.e,
            self.b * other.e + self.d * other.f + self.f,
        )

    def apply(self, p: Vec2) -> Vec2:
        return Vec2(self.a * p.x + self.c * p.y + self.e,
                    self.b * p.x + self.d * p.y + self.f)

    def apply_xy(self, x: float, y: float) -> Vec2:
        return Vec2(self.a * x + self.c * y + self.e,
                    self.b * x + self.d * y + self.f)

    def inverse(self) -> "Transform2D":
        det = self.a * self.d - self.b * self.c
        if abs(det) < 1e-12:
            return Transform2D.identity()
        ia, ib = self.d / det, -self.b / det
        ic, idd = -self.c / det, self.a / det
        ie = -(ia * self.e + ic * self.f)
        if_ = -(ib * self.e + idd * self.f)
        return Transform2D(ia, ib, ic, idd, ie, if_)

    @property
    def scale_factor(self) -> float:
        """Approximate uniform scale (mean of axis lengths)."""
        sx = math.hypot(self.a, self.b)
        sy = math.hypot(self.c, self.d)
        return (sx + sy) / 2.0
