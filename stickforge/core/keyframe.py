"""Keyframes and tracks — the data-driven heart of all animation.

A :class:`Track` is an ordered list of :class:`Keyframe` values over time. The
sampler interpolates between the bracketing keys using the easing of the key
being travelled *into*. Tracks are agnostic about what they drive: a joint
angle, an expression parameter, a camera value, an x/y offset — anything that
can be interpolated by the chosen ``interp`` mode.

Pure and side-effect free, so it is trivial to unit test.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from . import easing


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def lerp_angle(a: float, b: float, t: float) -> float:
    """Interpolate degrees along the shortest arc."""
    d = (b - a + 180.0) % 360.0 - 180.0
    return a + d * t


def _interp(a, b, t: float, mode: str):
    if mode == "step":
        return a
    if mode == "angle":
        return lerp_angle(a, b, t)
    if mode == "vec":
        return [lerp(x, y, t) for x, y in zip(a, b)]
    return lerp(a, b, t)            # "num" (default)


@dataclass(frozen=True)
class Keyframe:
    """A value at a time, plus the easing used to *arrive* at it."""

    t: float                       # seconds (or any monotonic unit)
    value: float | Sequence[float]
    ease: str = "ease_in_out"


@dataclass
class Track:
    """A named sequence of keyframes with an interpolation mode.

    ``interp`` is one of: ``"num"`` (scalar), ``"angle"`` (shortest-arc
    degrees), ``"vec"`` (component-wise), ``"step"`` (hold).
    """

    name: str
    keys: list[Keyframe] = field(default_factory=list)
    interp: str = "num"

    def __post_init__(self) -> None:
        self.keys = sorted(self.keys, key=lambda k: k.t)

    def add(self, t: float, value, ease: str = "ease_in_out") -> "Track":
        self.keys.append(Keyframe(t, value, ease))
        self.keys.sort(key=lambda k: k.t)
        return self

    @property
    def duration(self) -> float:
        return self.keys[-1].t if self.keys else 0.0

    def sample(self, t: float):
        return sample_track(self, t)


def sample_track(track: Track, t: float):
    """Value of ``track`` at time ``t`` (clamped to its endpoints)."""
    keys = track.keys
    if not keys:
        return None
    if t <= keys[0].t:
        return keys[0].value
    if t >= keys[-1].t:
        return keys[-1].value
    for i in range(len(keys) - 1):
        k0, k1 = keys[i], keys[i + 1]
        if k0.t <= t <= k1.t:
            span = (k1.t - k0.t) or 1e-9
            raw = (t - k0.t) / span
            e = easing.get(k1.ease)(raw)
            return _interp(k0.value, k1.value, e, track.interp)
    return keys[-1].value
