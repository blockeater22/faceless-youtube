"""Animation math: easing, interpolation, and keyframe sampling.

Everything here is pure and side-effect free so it is trivial to reason about
and test. Times are expressed as a fraction of the scene duration in [0, 1].
"""
from __future__ import annotations

import math
from typing import Sequence


# --------------------------------------------------------------------------- #
# Easing functions: map t in [0,1] -> eased t in [0,1]
# --------------------------------------------------------------------------- #
def linear(t: float) -> float:
    return t


def ease_in_out(t: float) -> float:
    """Smoothstep - gentle acceleration and deceleration (the default)."""
    t = clamp(t)
    return t * t * (3.0 - 2.0 * t)


def ease_out(t: float) -> float:
    t = clamp(t)
    return 1.0 - (1.0 - t) ** 3


def ease_in(t: float) -> float:
    t = clamp(t)
    return t ** 3


def ease_out_back(t: float) -> float:
    """Slight overshoot - great for things that 'pop' into existence."""
    t = clamp(t)
    c1, c3 = 1.70158, 2.70158
    return 1.0 + c3 * (t - 1.0) ** 3 + c1 * (t - 1.0) ** 2


EASINGS = {
    "linear": linear,
    "ease": ease_in_out,
    "ease_in_out": ease_in_out,
    "ease_out": ease_out,
    "ease_in": ease_in,
    "pop": ease_out_back,
}


def clamp(t: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, t))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def lerp_seq(a: Sequence[float], b: Sequence[float], t: float) -> list[float]:
    return [lerp(x, y, t) for x, y in zip(a, b)]


def smooth_angle_lerp(a: float, b: float, t: float) -> float:
    """Interpolate degrees taking the shortest path around the circle."""
    d = (b - a + 180.0) % 360.0 - 180.0
    return a + d * t


# --------------------------------------------------------------------------- #
# Keyframe sampling
# --------------------------------------------------------------------------- #
def sample_keys(keys: list[dict], t: float, fields: dict[str, str]) -> dict:
    """Sample a list of keyframes at time ``t`` (0..1).

    ``keys`` is a list of dicts each holding a ``"t"`` plus arbitrary fields.
    ``fields`` maps field-name -> interpolation kind:
        "num"   scalar lerp
        "vec"   sequence lerp (e.g. position)
        "ang"   sequence of angles (shortest-path lerp)
        "step"  no interpolation - hold the previous key's value
    The eased fraction between two keys uses each key's own ``"ease"`` (the one
    we are travelling *into*), defaulting to smoothstep.
    """
    if not keys:
        return {}
    keys = sorted(keys, key=lambda k: k["t"])
    if t <= keys[0]["t"]:
        return {f: keys[0].get(f) for f in fields}
    if t >= keys[-1]["t"]:
        return {f: keys[-1].get(f) for f in fields}

    # locate the bracketing pair
    for i in range(len(keys) - 1):
        k0, k1 = keys[i], keys[i + 1]
        if k0["t"] <= t <= k1["t"]:
            span = (k1["t"] - k0["t"]) or 1e-9
            raw = (t - k0["t"]) / span
            ease = EASINGS.get(k1.get("ease", "ease_in_out"), ease_in_out)
            e = ease(raw)
            out = {}
            for f, kind in fields.items():
                v0, v1 = k0.get(f), k1.get(f)
                if v0 is None or v1 is None or kind == "step":
                    out[f] = v0 if v0 is not None else v1
                elif kind == "num":
                    out[f] = lerp(v0, v1, e)
                elif kind == "vec":
                    out[f] = lerp_seq(v0, v1, e)
                elif kind == "ang":
                    out[f] = [smooth_angle_lerp(a, b, e) for a, b in zip(v0, v1)]
                else:
                    out[f] = v0
            return out
    return {f: keys[-1].get(f) for f in fields}


def blend_pose(p0: dict, p1: dict, t: float) -> dict:
    """Blend two pose dicts (see figures.POSES) angle-by-angle."""
    out = {}
    for key in p0:
        a, b = p0[key], p1[key]
        if isinstance(a, (list, tuple)):
            out[key] = [smooth_angle_lerp(x, y, t) for x, y in zip(a, b)]
        else:
            out[key] = smooth_angle_lerp(a, b, t)
    return out
