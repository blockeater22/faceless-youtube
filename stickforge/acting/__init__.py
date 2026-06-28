"""The Acting Engine — performance generation, not animation playback.

Where `animation/` plays keyframes, `acting/` generates *intention*: an
emotional state machine maps each emotion to body language, facial acting, eye
behaviour, and timing; a beat compiler turns a sequence of intentions
(think → react → act) into an :class:`~stickforge.animation.clip.AnimationClip`
with anticipation and "think before you speak" pauses.

Design goals (the success criteria): characters appear to think before acting,
body language reads emotion in silhouette, eyes carry part of the story, and a
scene is understandable with the sound muted.
"""
from .emotion import EmotionProfile, EMOTIONS, get_emotion
from .performance import Beat, compile_performance, perform, emotion_clip

__all__ = [
    "EmotionProfile", "EMOTIONS", "get_emotion",
    "Beat", "compile_performance", "perform", "emotion_clip",
]
