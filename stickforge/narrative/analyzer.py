"""The inference provider seam.

``Analyzer`` is the interface that turns text + segmentation into a
:class:`StoryAnalysis`. The shipped :class:`HeuristicAnalyzer` uses the
lexicons; an ``LLMAnalyzer`` can register into :data:`ANALYZERS` later and emit
the *same* structure with higher confidence — no consumer changes. This is the
"swap the brain's IQ without touching the body" boundary.
"""
from __future__ import annotations

import re

from ..core.registry import Registry
from . import lexicon as lx
from .schema import Inf, StoryAnalysis, StorySegmentation

ANALYZERS: "Registry" = Registry("analyzer")


class Analyzer:
    name = "base"

    def analyze(self, text: str, seg: StorySegmentation) -> StoryAnalysis:
        raise NotImplementedError


def _best(text: str, table: dict[str, list[str]]):
    """(key, hit_count) for the table entry with the most keyword hits."""
    low = text.lower()
    best, best_hits = "", 0
    for key, words in table.items():
        hits = sum(1 for w in words if w in low)
        if hits > best_hits:
            best, best_hits = key, hits
    return best, best_hits


def _conf(hits: int, base: float = 0.4, step: float = 0.12, cap: float = 0.9) -> float:
    return min(cap, base + step * hits) if hits else 0.3


def _find(text: str, table: dict[str, str]):
    low = text.lower()
    for key, val in table.items():
        if key in low:
            return val, key
    return "", ""


class HeuristicAnalyzer(Analyzer):
    name = "heuristic"

    def analyze(self, text: str, seg: StorySegmentation) -> StoryAnalysis:
        a = StoryAnalysis()
        low = text.lower()

        genre, gh = _best(text, lx.GENRE_CUES)
        if genre:
            a.genre = Inf(genre, _conf(gh), "genre cues")
            a.story_type = Inf({"education": "educational", "comedy": "comedy",
                                "documentary": "documentary"}.get(genre, "narrative"),
                               _conf(gh))
        tone, th = _best(text, lx.TONE_CUES)
        if tone:
            a.tone = Inf(tone, _conf(th), "tone cues")

        setting, skey = _find(text, {k: v[0] for k, v in lx.SETTING_CUES.items()})
        if setting:
            env, room, indoor = lx.SETTING_CUES[skey][1:]
            a.setting = Inf(setting, 0.65, skey)
            a.extra["environment"] = Inf(env, 0.65, skey)
            a.extra["room_type"] = Inf(room, 0.6, skey)
            a.extra["indoor"] = Inf(indoor, 0.6, skey)

        tval, tkey = _find(text, lx.TIME_CUES)
        if tval:
            a.time = Inf(tval, 0.7, tkey)
        wval, wkey = _find(text, lx.WEATHER_CUES)
        if wval:
            a.weather = Inf(wval, 0.7, wkey)

        # mood = dominant emotion; ties broken by earliest occurrence (POV)
        emo_counts: dict[str, int] = {}
        emo_first: dict[str, int] = {}
        for w, emo in lx.EMOTION_WORDS.items():
            m = re.search(rf"\b{re.escape(w)}", low)
            if m:
                n = len(re.findall(rf"\b{re.escape(w)}", low))
                emo_counts[emo] = emo_counts.get(emo, 0) + n
                emo_first[emo] = min(emo_first.get(emo, 10 ** 9), m.start())
        if emo_counts:
            mood = max(emo_counts, key=lambda e: (emo_counts[e], -emo_first[e]))
            a.mood = Inf(mood, _conf(emo_counts[mood]), "emotion words")

        conflict_hits = [c for c in lx.CONFLICT_CUES if re.search(rf"\b{c}\b", low)]
        if conflict_hits:
            a.conflict = Inf(conflict_hits[0], _conf(len(conflict_hits)),
                             ",".join(conflict_hits[:3]))
        comedy_hits = sum(1 for c in lx.COMEDY_CUES if c in low)
        a.humor = Inf(min(1.0, comedy_hits * 0.3 + (0.4 if genre == "comedy" else 0)),
                      _conf(comedy_hits))
        stakes_hits = sum(1 for c in lx.STAKES_CUES if c in low)
        a.stakes = Inf("high" if stakes_hits else "low", _conf(stakes_hits))
        urgency_hits = sum(1 for c in lx.URGENCY_CUES if c in low)
        a.urgency = Inf("high" if urgency_hits else "low", _conf(urgency_hits))

        a.viewer_emotion = Inf(_viewer_emotion(genre, a.mood.value), 0.5, "genre+mood")
        a.theme = Inf(_theme(genre, conflict_hits), 0.4, "inferred")
        a.emotional_arc = [(f"scene_{sc.index}", _scene_emotion(sc))
                           for sc in seg.scenes]
        a.tags = sorted({genre, tone, a.mood.value} - {""})
        return a


def _viewer_emotion(genre: str, mood: str) -> str:
    return {"comedy": "amusement", "drama": "empathy", "motivation": "inspiration",
            "education": "curiosity", "action": "excitement",
            "romance": "warmth", "documentary": "curiosity"}.get(
        genre, {"nervous": "empathy", "sad": "empathy", "excited": "delight",
                "angry": "tension"}.get(mood, "interest"))


def _theme(genre: str, conflict_hits: list[str]) -> str:
    if genre == "motivation":
        return "perseverance"
    if "fear" in conflict_hits or "doubt" in conflict_hits:
        return "overcoming self-doubt"
    return {"comedy": "the comedy of everyday life", "romance": "connection",
            "education": "learning"}.get(genre, "")


def _scene_emotion(sc) -> str:
    counts: dict[str, int] = {}
    for b in sc.beats:
        counts[b.emotion] = counts.get(b.emotion, 0) + 1
    counts.pop("neutral", None)
    return max(counts, key=counts.get) if counts else "neutral"


ANALYZERS.register("heuristic", HeuristicAnalyzer())


def get_analyzer(name: str = "heuristic") -> Analyzer:
    return ANALYZERS.get(name) if name in ANALYZERS else ANALYZERS.get("heuristic")
