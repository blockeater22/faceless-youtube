"""Poses: partial maps of {bone_name: local_angle_deg}.

A pose only lists the bones it changes; the skeleton fills the rest from each
bone's rest angle. Poses live in a registry so packs/plugins add new ones
without code changes. Angles use the engine convention (0 = up, clockwise+).
"""
from __future__ import annotations

from ..core.keyframe import lerp_angle
from ..core.registry import Registry

POSES: "Registry" = Registry("pose")


def register_pose(name: str, pose: dict[str, float], *, overwrite: bool = False) -> dict:
    return POSES.register(name, dict(pose), overwrite=overwrite)


def get_pose(name: str | dict) -> dict[str, float]:
    """Resolve a pose name, or pass an inline pose dict straight through."""
    if isinstance(name, dict):
        return dict(name)
    return dict(POSES.get(name))


def blend_pose(p0: dict[str, float], p1: dict[str, float], t: float) -> dict[str, float]:
    """Shortest-arc blend of two (possibly partial) poses."""
    out: dict[str, float] = {}
    for bone in set(p0) | set(p1):
        a = p0.get(bone, p1.get(bone, 0.0))
        b = p1.get(bone, p0.get(bone, 0.0))
        out[bone] = lerp_angle(a, b, t)
    return out


# --------------------------------------------------------------------------- #
# Built-in pose library (data only). Values tuned for default_humanoid().
# --------------------------------------------------------------------------- #
_BUILTINS: dict[str, dict[str, float]] = {
    "stand": {},
    "idle": {"upper_arm_l": 199, "upper_arm_r": 161, "head": 2},
    "wave": {"upper_arm_r": 35, "forearm_r": -18, "head": 5},
    "think": {"upper_arm_l": 150, "forearm_l": 72, "head": -7},
    "point_up": {"upper_arm_r": 10, "forearm_r": 0, "head": -8},
    "point_left": {"upper_arm_l": 250, "forearm_l": 0, "head": -6},
    "point_right": {"upper_arm_r": 110, "forearm_r": 0, "head": 6},
    "reach_up": {"upper_arm_l": 340, "forearm_l": -6, "upper_arm_r": 20,
                 "forearm_r": 6, "head": -10},
    "celebrate": {"upper_arm_l": 330, "forearm_l": -12, "upper_arm_r": 30,
                  "forearm_r": 12, "head": -8, "thigh_l": 190, "thigh_r": 170},
    "shrug": {"upper_arm_l": 235, "forearm_l": 40, "upper_arm_r": 125,
              "forearm_r": -40, "head": 0},
    "wave_both": {"upper_arm_l": 320, "forearm_l": -20, "upper_arm_r": 40,
                  "forearm_r": 20},
    "walk_a": {"thigh_l": 205, "shin_l": -26, "thigh_r": 158, "shin_r": 22,
               "upper_arm_l": 150, "forearm_l": 18, "upper_arm_r": 200,
               "forearm_r": -18, "spine": 6},
    "walk_b": {"thigh_l": 158, "shin_l": 22, "thigh_r": 205, "shin_r": -26,
               "upper_arm_l": 200, "forearm_l": -18, "upper_arm_r": 150,
               "forearm_r": 18, "spine": 6},
    "jump": {"thigh_l": 200, "shin_l": -40, "thigh_r": 160, "shin_r": 40,
             "upper_arm_l": 325, "forearm_l": -10, "upper_arm_r": 35,
             "forearm_r": 10, "head": -6},
    "sit": {"thigh_l": 250, "shin_l": -70, "thigh_r": 250, "shin_r": -70,
            "upper_arm_l": 215, "forearm_l": 30, "upper_arm_r": 145,
            "forearm_r": -30},
    "facepalm": {"upper_arm_r": 25, "forearm_r": 60, "head": 10},
}

for _name, _pose in _BUILTINS.items():
    register_pose(_name, _pose)
