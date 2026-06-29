"""Intent Graph construction — the intermediate "why/what/feel" representation.

Turns understanding into a typed knowledge graph *before* any scene is planned,
so the planner (and later Director/Cinematic/Psychology engines) reason over
intent, not prose. Nodes carry confidence; edges carry meaning (feels/wants/
fears/serves).
"""
from __future__ import annotations

from . import schema as S
from .planner import scene_function

_VISUAL_BY_EMOTION = {
    "nervous": ["sweaty hands", "fidgeting feet"], "anxious": ["restless glances"],
    "sad": ["slumped shoulders"], "excited": ["wide gestures"],
    "angry": ["clenched fists"], "confident": ["open posture"],
    "scared": ["stepping back"], "confused": ["head scratch", "head tilt"],
    "proud": ["chin up"], "embarrassed": ["covering face"],
}
_FEAR_BY_EMOTION = {"nervous": "failure", "anxious": "the unknown",
                    "scared": "danger", "embarrassed": "judgement"}
_ENTRY_VERBS = ("enter", "entered", "walk", "walked", "open", "opened",
                "approach", "approached", "step", "stepped")


def build_intent_graph(scene_seg, analysis, characters: dict, index: int = 0,
                       total: int = 1) -> S.IntentGraph:
    g = S.IntentGraph(scene_index=index)
    present = [n for n in characters
              if n in scene_seg.text or any(b.speaker == n for b in scene_seg.beats)]

    # narrative function + audience emotion + theme/stakes (scene framing)
    g.add(S.NARRATIVE_FUNCTION, scene_function(index, total), 0.7)
    g.add(S.AUDIENCE_EMOTION, analysis.viewer_emotion.value,
          analysis.viewer_emotion.confidence)
    if analysis.theme.value:
        g.add(S.THEME, analysis.theme.value, analysis.theme.confidence)
    if analysis.stakes.value == "high":
        g.add(S.STAKES, "high stakes", analysis.stakes.confidence)
    if analysis.conflict.value:
        g.add(S.CONFLICT, analysis.conflict.value, analysis.conflict.confidence)

    # per-character intent
    for name in present:
        c = characters[name]
        cn = g.add(S.CHARACTER, name, 0.8, {"role": c.role.value})
        emo = g.add(S.EMOTION, c.current_emotion.value,
                    c.current_emotion.confidence, {"character": name})
        g.link(cn, "feels", emo)
        if c.goal.value:
            gn = g.add(S.GOAL, c.goal.value, c.goal.confidence, {"character": name})
            g.link(cn, "wants", gn)
        fear = _FEAR_BY_EMOTION.get(c.current_emotion.value)
        if fear:
            fn = g.add(S.FEAR, fear, 0.5, {"character": name})
            g.link(cn, "fears", fn)
        for vis in _VISUAL_BY_EMOTION.get(c.current_emotion.value, []):
            vn = g.add(S.VISUAL, vis, 0.55, {"character": name})
            g.link(emo, "shows", vn)

    # comedy opportunity
    if analysis.humor.value > 0.3 or "awkward" in scene_seg.text.lower():
        g.add(S.COMEDY, "awkward beat", min(0.8, 0.4 + analysis.humor.value))

    # retention opportunity (hooks / hesitation before key actions)
    low = scene_seg.text.lower()
    if index == 0:
        g.add(S.RETENTION, "open with a hook", 0.6)
    if any(v in low for v in _ENTRY_VERBS):
        g.add(S.RETENTION, "pause before entering", 0.6)

    # education opportunity
    if analysis.genre.value == "education":
        g.add(S.EDUCATION, "explain with a visual metaphor", 0.6)
    return g


def extract_intent(text: str, analyzer: str = "heuristic") -> S.IntentGraph:
    """Convenience: full understanding of ``text`` collapsed to one IntentGraph."""
    from .engine import understand_story
    u = understand_story(text, analyzer=analyzer)
    merged = S.IntentGraph(scene_index=-1)
    for g in u.intent_graphs:
        for n in g.nodes:
            merged.nodes.append(n)
        merged.edges.extend(g.edges)
    return merged
