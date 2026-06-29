"""Character understanding — persistent intelligent entities, not name strings.

Detects named characters (dialogue speakers + proper nouns), then infers role,
goal, motivation, current emotion, self-confidence/stress, and relationships
from the surrounding text. Output is a dict of :class:`CharacterModel`s that
persist across scenes (keyed by name).
"""
from __future__ import annotations

import re

from .lexicon import EMOTION_WORDS, GOAL_CUES, ROLE_CUES
from .schema import CharacterModel, Inf, StorySegmentation

_STOP_NAMES = {
    "The", "A", "An", "He", "She", "It", "They", "We", "You", "I", "His",
    "Her", "Their", "But", "And", "Then", "When", "After", "Before", "Later",
    "Meanwhile", "Suddenly", "Inside", "Outside", "Today", "Tomorrow", "Monday",
    "Int", "Ext", "Scene", "Mr", "Mrs", "Ms", "Dr", "Of", "In", "On", "At",
    "This", "That", "There", "Here", "What", "Why", "How", "So", "As", "Now",
    "Finally", "Soon", "Once", "Every", "Some", "No", "Yes", "Okay",
}


def _proper_nouns(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    # capitalized words not at the very start of a sentence
    for m in re.finditer(r"(?<![.!?]\s)(?<!^)\b([A-Z][a-z]{2,})\b", text):
        w = m.group(1)
        if w in _STOP_NAMES:
            continue
        counts[w] = counts.get(w, 0) + 1
    # also sentence-initial names that recur elsewhere
    for m in re.finditer(r"\b([A-Z][a-z]{2,})\b", text):
        w = m.group(1)
        if w not in _STOP_NAMES and counts.get(w, 0) >= 1:
            counts[w] += 0
    return counts


def _role_for(name: str, text: str) -> Inf:
    low = text.lower()
    for role, cues in ROLE_CUES.items():
        if any(c in low for c in cues):
            return Inf(role, 0.55, f"cue:{role}")
    return Inf("character", 0.3)


def _emotion_near(name: str, sentences: list[str]) -> Inf:
    for s in sentences:
        if name in s:
            low = s.lower()
            for w, emo in EMOTION_WORDS.items():
                if re.search(rf"\b{re.escape(w)}", low):
                    return Inf(emo, 0.7, w)
    return Inf("neutral", 0.3)


def _goal_near(name: str, sentences: list[str]) -> Inf:
    for s in sentences:
        if name in s and any(re.search(rf"\b{c}\b", s.lower()) for c in GOAL_CUES):
            return Inf(s.strip(), 0.55, "goal-cue")
    return Inf("", 0.2)


def extract_characters(seg: StorySegmentation) -> dict[str, CharacterModel]:
    text = " ".join(s.text for s in seg.scenes)
    sentences = [b.text for sc in seg.scenes for b in sc.beats]
    speakers = {b.speaker for sc in seg.scenes for b in sc.beats if b.speaker}

    counts = _proper_nouns(text)
    names = set(speakers) | {n for n, c in counts.items() if c >= 1}
    if not names:
        names = {"Protagonist"}

    chars: dict[str, CharacterModel] = {}
    for name in sorted(names):
        emo = _emotion_near(name, sentences)
        conf = {"nervous": 0.25, "anxious": 0.2, "scared": 0.2, "sad": 0.3,
                "confident": 0.85, "proud": 0.8, "determined": 0.8}.get(
                    emo.value, 0.5)
        stress = {"nervous": 0.8, "anxious": 0.85, "scared": 0.9,
                  "angry": 0.7}.get(emo.value, 0.35)
        first = next((sc.index for sc in seg.scenes
                      if name in sc.text or any(b.speaker == name for b in sc.beats)), 0)
        chars[name] = CharacterModel(
            name=name, role=_role_for(name, text),
            current_emotion=emo, goal=_goal_near(name, sentences),
            confidence_level=conf, stress=stress,
            mentions=counts.get(name, 0) + (5 if name in speakers else 0),
            first_scene=first)
    _relationships(chars, seg)
    return chars


def _relationships(chars: dict[str, CharacterModel], seg: StorySegmentation) -> None:
    names = list(chars)
    for sc in seg.scenes:
        present = [n for n in names if n in sc.text or
                   any(b.speaker == n for b in sc.beats)]
        for i, a in enumerate(present):
            for b in present[i + 1:]:
                rel = "acquaintance"
                ra, rb = chars[a].role.value, chars[b].role.value
                if {ra, rb} & {"interviewer", "boss", "teacher"}:
                    rel = "professional"
                if {ra, rb} & {"friend"}:
                    rel = "friend"
                chars[a].relationships.setdefault(b, Inf(rel, 0.5, "co-occurrence"))
                chars[b].relationships.setdefault(a, Inf(rel, 0.5, "co-occurrence"))


def extract_relationships(chars: dict[str, CharacterModel]) -> list[tuple]:
    out = []
    for name, c in chars.items():
        for other, rel in c.relationships.items():
            if name < other:
                out.append((name, other, rel.value, rel.confidence))
    return out
