"""PartFrame: the local coordinate frame handed to a part's art provider.

A part is drawn in a small local space anchored at ``center``, scaled by
``size`` (pixels — usually the head radius for face parts, or a hand/foot
radius), oriented by ``angle`` (the bone/head world angle), tinted by
``palette`` and modulated by ``params`` (e.g. expression values or style
options). The helper :meth:`at` maps local part coordinates (x right, y down,
in units of ``size``) into world pixels honoring the orientation.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..core.geometry import Vec2


@dataclass
class PartFrame:
    center: Vec2
    size: float
    angle: float = 0.0
    palette: dict = field(default_factory=dict)
    params: dict = field(default_factory=dict)
    outline_w: float = 2.0

    def at(self, lx: float, ly: float) -> Vec2:
        """Local (lx, ly) in size-units -> world pixel, honoring orientation."""
        return Vec2(lx * self.size, ly * self.size).rotated(self.angle) + self.center

    def color(self, key: str, default: str = "#23272e") -> str:
        return self.palette.get(key, default)

    def p(self, key: str, default: float = 0.0) -> float:
        return float(self.params.get(key, default))
