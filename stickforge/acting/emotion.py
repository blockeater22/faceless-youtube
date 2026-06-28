"""The emotional state machine.

Each emotion is an :class:`EmotionProfile` that maps a feeling to the full body
of an acting choice — a silhouette-readable body pose, spine/head attitude, a
body-shift, hand state, plus timing and eye behaviour. Nothing here is random:
every value answers "what does this tell the audience?"

The body poses are registered here (so emotions read without a face), then each
profile composes a pose + a facial expression + eye bias + timing.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..core.registry import Registry
from ..pose.pose import register_pose, get_pose
from ..expression.expression import get_expression

EMOTIONS: "Registry" = Registry("emotion")


# --------------------------------------------------------------------------- #
# Silhouette-readable body poses for acting (arms/lean/head/stance/step).
# --------------------------------------------------------------------------- #
# Specific acting gestures NOT produced by the generative builder. (The builder
# owns the movement-derived stances: stand/idle/open_arms/reach_joy/lean_in/
# hands_chest/hand_on_hip/power_stance — see pose/builder.py.)
_ACTING_POSES = {
    "recoil":      {"spine": -9, "head": -7, "upper_arm_l": 232, "forearm_l": 24,
                    "upper_arm_r": 128, "forearm_r": -24, "thigh_r": 158,
                    "shin_r": 22},
    "slump":       {"head": 13, "spine": 3, "upper_arm_l": 199, "forearm_l": -3,
                    "upper_arm_r": 161, "forearm_r": 3},
    "hands_to_face": {"upper_arm_l": 156, "forearm_l": 74, "upper_arm_r": 204,
                      "forearm_r": -74, "head": 4},
    "step_back":   {"spine": -5, "thigh_r": 156, "shin_r": 24, "head": -3,
                    "upper_arm_l": 206, "upper_arm_r": 154},
    "aggressive":  {"upper_arm_l": 216, "forearm_l": -2, "upper_arm_r": 144,
                    "forearm_r": 2, "spine": 7, "head": 6, "thigh_l": 200,
                    "thigh_r": 160},
    "hand_on_chin": {"upper_arm_r": 110, "forearm_r": -135,
                     "upper_arm_l": 198, "forearm_l": -4},      # pondering
    "face_palm":   {"upper_arm_r": 78, "forearm_r": -158,
                    "upper_arm_l": 198, "forearm_l": -4},       # hand to forehead
    "arms_crossed": {"upper_arm_l": 218, "forearm_l": -118, "upper_arm_r": 142,
                     "forearm_r": 118, "head": 0},
    "hands_clasped": {"upper_arm_l": 203, "forearm_l": 34, "upper_arm_r": 157,
                      "forearm_r": -34},
}
# ensure the generative stances are registered (builder owns stand/open_arms/...)
from ..pose import builder as _builder        # noqa: E402  (registers on import)
_builder.register_generated_poses()
for _n, _p in _ACTING_POSES.items():
    register_pose(_n, _p, overwrite=True)


@dataclass
class EmotionProfile:
    emotion: str
    expression: str                  # existing facial expression name
    pose: str = "stand"              # body pose (silhouette-readable)
    head: float = 0.0                # extra head tilt (deg)
    lean: float = 0.0                # spine attitude (deg)
    offset: tuple = (0.0, 0.0)       # body shift (figure units)
    hands: tuple = ("four_finger", "four_finger")
    eye: tuple = (0.0, 0.0)          # gaze bias (pupil_x, pupil_y)
    blink_rate: float = 1.0          # multiplier on involuntary blinking
    idle_amp: float = 1.0            # idle/fidget amplitude
    tempo: float = 1.0               # >1 = quicker/lighter, <1 = slower/heavier

    def body_pose(self) -> dict:
        """Merge the base pose with this emotion's spine/head attitude."""
        pose = dict(get_pose(self.pose))
        if self.lean:
            pose["spine"] = pose.get("spine", 0.0) + self.lean
        if self.head:
            pose["head"] = pose.get("head", 0.0) + self.head
        return pose

    def face(self) -> dict:
        """Full facial params with the emotion's eye bias applied."""
        f = dict(get_expression(self.expression))
        f["pupil_x"] = self.eye[0]
        f["pupil_y"] = self.eye[1]
        return f


