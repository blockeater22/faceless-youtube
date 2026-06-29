"""The cognitive pipeline facade — the public services other engines call.

    understand_story(text) -> StoryUnderstanding   (analysis + characters +
                                                    segmentation + intent graphs)
    plan(understanding)    -> [SceneSpec]           (validated Scene Graphs)

Downstream engines (World, Director, Cinematic, Psychology, Universe) consume
``SceneSpec``/``IntentGraph`` only — never the original English.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .analyzer import get_analyzer
from .characters import extract_characters
from .intent import build_intent_graph
from .planner import plan_scene, infer_emotion_curve
from .schema import StoryAnalysis, StorySegmentation, SceneSpec, IntentGraph
from .segmentation import segment_story
from .validate import validate_scene_graph


@dataclass
class StoryUnderstanding:
    text: str
    analysis: StoryAnalysis
    characters: dict
    segmentation: StorySegmentation
    intent_graphs: list = field(default_factory=list)   # one per scene

    @property
    def scene_count(self) -> int:
        return len(self.segmentation.scenes)

    def to_dict(self) -> dict:
        return {
            "analysis": self.analysis.to_dict(),
            "characters": {n: c.to_dict() for n, c in self.characters.items()},
            "segmentation": self.segmentation.to_dict(),
            "intent_graphs": [g.to_dict() for g in self.intent_graphs],
        }


def understand_story(text: str, analyzer: str = "heuristic") -> StoryUnderstanding:
    seg = segment_story(text)
    chars = extract_characters(seg)
    analysis = get_analyzer(analyzer).analyze(text, seg)
    total = len(seg.scenes)
    graphs = [build_intent_graph(sc, analysis, chars, sc.index, total)
              for sc in seg.scenes]
    return StoryUnderstanding(text, analysis, chars, seg, graphs)


def plan(understanding: StoryUnderstanding, validate: bool = True) -> list[SceneSpec]:
    out: list[SceneSpec] = []
    total = understanding.scene_count
    for sc in understanding.segmentation.scenes:
        g = understanding.intent_graphs[sc.index]
        spec = plan_scene(g, understanding.analysis, sc,
                          understanding.characters, sc.index, total)
        if validate:
            validate_scene_graph(spec)
        out.append(spec)
    return out


def summarize_story(understanding: StoryUnderstanding) -> dict:
    a = understanding.analysis
    return {
        "genre": a.genre.value, "tone": a.tone.value, "setting": a.setting.value,
        "time": a.time.value, "weather": a.weather.value, "mood": a.mood.value,
        "theme": a.theme.value, "viewer_emotion": a.viewer_emotion.value,
        "characters": list(understanding.characters),
        "scenes": understanding.scene_count,
        "emotion_curve": infer_emotion_curve(understanding),
    }
