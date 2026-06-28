"""Archetypes — personality-first character design.

A character is defined by *who they are*, not *what assets are attached*. An
:class:`Archetype` encodes the professional levers that make a character
instantly recognizable and non-interchangeable:

  * shape language  — round (friendly), square (strong/heavy), triangle
    (dynamic/heroic): the dominant read of the silhouette.
  * proportions     — head size, torso, limb length & thickness, stance width.
    These build a *parametric skeleton*, so two archetypes never share a
    silhouette.
  * posture / body language — a signature resting pose (arms crossed, hand on
    hip, hands clasped) that telegraphs attitude before any motion.
  * acting tendency — a resting expression and signature gesture.

Every field answers "what does this tell the audience about this character?"
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..core.registry import Registry
from ..pose.pose import register_pose
from .skeleton import Bone, Skeleton

ARCHETYPES: "Registry" = Registry("archetype")


# --------------------------------------------------------------------------- #
# Signature stance poses (body language). Registered once on import.
# --------------------------------------------------------------------------- #
_STANCES = {
    "arms_crossed": {"upper_arm_l": 218, "forearm_l": -118,
                     "upper_arm_r": 142, "forearm_r": 118, "head": 0},
    "hands_clasped": {"upper_arm_l": 203, "forearm_l": 34,
                      "upper_arm_r": 157, "forearm_r": -34},
    "hand_on_hip": {"upper_arm_r": 126, "forearm_r": 74,
                    "upper_arm_l": 196, "forearm_l": -6},
    "power_stance": {"upper_arm_l": 214, "forearm_l": 8,
                     "upper_arm_r": 146, "forearm_r": -8},
}
for _n, _p in _STANCES.items():
    register_pose(_n, _p, overwrite=True)


@dataclass
class Archetype:
    id: str
    name: str
    shape: str                       # "round" | "square" | "triangle"
    # proportions (fractions of the figure unit U)
    head_radius: float = 0.19
    spine: float = 0.32
    arm_upper: float = 0.205
    arm_fore: float = 0.195
    thigh: float = 0.255
    shin: float = 0.250
    stance: float = 14.0             # leg splay (deg); width of the base
    lean: float = 0.0                # sideways spine attitude (deg)
    # build (limb/torso thickness, shoulder width, belly) — drives the look
    build: dict = field(default_factory=lambda: {
        "limb": 0.065, "torso": 0.12, "shoulder": 0.17, "belly": 0.0})
    # identity
    palette: str = "classic"
    parts: dict = field(default_factory=dict)
    base_pose: str = "stand"
    base_expression: str = "happy"
    hands: dict = field(default_factory=dict)
    head_scale: float = 1.0

    def to_design_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "archetype": self.id,
            "palette": self.palette, "parts": dict(self.parts),
            "build": dict(self.build), "base_pose": self.base_pose,
            "base_expression": self.base_expression, "hands": dict(self.hands),
            "head_scale": self.head_scale,
        }


def parametric_skeleton(a: Archetype) -> Skeleton:
    """Build a skeleton sized by an archetype — the silhouette differentiator."""
    s = Skeleton(name=a.id, head_radius=a.head_radius)
    head_len = a.head_radius * 0.9
    st = a.stance
    s.add(Bone("spine", None, a.spine, a.lean, kind="limb", width=1.0))
    s.add(Bone("head", "spine", head_len, 0.0, "tip", "head"))
    s.add(Bone("upper_arm_l", "spine", a.arm_upper, 193.0, "tip"))
    s.add(Bone("forearm_l", "upper_arm_l", a.arm_fore, -6.0, "tip"))
    s.add(Bone("upper_arm_r", "spine", a.arm_upper, 167.0, "tip"))
    s.add(Bone("forearm_r", "upper_arm_r", a.arm_fore, 6.0, "tip"))
    s.add(Bone("thigh_l", "spine", a.thigh, 180 + st, "base"))
    s.add(Bone("shin_l", "thigh_l", a.shin, -st * 0.7, "tip"))
    s.add(Bone("thigh_r", "spine", a.thigh, 180 - st, "base"))
    s.add(Bone("shin_r", "thigh_r", a.shin, st * 0.7, "tip"))
    return s


def get_archetype(name: str) -> Archetype:
    return ARCHETYPES.get(name)


# --------------------------------------------------------------------------- #
# The founding cast — six personalities with deliberately distinct silhouettes.
# --------------------------------------------------------------------------- #
def _register():
    cast = [
        Archetype(
            "hero", "The Hero", shape="triangle",
            head_radius=0.155, spine=0.40, arm_upper=0.23, arm_fore=0.21,
            thigh=0.33, shin=0.31, stance=13, lean=-2,
            build={"limb": 0.064, "torso": 0.13, "shoulder": 0.27, "belly": 0.0},
            palette="blue", base_pose="power_stance", base_expression="determined",
            hands={"l": "fist", "r": "fist"},
            parts={"head": "round", "hair": "flattop", "brows": "thick",
                   "eyes": "cartoon", "mouth": "default", "feet": "boot"}),
        Archetype(
            "kid", "The Kid", shape="round",
            head_radius=0.30, spine=0.20, arm_upper=0.135, arm_fore=0.125,
            thigh=0.155, shin=0.15, stance=18, lean=1, head_scale=1.0,
            build={"limb": 0.078, "torso": 0.12, "shoulder": 0.12, "belly": 0.14},
            palette="red", base_pose="wave", base_expression="excited",
            hands={"l": "open_hand", "r": "wave"},
            parts={"head": "round", "hair": "tuft", "brows": "thin",
                   "eyes": "round", "mouth": "wide", "feet": "shoe"}),
        Archetype(
            "brute", "The Brute", shape="square",
            head_radius=0.15, spine=0.30, arm_upper=0.215, arm_fore=0.165,
            thigh=0.165, shin=0.145, stance=21, lean=2,
            build={"limb": 0.098, "torso": 0.185, "shoulder": 0.34, "belly": 0.14},
            palette="green", base_pose="arms_crossed", base_expression="angry",
            hands={"l": "fist", "r": "fist"},
            parts={"head": "square", "hair": "buzz", "brows": "thick",
                   "eyes": "cartoon", "mouth": "default", "feet": "boot"}),
        Archetype(
            "sage", "The Sage", shape="triangle",
            head_radius=0.165, spine=0.40, arm_upper=0.25, arm_fore=0.23,
            thigh=0.345, shin=0.325, stance=8, lean=5,
            build={"limb": 0.042, "torso": 0.085, "shoulder": 0.14, "belly": 0.0},
            palette="grey", base_pose="hands_clasped", base_expression="thinking",
            hands={"l": "four_finger", "r": "four_finger"},
            parts={"head": "egg", "hair": "mop", "brows": "flat",
                   "eyes": "sleepy", "mouth": "small", "feet": "shoe"}),
        Archetype(
            "clerk", "The Clerk", shape="square",
            head_radius=0.19, spine=0.31, arm_upper=0.18, arm_fore=0.17,
            thigh=0.255, shin=0.245, stance=6, lean=4,
            build={"limb": 0.048, "torso": 0.10, "shoulder": 0.12, "belly": 0.02},
            palette="classic", base_pose="hands_clasped", base_expression="nervous",
            hands={"l": "four_finger", "r": "four_finger"},
            parts={"head": "round", "hair": "swoosh", "brows": "thin",
                   "eyes": "cartoon", "mouth": "small", "feet": "shoe",
                   "accessory": "glasses"}),
        Archetype(
            "diva", "The Diva", shape="round",
            head_radius=0.18, spine=0.35, arm_upper=0.205, arm_fore=0.195,
            thigh=0.335, shin=0.315, stance=11, lean=-3,
            build={"limb": 0.05, "torso": 0.11, "shoulder": 0.16, "belly": 0.0},
            palette="pink", base_pose="hand_on_hip", base_expression="smirk",
            hands={"l": "four_finger", "r": "four_finger"},
            parts={"head": "round", "hair": "ponytail", "brows": "thin",
                   "eyes": "anime", "mouth": "default", "feet": "shoe"}),
    ]
    for a in cast:
        ARCHETYPES.register(a.id, a, overwrite=True)


_register()
