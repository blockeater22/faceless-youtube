"""Performance planners + scene rhythm.

Each planner is a reusable service returning :class:`PerformanceBeat` s with a
motivation note; ``plan_scene_rhythm`` sequences them into an intentional
timeline (enter → settle → look → pause → speak/gesture → react …) with timing
from emotion tempo and line length. Reuses ``acting`` (gesture vocab, emotion
tempo) and ``world.nav`` (motivated movement paths).
"""
from __future__ import annotations

from ..core.geometry import Vec2
from ..voice.engine import estimate_duration
from .schema import PerformanceBeat

_GESTURE = {"angry": "fist", "determined": "fist", "confident": "point",
            "happy": "open_hand", "excited": "wave", "proud": "open_hand",
            "nervous": "four_finger", "confused": "four_finger",
            "curious": "point", "shocked": "open_hand"}
_REACTIONS = {"shocked", "confused", "surprised", "suspicious", "scared"}


def _emo_of(spec, name: str) -> str:
    for c in spec.characters or []:
        if c["name"] == name:
            return c.get("emotion", "neutral")
    return "neutral"


def plan_emotional_performance(spec, marks) -> list[PerformanceBeat]:
    """Set each actor's emotional body language at the top of the scene."""
    out = []
    for name, m in marks.items():
        emo = _emo_of(spec, name)
        out.append(PerformanceBeat(0.0, 0.5, name, "emotion",
                                   {"emotion": emo, "body_language": m.body_language},
                                   priority=4,
                                   note=f"establish {emo} ({m.posture} posture)"))
    return out


def plan_movements(world, marks, state=None, base_t: float = 0.0) -> list[PerformanceBeat]:
    """Motivated entrances/repositioning over the navigation graph."""
    out = []
    entrance = next((z for z in world.zones if z.kind == "entrance"), None)
    for name, m in marks.items():
        start = None
        if state and name in state and state[name].position is not None:
            start = state[name].position
        elif entrance is not None:
            start = entrance.center
        if start is None:
            continue
        if (start - m.position).length() < 70:
            continue
        motive = {"small": "enters hesitantly, lingering near the door",
                  "open": "strides in confidently",
                  "aggressive": "marches in"}.get(m.posture, "walks in")
        path = _nav_path(world, start, m.position)
        out.append(PerformanceBeat(base_t, 1.3, name, "enter",
                                   {"from": [round(start.x, 1), round(start.y, 1)],
                                    "to": [round(m.position.x, 1), round(m.position.y, 1)],
                                    "path": path}, priority=3, note=motive))
    return out


def _nav_path(world, a: Vec2, b: Vec2) -> list[str]:
    def nearest(p):
        return min(world.nav.nodes, key=lambda n: (world.nav.nodes[n].position - p).length(),
                   default=None)
    na, nb = nearest(a), nearest(b)
    return world.nav.path(na, nb) if na and nb else []


def plan_interactions(world, marks, base_t: float = 0.0) -> list[PerformanceBeat]:
    """Reserve and use nearby interactive objects (sit on a chair, etc.)."""
    out, reserved = [], set()
    seats = [o for o in world.objects if o.semantic_role in ("chair", "sofa")]
    for name, m in marks.items():
        seat = min((s for s in seats if s.id not in reserved),
                   key=lambda s: abs(s.position.x - m.position.x), default=None)
        if seat and abs(seat.position.x - m.position.x) < 220:
            reserved.add(seat.id)
            out.append(PerformanceBeat(base_t, 0.9, name, "interact",
                                       {"object": seat.id, "action": "sit",
                                        "zone": "seating"}, priority=3,
                                       note=f"sits ({seat.semantic_role})"))
    return out


def plan_eye_contact(marks, spec, base_t: float = 0.0, dur: float = 1.0) -> list[PerformanceBeat]:
    """Establishing gaze: mutual contact, or attention to the focus."""
    out = []
    names = list(marks)
    for name in names:
        emo = _emo_of(spec, name)
        others = [n for n in names if n != name]
        if others:
            mode = "glance" if emo in ("nervous", "anxious", "scared", "embarrassed") \
                else "eye_contact"
            out.append(PerformanceBeat(base_t, dur, name, "look",
                                       {"target": others[0], "mode": mode},
                                       priority=4,
                                       note="seeks eye contact" if mode == "eye_contact"
                                       else "glances, then looks away"))
        else:
            out.append(PerformanceBeat(base_t, dur, name, "look",
                                       {"target": "focus", "mode": "observe"},
                                       priority=4, note="takes in the space"))
    return out


def plan_gestures(spec, marks, base_t: float = 0.0) -> list[PerformanceBeat]:
    """Emotion-motivated gestures (one per actor, at base_t)."""
    out = []
    for name in marks:
        g = _GESTURE.get(_emo_of(spec, name))
        if g:
            out.append(PerformanceBeat(base_t, 1.0, name, "gesture",
                                       {"gesture": g}, note="emotional gesture"))
    return out


def plan_scene_rhythm(world, spec, marks, state=None) -> tuple[list, float]:
    """Sequence all planners into an intentional performance timeline."""
    beats: list[PerformanceBeat] = []
    beats += plan_emotional_performance(spec, marks)

    moves = plan_movements(world, marks, state, base_t=0.0)
    beats += moves
    t = 1.4 if moves else 0.3
    for name, m in marks.items():
        beats.append(PerformanceBeat(t, 0.4, name, "settle", {"zone": m.zone},
                                     note="settles into position"))
    t += 0.4

    beats += plan_eye_contact(marks, spec, base_t=t, dur=1.0)
    t += 1.0
    inter = plan_interactions(world, marks, base_t=t)
    beats += inter
    if inter:
        t += 1.0

    dlg = spec.dialogue_timing
    if dlg:
        for line in dlg:
            spk = line.get("speaker") or next(iter(marks), None)
            text = line.get("text", "")
            emo = line.get("emotion", "neutral")
            dur = estimate_duration(text)
            if emo in _REACTIONS:
                beats.append(PerformanceBeat(t, 0.6, spk, "pause", {},
                                             note="beat of hesitation before reacting"))
                t += 0.6
            beats.append(PerformanceBeat(t, dur, spk, "speak",
                                         {"text": text, "emotion": emo},
                                         priority=2, note="delivers the line"))
            g = _GESTURE.get(emo)
            if g:
                beats.append(PerformanceBeat(t, min(dur, 1.0), spk, "gesture",
                                             {"gesture": g}, note=f"{emo} gesture"))
            for ln in [n for n in marks if n != spk]:
                beats.append(PerformanceBeat(t, dur, ln, "look",
                                             {"target": spk, "mode": "attentive"},
                                             note="listens"))
                beats.append(PerformanceBeat(t + dur * 0.65, 0.4, ln, "react",
                                             {"emotion": emo}, priority=3,
                                             note="reacts to the line"))
            t += dur
    else:
        for name in marks:
            emo = _emo_of(spec, name)
            beats.append(PerformanceBeat(t, 1.0, name, "look",
                                         {"target": "focus", "mode": "observe"},
                                         note="take in the moment"))
            g = _GESTURE.get(emo)
            if g:
                beats.append(PerformanceBeat(t + 0.6, 1.0, name, "gesture",
                                             {"gesture": g}, note=f"{emo} gesture"))
        t += 2.2

    beats.sort(key=lambda b: (b.t, b.priority))
    return beats, round(t, 3)
