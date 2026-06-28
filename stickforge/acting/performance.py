"""Beat-based performance generation.

A performance is a list of :class:`Beat` s — units of *intention*, not motion.
The compiler lays them out in time and bakes in the acting principles:

  * think before you act — a ``think`` beat inserts a held pause with the eyes
    drifting up before the next move;
  * anticipation — ``react`` beats ease in with a coil-back ("anticipate");
  * timing — each emotion's ``tempo`` stretches/compresses its beat;
  * eye acting — gaze is keyed per beat (and ``look`` beats move only the eyes).

It emits a plain :class:`~stickforge.animation.clip.AnimationClip`, so the rest
of the pipeline (scene, renderer, export) is unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..animation.clip import AnimationClip
from ..expression.expression import get_expression
from .emotion import get_emotion


@dataclass
class Beat:
    emotion: str = "neutral"
    dur: float = 1.5
    kind: str = "act"            # act | react | think | look | hold
    look: tuple | None = None    # (pupil_x, pupil_y) for look/think beats
    text: str = ""               # optional subtitle / staging note


def compile_performance(beats: list[Beat], *, loop: bool = False) -> AnimationClip:
    poses: list[dict] = []
    exprs: list[dict] = []
    hands: list[dict] = []
    offs: list[dict] = []

    def key(t, prof, pose_ease):
        poses.append({"t": round(t, 3), "pose": prof.body_pose(), "ease": pose_ease})
        f = prof.face()
        exprs.append({"t": round(t, 3), "expr": f, "ease": "ease_out"})
        hands.append({"t": round(t, 3), "l": prof.hands[0], "r": prof.hands[1]})
        offs.append({"t": round(t, 3), "value": list(prof.offset), "ease": pose_ease})
        return f

    t = 0.0
    prev_face = key(t, get_emotion("neutral"), "ease_in_out")   # ease from rest

    for b in beats:
        prof = get_emotion(b.emotion)
        if b.kind == "think":
            think = get_emotion("thinking")
            f = think.face()
            if b.look:
                f["pupil_x"], f["pupil_y"] = b.look
            # land the thinking pose quickly, then HOLD it (the pause)
            poses.append({"t": round(t, 3), "pose": think.body_pose(), "ease": "ease_out"})
            exprs.append({"t": round(t, 3), "expr": f, "ease": "ease_out"})
            hands.append({"t": round(t, 3), "l": "four_finger", "r": "four_finger"})
            hold = round(t + b.dur * 0.82, 3)
            poses.append({"t": hold, "pose": think.body_pose(), "ease": "linear"})
            exprs.append({"t": hold, "expr": f, "ease": "linear"})
            prev_face = f
            t += b.dur
        elif b.kind == "look":
            f = dict(prev_face)
            if b.look:
                f["pupil_x"], f["pupil_y"] = b.look
            exprs.append({"t": round(t, 3), "expr": f, "ease": "ease_out"})
            prev_face = f
            t += b.dur
        else:                                          # act | react | hold
            ease = "anticipate" if b.kind == "react" else "ease_in_out"
            d = b.dur / max(0.25, prof.tempo)
            prev_face = key(t, prof, ease)
            t += d

    return AnimationClip.from_spec(
        {"duration": round(t, 3), "loop": loop, "poses": poses,
         "expressions": exprs, "hands": hands, "offset": offs}, "performance")


def perform(beats: list[Beat], **kw) -> AnimationClip:
    return compile_performance(beats, **kw)


def emotion_clip(emotion: str, dur: float = 2.6, loop: bool = True) -> AnimationClip:
    """A looping idle that simply *holds* an emotion (idle life adds the rest)."""
    prof = get_emotion(emotion)
    f = prof.face()
    return AnimationClip.from_spec({
        "duration": dur, "loop": loop,
        "poses": [{"t": 0, "pose": prof.body_pose()},
                  {"t": dur, "pose": prof.body_pose()}],
        "expressions": [{"t": 0, "expr": f}, {"t": dur, "expr": f}],
        "hands": [{"t": 0, "l": prof.hands[0], "r": prof.hands[1]}],
        "offset": [{"t": 0, "value": list(prof.offset)},
                   {"t": dur, "value": list(prof.offset)}],
    }, f"emotion_{emotion}")