def get_emotion(name: str) -> EmotionProfile:
    if name in EMOTIONS:
        return EMOTIONS.get(name)
    return EMOTIONS.get("neutral")


def _register():
    profiles = [
        EmotionProfile("neutral", "neutral", "stand", blink_rate=1.0),
        EmotionProfile("happy", "happy", "open_arms", head=-2, eye=(0, -0.05),
                       hands=("open_hand", "open_hand"), idle_amp=1.0, tempo=1.05),
        EmotionProfile("excited", "excited", "reach_joy", lean=-3, offset=(0, -0.05),
                       hands=("open_hand", "open_hand"), blink_rate=1.3,
                       idle_amp=1.5, tempo=1.25),
        EmotionProfile("nervous", "nervous", "hands_clasped", head=6, lean=4,
                       eye=(0.35, 0.05), blink_rate=1.7, idle_amp=1.4, tempo=1.1),
        EmotionProfile("confident", "proud", "hand_on_hip", head=-4, lean=-3,
                       blink_rate=0.8, idle_amp=0.8, tempo=0.9),
        EmotionProfile("embarrassed", "nervous", "hands_to_face", head=7,
                       eye=(0.45, 0.2), blink_rate=1.2, idle_amp=1.1, tempo=1.0),
        EmotionProfile("curious", "surprised", "lean_in", head=6, eye=(0.3, -0.25),
                       blink_rate=0.9, idle_amp=1.0, tempo=1.05),
        EmotionProfile("confused", "confused", "hand_on_chin", head=8, eye=(0.25, -0.35),
                       hands=("four_finger", "four_finger"), blink_rate=1.0,
                       idle_amp=1.0, tempo=0.95),
        EmotionProfile("suspicious", "smirk", "arms_crossed", lean=-4, head=5,
                       eye=(0.55, 0.0), blink_rate=0.7, idle_amp=0.8, tempo=0.9),
        EmotionProfile("shocked", "shocked", "recoil", head=-6, offset=(0, -0.02),
                       hands=("open_hand", "open_hand"), blink_rate=0.5,
                       idle_amp=1.6, tempo=1.4),
        EmotionProfile("angry", "angry", "aggressive",
                       hands=("fist", "fist"), blink_rate=0.7, idle_amp=1.1,
                       tempo=1.1),
        EmotionProfile("frustrated", "exhausted", "face_palm", head=8,
                       blink_rate=1.0, idle_amp=1.0, tempo=1.0),
        EmotionProfile("sad", "sad", "slump", head=13, offset=(0, 0.03),
                       eye=(0, 0.4), blink_rate=0.6, idle_amp=0.7, tempo=0.8),
        EmotionProfile("hopeful", "happy", "hands_chest", head=-8, eye=(0, -0.45),
                       blink_rate=0.9, idle_amp=0.9, tempo=0.95),
        EmotionProfile("determined", "determined", "power_stance", lean=4, head=-2,
                       hands=("fist", "fist"), blink_rate=0.8, idle_amp=0.9,
                       tempo=1.0),
        EmotionProfile("relieved", "happy", "hands_chest", head=-5, lean=-2,
                       offset=(0, 0.02), eye=(0, -0.1), blink_rate=1.2,
                       idle_amp=0.8, tempo=0.85),
        EmotionProfile("anxious", "nervous", "hands_clasped", head=8, lean=5,
                       eye=(0.3, 0.2), blink_rate=1.8, idle_amp=1.4, tempo=1.1),
        EmotionProfile("thinking", "thinking", "hand_on_chin", head=7, eye=(0.3, -0.5),
                       blink_rate=0.8, idle_amp=0.9, tempo=0.9),
    ]
    for p in profiles:
        EMOTIONS.register(p.emotion, p, overwrite=True)


_register()
