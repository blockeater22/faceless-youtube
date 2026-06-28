"""Camera2D — the single bridge from world space to screen pixels.

The camera has a world-space ``center`` (what sits at the middle of frame) and a
``zoom``. :meth:`project` maps a world point to a pixel, applying the layer's
parallax so distant layers respond less to camera moves. Nothing else in the
engine is allowed to compute screen coordinates — the Cinematic Engine will
drive this object (pans, push-ins, framing) without the renderer changing.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..core.geometry import Vec2
from .world import REFERENCE, Viewport


@dataclass
class Camera2D:
    center: Vec2 = Vec2(0.0, 0.0)     # world point shown at screen centre
    zoom: float = 1.0
    rotation: float = 0.0             # reserved (dutch angle), degrees

    def screen_scale(self, viewport: Viewport) -> float:
        """Pixels per world unit at this zoom."""
        return (viewport.min_dim / REFERENCE) * self.zoom

    def project(self, world: Vec2, viewport: Viewport, parallax: float = 1.0) -> Vec2:
        """World point -> screen pixel (parallax shrinks the camera offset)."""
        s = self.screen_scale(viewport)
        cam = Vec2(self.center.x * parallax, self.center.y * parallax)
        vc = viewport.center
        return Vec2((world.x - cam.x) * s + vc.x, (world.y - cam.y) * s + vc.y)

    def unproject(self, screen: Vec2, viewport: Viewport, parallax: float = 1.0) -> Vec2:
        """Screen pixel -> world point (inverse of :meth:`project`)."""
        s = self.screen_scale(viewport)
        vc = viewport.center
        return Vec2((screen.x - vc.x) / s + self.center.x * parallax,
                    (screen.y - vc.y) / s + self.center.y * parallax)

    # -- cinematic helpers (used later by the Cinematic Engine) ----------- #
    def look_at(self, point: Vec2) -> "Camera2D":
        return Camera2D(center=point, zoom=self.zoom, rotation=self.rotation)

    def framed_on(self, point: Vec2, height_units: float,
                  viewport: Viewport) -> "Camera2D":
        """Frame so ``height_units`` of world fills the viewport's short edge."""
        z = REFERENCE / max(1e-6, height_units)
        return Camera2D(center=point, zoom=z, rotation=self.rotation)

    @classmethod
    def from_pan_zoom(cls, zoom: float, pan_x: float, pan_y: float,
                      viewport: Viewport) -> "Camera2D":
        """Bridge the legacy {zoom, pan_x(frac), pan_y(frac)} camera sample."""
        size = viewport.world_size()
        return cls(center=Vec2(-pan_x * size.x, -pan_y * size.y), zoom=zoom)
