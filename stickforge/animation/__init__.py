"""Keyframed animation clips + procedural 'life' (breath / blink / sway)."""

from .clip import Posing, AnimationClip
from .procedural import breath, sway, blink_amount, apply_life, phase_for

__all__ = [
    "Posing",
    "AnimationClip",
    "breath",
    "sway",
    "blink_amount",
    "apply_life",
    "phase_for",
]
