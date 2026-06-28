"""Generative posing — build a pose from movement, not from limb angles.

A pose is not authored arms-first. It is *constructed* down the professional
pipeline: line of action -> weight/balance -> spine & head -> leg placement
(contrapposto) -> arm placement -> hand gesture. The low-level bone angles the
rig consumes are the *output* of that pipeline, never the input.

    build_pose(loa=12, weight=0.6, head=4, arm_l="down", arm_r="hip")

Angle convention (engine-wide): 0 = up, clockwise positive (90 = image-right).
"""
from __future__ import annotations

from dataclasses import dataclass

from .pose import register_pose


def _clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


# Arm placements for the LEFT side (image-left). The right side is the mirror
# image, derived automatically. (upper_arm_angle, forearm_local_angle).
ARM_LEFT: dict[str, tuple[float, float]] = {
    "down":  (193, -6),     # relaxed at the side
    "out":   (236, 2),      # extended to the side
    "up":    (322, -12),    # raised overhead
    "reach": (292, -20),    # diagonal up-and-out (appeal line)
    "front": (208, 46),     # forward / gesturing across
    "hip":   (150, 78),     # hand on hip (akimbo)
    "chest": (203, 60),     # hand to chest
    "cross": (218, -118),   # folded across the body
    "point": (250, 2),      # pointing to the side
    "chin":  (250, 132),    # hand to chin (pondering)
}


def _mirror(arm: tuple[float, float]) -> tuple[float, float]:
    """Reflect a left-arm placement to the right (x -> -x)."""
    upper, fore = arm
    return ((360 - upper) % 360, -fore)


def _legs(weight: float, crouch: float) -> dict:
    """Leg placement from weight distribution (contrapposto) + crouch.

    weight in [-1, 1]: 0 = even relaxed stance; +1 = all weight on the
    image-right foot (it goes vertical under the hip, the free leg relaxes out).
    """
    w = _clamp(weight, -1.0, 1.0)
    mag = abs(w)
    if mag < 0.18:                                  # even, gently splayed
        legs = {"thigh_l": 198, "shin_l": -14, "thigh_r": 162, "shin_r": 14}
    else:
        support_r = w >= 0
        out = 18 + 12 * mag
        bend = 12 + 12 * mag
        if support_r:                               # weight on right foot
            legs = {"thigh_r": 178, "shin_r": 2,            # support: vertical
                    "thigh_l": 180 + out, "shin_l": -bend}  # free: out + bent
        else:                                       # weight on left foot
            legs = {"thigh_l": 182, "shin_l": -2,
                    "thigh_r": 180 - out, "shin_r": bend}
    if crouch > 0:                                  # bend both knees, sink down
        c = _clamp(crouch, 0, 1)
        legs = {"thigh_l": 206, "shin_l": -36 * c - 8, "thigh_r": 154,
                "shin_r": 36 * c + 8}
    return legs


@dataclass
class PoseIntent:
    loa: float = 0.0           # line of action curvature (deg); the dominant flow
    weight: float = 0.0        # -1..1 weight distribution (contrapposto)
    head: float = 0.0          # head direction / tilt (deg)
    arm_l: str = "down"
    arm_r: str = "down"
    crouch: float = 0.0        # 0..1 knee bend / sink


def build_pose(loa: float = 0.0, weight: float = 0.0, head: float = 0.0,
               arm_l: str = "down", arm_r: str = "down",
               crouch: float = 0.0) -> dict:
    """Construct a bone-angle pose from the movement pipeline (see module doc)."""
    pose = _legs(weight, crouch)
    # spine follows the line of action; it also counter-leans to stay balanced
    # over the weighted foot (upper mass shifts toward the free side).
    pose["spine"] = loa - 6.0 * weight
    # head completes the curve (counter to the LOA) and adds its own direction
    pose["head"] = head - 0.45 * loa + 3.0 * weight
    # arms are placed LAST
    uL, fL = ARM_LEFT.get(arm_l, ARM_LEFT["down"])
    uR, fR = _mirror(ARM_LEFT.get(arm_r, ARM_LEFT["down"]))
    pose["upper_arm_l"], pose["forearm_l"] = uL, fL
    pose["upper_arm_r"], pose["forearm_r"] = uR, fR
    return pose


def from_intent(i: PoseIntent) -> dict:
    return build_pose(i.loa, i.weight, i.head, i.arm_l, i.arm_r, i.crouch)


# --------------------------------------------------------------------------- #
# Regenerate the acting stances *through the pipeline* so they carry a line of
# action and real weight instead of being stiff and symmetric.
# --------------------------------------------------------------------------- #
_GENERATED = {
    "stand":        dict(loa=5, weight=0.5, head=2),                 # relaxed contrapposto
    "idle":         dict(loa=4, weight=0.45, head=2),
    "open_arms":    dict(loa=-6, weight=0.4, head=-3, arm_l="out", arm_r="out"),
    "reach_joy":    dict(loa=-8, weight=0.3, head=-8, arm_l="up", arm_r="reach"),
    "hand_on_hip":  dict(loa=10, weight=0.6, head=-4, arm_l="down", arm_r="hip"),
    "power_stance": dict(loa=0, weight=0.0, head=-2, arm_l="out", arm_r="out", crouch=0.12),
    "lean_in":      dict(loa=14, weight=0.5, head=6, arm_l="down", arm_r="front"),
    "hands_chest":  dict(loa=-5, weight=0.35, head=-6, arm_l="chest", arm_r="chest"),
}


def register_generated_poses() -> None:
    for name, kw in _GENERATED.items():
        register_pose(name, build_pose(**kw), overwrite=True)


register_generated_poses()
