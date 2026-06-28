"""World space conventions + the output viewport.

World space is resolution-independent. Distances are in *world units*; the
reference is :data:`REFERENCE` units across the viewport's short edge at camera
zoom 1.0 (mirroring the engine's "min-dim = constant" rule, so a character is
the same size in 9:16 and 16:9). The origin is the default frame centre; +y is
down (image convention); the ground plane is a fixed +y.

A :class:`Viewport` is the only place pixels appear before the camera projects.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..core.geometry import Vec2

REFERENCE = 1000.0            # world units across the short edge at zoom 1
GROUND_Y = 300.0             # ground plane (world units below the origin)


@dataclass(frozen=True)
class Viewport:
    width: int
    height: int

    @property
    def min_dim(self) -> int:
        return min(self.width, self.height)

    @property
    def center(self) -> Vec2:
        return Vec2(self.width / 2.0, self.height / 2.0)

    def world_size(self) -> Vec2:
        """The world-space extent visible at zoom 1.0."""
        k = REFERENCE / self.min_dim
        return Vec2(self.width * k, self.height * k)


class World:
    """Static helpers for placing content in world space."""

    REFERENCE = REFERENCE
    GROUND_Y = GROUND_Y

    @staticmethod
    def frac_to_world(fx: float, fy: float, viewport: Viewport) -> Vec2:
        """Convert legacy screen fractions (0..1) to world units, such that the
        default camera reproduces the original framing (compatibility bridge)."""
        size = viewport.world_size()
        return Vec2((fx - 0.5) * size.x, (fy - 0.5) * size.y)

    @staticmethod
    def on_ground(x: float) -> Vec2:
        """A point standing on the ground plane at world-x ``x``."""
        return Vec2(x, GROUND_Y)
