"""Story segmentation — Scene -> Beat -> Action, with metadata at every level.

Heuristic boundaries: explicit headings (``INT./EXT.``, ``Scene N``,
``(location)``), location/time shifts, and transition cues ("Later,",
"Meanwhile,", "The next day"). Beats are sentences or dialogue lines; actions
are clauses with a guessed verb/subject. The LLM provider can replace this with
a smarter segmenter emitting the same :class:`StorySegmentation`.
"""
from __future__ import annotations

import re

from .lexicon import EMOTION_WORDS, SETTING_CUES, TIME_CUES
from .schema import Action, Beat, SceneSeg, StorySegmentation

_TRANSITION = re.compile(r"^(later|meanwhile|the next day|that (?:evening|night|"
                         r"morning)|suddenly|afterwards|hours later|years later)\b",
                         re.I)
_HEADING = re.compile(r"^(int\.|ext\.|scene\s+\d+|#)", re.I)
_SPEAKER = re.compile(r"^([A-Z][\w'-]{0,20})\s*:\s*(.+)$")
_SENT = re.compile(r"[^.!?]+[.!?]?")


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT.findall(text) if s.strip()]


def _find(text: str, table: dict) -> str:
    low = text.lower()
    for key, val in table.items():
        if key in low:
            return val if isinstance(val, str) else key
    return ""


def _emotion(text: str) -> str:
    low = text.lower()
    for w, emo in EMOTION_WORDS.items():
        if re.search(rf"\b{re.escape(w)}", low):
            return emo
    if low.rstrip().endswith("?"):
        return "curious"
    if low.rstrip().endswith("!"):
        return "excited"
    return "neutral"


def _actions(text: str) -> list[Action]:
    out = []
    for clause in re.split(r",| and | then ", text):
        clause = clause.strip()
        if not clause:
            continue
        verb = ""
        for w in re.findall(r"[a-zA-Z]+", clause.lower()):
            if w.endswith("ed") or w.endswith("ing") or w in (
                    "walk", "run", "sit", "stand", "open", "enter", "look"):
                verb = w
                break
        subj = ""
        m = re.search(r"\b([A-Z][a-z]+)\b", clause)
        if m:
            subj = m.group(1)
        out.append(Action(clause, verb, subj))
    return out


def segment_story(text: str) -> StorySegmentation:
    seg = StorySegmentation()
    cur = SceneSeg(index=0, text="")
    beat_i = 0

    def push_scene():
        nonlocal cur
        if cur.text.strip() or cur.beats:
            cur.location_cue = _find(cur.text, {k: k for k in SETTING_CUES})
            cur.time_cue = _find(cur.text, TIME_CUES)
            seg.scenes.append(cur)

    raw_lines = [ln.strip() for ln in text.splitlines()]
    started = False
    for line in raw_lines:
        if not line or line.startswith("#") and len(line) < 3:
            continue
        is_heading = bool(_HEADING.match(line)) or (
            line.startswith("(") and line.endswith(")"))
        new_scene = is_heading or bool(_TRANSITION.match(line))
        if new_scene and started:
            push_scene()
            cur = SceneSeg(index=len(seg.scenes), text="")
        started = True
        if is_heading:
            cur.heading = line.strip("()# ")
            cur.text += " " + line
            continue
        # split a paragraph/line into beats
        sp = _SPEAKER.match(line)
        if sp:
            cur.text += " " + sp.group(2)
            cur.beats.append(Beat(beat_i, sp.group(2), speaker=sp.group(1),
                                  emotion=_emotion(sp.group(2)),
                                  actions=_actions(sp.group(2)), kind="dialogue"))
            beat_i += 1
        else:
            for s in _sentences(line):
                cur.text += " " + s
                # a sentence-internal transition can also split scenes
                if _TRANSITION.match(s) and started and cur.beats:
                    push_scene()
                    cur = SceneSeg(index=len(seg.scenes), text=" " + s)
                cur.beats.append(Beat(beat_i, s, emotion=_emotion(s),
                                      actions=_actions(s), kind="action"))
                beat_i += 1
    push_scene()
    if not seg.scenes:                       # always at least one scene
        seg.scenes.append(SceneSeg(index=0, text=text))
    return seg
