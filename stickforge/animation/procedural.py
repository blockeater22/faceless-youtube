"""Procedural 'life': cheap per-frame motion so a figure is never frozen.

Breathing, weight-shift sway, and periodic blinks are layered on top of any
posed/keyframed animation. This is the single biggest quality lever versus a
"pose, then hold" look. All functions are pure and deterministic given a phase.
"""
from __future__ import annotations

import hashlib
import math

from .clip import Posing


def phase_for(seed: str) -> float:
    """A stable phase offset per figure, so figures don't move in lockstep."""
    h = int(hashlib.md5(str(seed).encode()).hexdigest()[:8], 16)
    return (h % 1000) / 1000.0 * math.tau


def breath(t: float, phase: float, period: float = 4.0) -> float:
    return math.sin(t * (math.tau / period) + phase)


def sway(t: float, phase: float, period: float = 6.5) -> float:
    return math.sin(t * (math.tau / period) + phase * 1.3)


def blink_amount(t: float, phase: float, every: float = 3.6, dur: float = 0.16) -> float:
    """0 = eyes fully open contribution, 1 = fully shut, smooth in/out."""
    local = (t + phase * 0.57) % every
    if local >= dur:
        return 0.0
    # smooth close-then-open within the blink window
    x = local / dur
    return math.sin(x * math.pi)


def apply_life(posing: Posing, t: float, phase: float, amount: float = 1.0) -> Posing:
    """Return a copy of ``posing`` with breathing/sway/blink layered in."""
    if amount <= 0:
        return posing
    b, s = breath(t, phase), sway(t, phase)
    pose = dict(posing.pose)
    pose["spine"] = pose.get("spine", 0.0) + s * 1.6 * amount
    pose["head"] = pose.get("head", 0.0) + b * 1.2 * amount
    # subtle shoulder lift on the inhale
    pose["upper_arm_l"] = pose.get("upper_arm_l", 196.0) + b * 1.4 * amount
    pose["upper_arm_r"] = pose.get("upper_arm_r", 164.0) - b * 1.4 * amount

    expr = dict(posing.expr)
    shut = blink_amount(t, phase) * amount
    if shut > 0:
        expr["eye_open"] = expr.get("eye_open", 1.0) * (1.0 - shut)

    off = posing.offset
    from ..core.geometry import Vec2
    off = Vec2(off.x + s * 0.006 * amount, off.y + b * 0.004 * amount)

    return Posing(pose=pose, expr=expr, offset=off, scale=posing.scale)
