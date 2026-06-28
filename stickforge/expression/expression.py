"""Expressions: a small set of continuous facial parameters, composed.

Rather than hardcoding a face per emotion, every expression is a point in a
shared parameter space. Emotions are named presets; anything in between is just
a blend. The renderer reads these parameters — it knows nothing about "happy"
or "angry".

Parameters (all roughly in [-1, 1] or [0, 1], relative to the head radius):
    brow_l_h / brow_r_h    raise (+) or lower (-) each brow
    brow_l_a / brow_r_a    inner-end tilt in degrees (+ = inner down = angry)
    eye_open               1 = wide open, 0 = shut
    eye_wide               extra widening (surprise/fear)
    pupil_x / pupil_y      gaze direction (eye tracking)
    mouth_curve            -1 = frown, +1 = smile
    mouth_open             0 = closed, 1 = fully open
    mouth_skew             asymmetry (smirk)
    tears                  0..1 cry intensity (renderer may draw drops)
"""
from __future__ import annotations

from ..core.keyframe import lerp
from ..core.registry import Registry

EXPRESSIONS: "Registry" = Registry("expression")

NEUTRAL: dict[str, float] = {
    "brow_l_h": 0.0, "brow_r_h": 0.0,
    "brow_l_a": 0.0, "brow_r_a": 0.0,
    "eye_open": 1.0, "eye_wide": 0.0,
    "pupil_x": 0.0, "pupil_y": 0.0,
    "mouth_curve": 0.0, "mouth_open": 0.0, "mouth_skew": 0.0,
    "tears": 0.0,
}


def register_expression(name: str, params: dict[str, float], *,
                        overwrite: bool = False) -> dict:
    return EXPRESSIONS.register(name, dict(params), overwrite=overwrite)


def get_expression(name: str | dict) -> dict[str, float]:
    """Return a *complete* parameter set (preset merged over NEUTRAL)."""
    preset = name if isinstance(name, dict) else EXPRESSIONS.get(name)
    full = dict(NEUTRAL)
    full.update(preset)
    return full


def blend_expression(a: dict[str, float], b: dict[str, float],
                     t: float) -> dict[str, float]:
    """Linear blend of two expressions (completed against NEUTRAL first)."""
    fa, fb = dict(NEUTRAL), dict(NEUTRAL)
    fa.update(a)
    fb.update(b)
    return {k: lerp(fa[k], fb[k], t) for k in NEUTRAL}


# --------------------------------------------------------------------------- #
# Built-in emotion presets (partial; merged over NEUTRAL on resolve).
# --------------------------------------------------------------------------- #
_BUILTINS: dict[str, dict[str, float]] = {
    "neutral": {},
    "happy": {"mouth_curve": 0.85, "brow_l_h": 0.10, "brow_r_h": 0.10, "eye_open": 0.92},
    "excited": {"mouth_curve": 0.9, "mouth_open": 0.45, "eye_wide": 0.5,
                "brow_l_h": 0.28, "brow_r_h": 0.28},
    "sad": {"mouth_curve": -0.7, "brow_l_a": -16, "brow_r_a": -16,
            "brow_l_h": 0.12, "brow_r_h": 0.12, "eye_open": 0.72},
    "angry": {"mouth_curve": -0.4, "brow_l_a": 22, "brow_r_a": 22,
              "brow_l_h": -0.16, "brow_r_h": -0.16, "eye_wide": 0.12},
    "surprised": {"eye_wide": 0.85, "mouth_open": 0.7, "brow_l_h": 0.32,
                  "brow_r_h": 0.32},
    "shocked": {"eye_wide": 1.0, "mouth_open": 0.95, "brow_l_h": 0.4,
                "brow_r_h": 0.4},
    "confused": {"brow_l_h": 0.28, "brow_r_h": -0.08, "mouth_curve": -0.12,
                 "mouth_skew": 0.3},
    "thinking": {"pupil_y": -0.55, "pupil_x": 0.35, "brow_l_h": 0.12,
                 "mouth_curve": -0.05, "mouth_skew": 0.25},
    "scared": {"eye_wide": 0.7, "brow_l_h": 0.28, "brow_r_h": 0.28,
               "mouth_open": 0.35, "mouth_curve": -0.3},
    "nervous": {"eye_open": 0.85, "brow_l_h": 0.18, "brow_r_h": 0.1,
                "mouth_curve": -0.2, "mouth_skew": 0.35, "pupil_x": 0.3},
    "sleepy": {"eye_open": 0.25, "brow_l_h": -0.06, "brow_r_h": -0.06},
    "laughing": {"eye_open": 0.15, "mouth_curve": 0.9, "mouth_open": 0.6,
                 "brow_l_h": 0.15, "brow_r_h": 0.15},
    "crying": {"eye_open": 0.2, "mouth_curve": -0.8, "mouth_open": 0.3,
               "brow_l_a": -18, "brow_r_a": -18, "tears": 1.0},
    "smirk": {"mouth_curve": 0.35, "mouth_skew": 0.7, "brow_l_h": 0.12,
              "eye_open": 0.9},
    "determined": {"brow_l_a": 12, "brow_r_a": 12, "eye_wide": 0.1,
                   "mouth_curve": -0.05},
    "proud": {"mouth_curve": 0.6, "brow_l_h": 0.1, "brow_r_h": 0.1,
              "eye_open": 0.85, "pupil_y": -0.1},
    "exhausted": {"eye_open": 0.35, "mouth_open": 0.25, "mouth_curve": -0.2,
                  "brow_l_h": 0.08, "brow_r_h": 0.08},
}

for _name, _params in _BUILTINS.items():
    register_expression(_name, _params)
