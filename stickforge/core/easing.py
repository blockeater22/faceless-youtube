"""Easing curves: map a normalized time t in [0,1] to an eased value in [0,1].

These are the temporal backbone of the animation engine. New curves can be
added by other modules via :data:`EASINGS.register`.
"""
from __future__ import annotations

import math
from typing import Callable

from .registry import Registry

EASINGS: "Registry" = Registry("easing")


def clamp(t: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if t < lo else hi if t > hi else t


@EASINGS.register("linear")
def linear(t: float) -> float:
    return clamp(t)


@EASINGS.register("ease")
@EASINGS.register("ease_in_out")
def ease_in_out(t: float) -> float:
    """Smoothstep — the gentle default."""
    t = clamp(t)
    return t * t * (3.0 - 2.0 * t)


@EASINGS.register("ease_in")
def ease_in(t: float) -> float:
    t = clamp(t)
    return t * t * t


@EASINGS.register("ease_out")
def ease_out(t: float) -> float:
    t = clamp(t)
    return 1.0 - (1.0 - t) ** 3


@EASINGS.register("pop")
@EASINGS.register("ease_out_back")
def ease_out_back(t: float) -> float:
    """Overshoot then settle — great for things that 'pop' in."""
    t = clamp(t)
    c1, c3 = 1.70158, 2.70158
    return 1.0 + c3 * (t - 1.0) ** 3 + c1 * (t - 1.0) ** 2


@EASINGS.register("anticipate")
def anticipate(t: float) -> float:
    """Dip back slightly before moving forward — animation anticipation."""
    t = clamp(t)
    c = 1.70158
    return t * t * ((c + 1) * t - c)


@EASINGS.register("bounce")
def bounce(t: float) -> float:
    t = clamp(t)
    n1, d1 = 7.5625, 2.75
    if t < 1 / d1:
        return n1 * t * t
    if t < 2 / d1:
        t -= 1.5 / d1
        return n1 * t * t + 0.75
    if t < 2.5 / d1:
        t -= 2.25 / d1
        return n1 * t * t + 0.9375
    t -= 2.625 / d1
    return n1 * t * t + 0.984375


@EASINGS.register("elastic")
def elastic(t: float) -> float:
    t = clamp(t)
    if t in (0.0, 1.0):
        return t
    c4 = (2 * math.pi) / 3
    return 2 ** (-10 * t) * math.sin((t * 10 - 0.75) * c4) + 1


def get(name: str | Callable[[float], float] | None):
    """Resolve an easing by name, pass through a callable, or default to ease."""
    if name is None:
        return ease_in_out
    if callable(name):
        return name
    return EASINGS.get(name)
