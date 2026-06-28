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
    """Layer involuntary life over a posing — emotion-aware.

    ``posing.idle_amp`` scales the motion (calm vs. agitated) and
    ``posing.blink_rate`` scales how often the eyes blink, so a nervous beat
    fidgets and blinks fast while a confident beat is still and slow.
    """
    if amount <= 0:
        return posing
    amp = amount * max(0.0, posing.idle_amp)
    b, s = breath(t, phase), sway(t, phase)
    # weight-shift: a slow side-to-side balance correction
    ws = math.sin(t * (math.tau / 9.0) + phase * 2.1)
    pose = dict(posing.pose)
    pose["spine"] = pose.get("spine", 0.0) + (s * 1.5 + ws * 0.8) * amp
    pose["head"] = pose.get("head", 0.0) + b * 1.2 * amp
    pose["upper_arm_l"] = pose.get("upper_arm_l", 196.0) + b * 1.4 * amp
    pose["upper_arm_r"] = pose.get("upper_arm_r", 164.0) - b * 1.4 * amp
    # fidget: small high-frequency limb jitter when agitated (idle_amp > 1)
    fidget = max(0.0, posing.idle_amp - 1.0)
    if fidget > 0:
        j = math.sin(t * 9.3 + phase * 3.0) * 2.2 * fidget * amount
        pose["forearm_l"] = pose.get("forearm_l", -6.0) + j
        pose["forearm_r"] = pose.get("forearm_r", 6.0) - j

    expr = dict(posing.expr)
    every = 3.6 / max(0.2, posing.blink_rate)
    shut = blink_amount(t, phase, every=every) * amount
    if shut > 0:
        expr["eye_open"] = expr.get("eye_open", 1.0) * (1.0 - shut)
    # eye micro-scan: living eyes drift a touch (never overrides intent fully)
    expr["pupil_x"] = expr.get("pupil_x", 0.0) + math.sin(t * 0.9 + phase) * 0.06 * amount
    expr["pupil_y"] = expr.get("pupil_y", 0.0) + math.sin(t * 0.7 + phase * 1.7) * 0.04 * amount

    from ..core.geometry import Vec2
    off = posing.offset
    off = Vec2(off.x + s * 0.006 * amp, off.y + b * 0.004 * amp)

    return Posing(pose=pose, expr=expr, offset=off, scale=posing.scale,
                  hands=posing.hands, idle_amp=posing.idle_amp,
                  blink_rate=posing.blink_rate)
