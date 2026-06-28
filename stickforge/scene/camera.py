"""The Camera: keyframable zoom / pan plus deterministic shake.

The camera is resolved to a simple affine (scale about a focal point, then
translate), which the renderer emits as an SVG group transform. Zoom, pan, and
shake are all data-driven so cinematic moves ship as assets.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field

from ..core.keyframe import Track, Keyframe, sample_track


def _track(keys: list[dict], interp: str = "num") -> Track | None:
    if not keys:
        return None
    return Track("cam", [Keyframe(k["t"], k["value"], k.get("ease", "ease_in_out"))
                         for k in keys], interp=interp)


@dataclass
class Camera:
    zoom: float = 1.0
    pan_x: float = 0.0               # fraction of width
    pan_y: float = 0.0               # fraction of height
    shake: float = 0.0               # fraction of min-dim amplitude
    zoom_track: Track | None = None
    pan_x_track: Track | None = None
    pan_y_track: Track | None = None
    seed: int = 0

    @classmethod
    def from_spec(cls, spec: dict) -> "Camera":
        spec = spec or {}
        return cls(
            zoom=float(spec.get("zoom", 1.0)),
            pan_x=float(spec.get("pan_x", 0.0)),
            pan_y=float(spec.get("pan_y", 0.0)),
            shake=float(spec.get("shake", 0.0)),
            zoom_track=_track(spec.get("zoom_keys", [])),
            pan_x_track=_track(spec.get("pan_x_keys", [])),
            pan_y_track=_track(spec.get("pan_y_keys", [])),
            seed=int(hashlib.md5(repr(spec).encode()).hexdigest()[:6], 16),
        )

    def sample(self, t: float) -> dict:
        zoom = sample_track(self.zoom_track, t) if self.zoom_track else self.zoom
        px = sample_track(self.pan_x_track, t) if self.pan_x_track else self.pan_x
        py = sample_track(self.pan_y_track, t) if self.pan_y_track else self.pan_y
        sx = sy = 0.0
        if self.shake > 0:
            # two incommensurate sines => non-repeating jitter
            sx = self.shake * math.sin(t * 37.0 + self.seed)
            sy = self.shake * math.sin(t * 41.3 + self.seed * 1.7)
        return {"zoom": max(0.01, zoom), "pan_x": px + sx, "pan_y": py + sy}
