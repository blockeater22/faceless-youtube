"""Procedural 'life' for figures + a Ken Burns camera.

Pure, cheap, per-frame helpers that make a static stick figure feel alive
(breathing, sway, blinks) and give every shot subtle motion (slow zoom/drift).
This is the single biggest quality lever vs. the old "fade in, then freeze"
look — retention guides are unanimous that *something must keep moving*.
"""
from __future__ import annotations

import hashlib
import math

from PIL import Image


def phase_for(actor_id: str) -> float:
    """A stable per-figure phase offset so two figures don't breathe in lockstep."""
    h = int(hashlib.md5(str(actor_id).encode()).hexdigest()[:8], 16)
    return (h % 1000) / 1000.0 * math.tau


def breath(t: float, phase: float, period: float = 4.0) -> float:
    """-1..1 slow vertical bob (a calm ~4s breathing cycle)."""
    return math.sin(t * (math.tau / period) + phase)


def sway(t: float, phase: float, period: float = 6.5) -> float:
    """-1..1 even slower side-to-side weight shift."""
    return math.sin(t * (math.tau / period) + phase * 1.3)


def is_blink(t: float, phase: float, every: float = 3.6, dur: float = 0.13) -> bool:
    """Deterministic blink windows — eyes shut briefly every few seconds."""
    return (t + phase * 0.57) % every < dur


def scene_seed(scene_id: str) -> int:
    return int(hashlib.md5(str(scene_id).encode()).hexdigest()[:8], 16)


def camera(frame: Image.Image, prog: float, seed: int, amp: float) -> Image.Image:
    """Apply a slow Ken Burns move to an RGBA world frame; returns same size.

    Push-in on even seeds, pull-out on odd, plus a gentle drift — so back-to-back
    scenes never move the same way. ``prog`` is 0..1 through the scene.
    """
    if amp <= 0:
        return frame
    w, h = frame.size
    r = (seed % 1000) / 1000.0
    e = prog * prog * (3.0 - 2.0 * prog)         # smoothstep
    z = 1.0 + amp * (e if seed % 2 == 0 else (1.0 - e))
    z = max(1.0, z)
    cw, ch = w / z, h / z
    dx = (r - 0.5) * 0.020 * w * e               # drift up to ~1% of frame
    dy = ((r * 7.0 % 1.0) - 0.5) * 0.015 * h * e
    cx = min(max(cw / 2, w / 2 + dx), w - cw / 2)
    cy = min(max(ch / 2, h / 2 + dy), h - ch / 2)
    box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
    return frame.resize((w, h), Image.LANCZOS, box=box)
