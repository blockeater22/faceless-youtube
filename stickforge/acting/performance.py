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
    gaze: tuple | None = None    # (pupil_x, pupil_y) eye-contact override
    talk: bool = True            # generate lip-sync visemes when this beat has text


def compile_performance(beats: list[Beat], *, loop: bool = False,
                        return_marks: bool = False, fixed_timing: bool = False):
    """Compile beats into a clip. With ``return_marks=True`` also returns a list
    of ``{"start","end","kind","emotion","text"}`` so callers (e.g. the Story
    Engine) can align subtitles to the tempo-scaled beat timing."""
    poses: list[dict] = []
    exprs: list[dict] = []
    hands: list[dict] = []
    offs: list[dict] = []
    idle: list[dict] = []

    def key(t, prof, pose_ease):
        poses.append({"t": round(t, 3), "pose": prof.body_pose(), "ease": pose_ease})
        f = prof.face()
        exprs.append({"t": round(t, 3), "expr": f, "ease": "ease_out"})
        hands.append({"t": round(t, 3), "l": prof.hands[0], "r": prof.hands[1]})
        offs.append({"t": round(t, 3), "value": list(prof.offset), "ease": pose_ease})
        idle.append({"t": round(t, 3), "amp": prof.idle_amp, "blink": prof.blink_rate})
        return f

    t = 0.0
    marks: list[dict] = []
    prev_face = key(t, get_emotion("neutral"), "ease_in_out")   # ease from rest

    for b in beats:
        start = t
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
            idle.append({"t": round(t, 3), "amp": think.idle_amp, "blink": think.blink_rate})
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
            d = b.dur if fixed_timing else b.dur / max(0.25, prof.tempo)
            prev_face = key(t, prof, ease)
            if b.gaze:                                  # eye contact / staging
                prev_face["pupil_x"], prev_face["pupil_y"] = b.gaze
            if b.text and b.talk:                       # lip-sync visemes
                from ..voice.lipsync import visemes_for
                for ft, mo, mc in visemes_for(b.text, d):
                    vf = dict(prev_face)
                    vf["mouth_open"] = mo
                    vf["mouth_curve"] = 0.5 * vf.get("mouth_curve", 0.0) + mc
                    exprs.append({"t": round(t + ft, 3), "expr": vf, "ease": "linear"})
            t += d
        marks.append({"start": round(start, 3), "end": round(t, 3),
                      "kind": b.kind, "emotion": b.emotion, "text": b.text})

    clip = AnimationClip.from_spec(
        {"duration": round(t, 3), "loop": loop, "poses": poses,
         "expressions": exprs, "hands": hands, "offset": offs, "idle": idle},
        "performance")
    return (clip, marks) if return_marks else clip


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
        "idle": [{"t": 0, "amp": prof.idle_amp, "blink": prof.blink_rate}],
    }, f"emotion_{emotion}")
