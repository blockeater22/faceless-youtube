"""Procedural body language — derived from the acting engine, not canned.

Reuses each emotion's acting profile (idle amplitude, tempo, gaze bias, blink
rate, signature hands/pose) and adds a directorial reading (posture, gesture
size, movement speed, breathing). No baked clips — the renderer/acting layer
realizes these parameters.
"""
from __future__ import annotations

from ..acting.emotion import get_emotion
from .proxemics import posture_for


def body_language(emotion: str) -> dict:
    p = get_emotion(emotion)
    energy = round(p.idle_amp, 2)
    return {
        "posture": posture_for(emotion),
        "energy": energy,
        "breathing": "fast" if energy > 1.2 else "slow" if energy < 0.85 else "even",
        "movement_speed": round(min(1.6, max(0.6, p.tempo)), 2),
        "gesture_size": ("small" if posture_for(emotion) == "small"
                         else "large" if emotion in ("excited", "confident", "angry")
                         else "medium"),
        "gaze_bias": list(p.eye),
        "blink_rate": p.blink_rate,
        "rest_pose": p.pose,
        "rest_hands": list(p.hands),
    }
