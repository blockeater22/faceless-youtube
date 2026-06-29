"""Versioned cognitive contracts — the stable data every engine consumes.

These structures are the product of "understanding". They are deliberately
open/extensible (dict payloads + ``extra``) so the schema can evolve for a
decade without breaking consumers, and every inferred value is wrapped in
:class:`Inf` (value + confidence + evidence) so quality can improve (e.g. via an
LLM provider) without changing the shape.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

SCHEMA_VERSION = 1


@dataclass
class Inf:
    """An inferred value with a confidence in [0,1] and supporting evidence."""
    value: Any
    confidence: float = 0.5
    evidence: str = ""

    def to_dict(self) -> dict:
        return {"value": self.value, "confidence": round(self.confidence, 3),
                "evidence": self.evidence}


# --------------------------------------------------------------------------- #
# Story-level understanding
# --------------------------------------------------------------------------- #
@dataclass
class StoryAnalysis:
    story_type: Inf = field(default_factory=lambda: Inf("narrative", 0.3))
    genre: Inf = field(default_factory=lambda: Inf("slice_of_life", 0.3))
    tone: Inf = field(default_factory=lambda: Inf("neutral", 0.3))
    theme: Inf = field(default_factory=lambda: Inf("", 0.2))
    setting: Inf = field(default_factory=lambda: Inf("unspecified", 0.2))
    time: Inf = field(default_factory=lambda: Inf("day", 0.3))
    weather: Inf = field(default_factory=lambda: Inf("clear", 0.3))
    mood: Inf = field(default_factory=lambda: Inf("neutral", 0.3))
    conflict: Inf = field(default_factory=lambda: Inf("", 0.2))
    resolution: Inf = field(default_factory=lambda: Inf("", 0.2))
    stakes: Inf = field(default_factory=lambda: Inf("low", 0.3))
    urgency: Inf = field(default_factory=lambda: Inf("low", 0.3))
    viewer_emotion: Inf = field(default_factory=lambda: Inf("interest", 0.3))
    humor: Inf = field(default_factory=lambda: Inf(0.0, 0.4))      # 0..1
    emotional_arc: list = field(default_factory=list)             # [(label, emotion)]
    tags: list = field(default_factory=list)
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        out = {k: (v.to_dict() if isinstance(v, Inf) else v)
               for k, v in self.__dict__.items() if k != "extra"}
        out.update(self.extra)
        return out


@dataclass
class CharacterModel:
    name: str
    role: Inf = field(default_factory=lambda: Inf("character", 0.3))
    personality: list = field(default_factory=list)
    goal: Inf = field(default_factory=lambda: Inf("", 0.2))
    motivation: Inf = field(default_factory=lambda: Inf("", 0.2))
    current_emotion: Inf = field(default_factory=lambda: Inf("neutral", 0.3))
    desired_emotion: Inf = field(default_factory=lambda: Inf("happy", 0.3))
    confidence_level: float = 0.5     # the character's self-confidence (0..1)
    stress: float = 0.3
    energy: float = 0.6
    relationships: dict = field(default_factory=dict)   # name -> Inf(relation)
    props: list = field(default_factory=list)
    arc: Inf = field(default_factory=lambda: Inf("flat", 0.3))
    mentions: int = 0
    first_scene: int = 0
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name, "role": self.role.to_dict(),
            "personality": self.personality, "goal": self.goal.to_dict(),
            "motivation": self.motivation.to_dict(),
            "current_emotion": self.current_emotion.to_dict(),
            "desired_emotion": self.desired_emotion.to_dict(),
            "confidence": self.confidence_level, "stress": self.stress,
            "energy": self.energy,
            "relationships": {k: v.to_dict() for k, v in self.relationships.items()},
            "props": self.props, "arc": self.arc.to_dict(),
            "mentions": self.mentions, "first_scene": self.first_scene,
            **self.extra,
        }


# --------------------------------------------------------------------------- #
# Intent graph (a typed knowledge graph of why/what/feel)
# --------------------------------------------------------------------------- #
# node types
GOAL, FEAR, CONFLICT, MOTIVATION = "goal", "fear", "conflict", "motivation"
EMOTION, AUDIENCE_EMOTION = "emotion", "audience_emotion"
NARRATIVE_FUNCTION = "narrative_function"
COMEDY, VISUAL, RETENTION, EDUCATION = ("comedy_opportunity", "visual_opportunity",
                                        "retention_opportunity", "education_opportunity")
THEME, STAKES, SYMBOL, SUBTEXT = "theme", "stakes", "symbol", "subtext"
CHARACTER = "character"


@dataclass
class IntentNode:
    id: str
    type: str
    label: str
    confidence: float = 0.5
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"id": self.id, "type": self.type, "label": self.label,
                "confidence": round(self.confidence, 3), "data": self.data}


@dataclass
class IntentGraph:
    scene_index: int = 0
    nodes: list = field(default_factory=list)
    edges: list = field(default_factory=list)      # (src_id, rel, dst_id)

    def add(self, type: str, label: str, confidence: float = 0.5,
            data: dict | None = None, id: str | None = None) -> IntentNode:
        nid = id or f"{type}:{len(self.nodes)}"
        n = IntentNode(nid, type, label, confidence, data or {})
        self.nodes.append(n)
        return n

    def link(self, src: IntentNode | str, rel: str, dst: IntentNode | str) -> None:
        s = src.id if isinstance(src, IntentNode) else src
        d = dst.id if isinstance(dst, IntentNode) else dst
        self.edges.append((s, rel, d))

    def of_type(self, type: str) -> list[IntentNode]:
        return [n for n in self.nodes if n.type == type]

    def to_dict(self) -> dict:
        return {"scene_index": self.scene_index,
                "nodes": [n.to_dict() for n in self.nodes],
                "edges": [list(e) for e in self.edges]}


# --------------------------------------------------------------------------- #
# Segmentation (Scene -> Beat -> Action)
# --------------------------------------------------------------------------- #
@dataclass
class Action:
    text: str
    verb: str = ""
    subject: str = ""


@dataclass
class Beat:
    index: int
    text: str
    speaker: str | None = None
    emotion: str = "neutral"
    actions: list = field(default_factory=list)      # list[Action]
    kind: str = "action"                             # action | dialogue


@dataclass
class SceneSeg:
    index: int
    text: str
    heading: str = ""
    location_cue: str = ""
    time_cue: str = ""
    beats: list = field(default_factory=list)        # list[Beat]


@dataclass
class StorySegmentation:
    scenes: list = field(default_factory=list)        # list[SceneSeg]

    def to_dict(self) -> dict:
        return {"scenes": [{
            "index": s.index, "heading": s.heading,
            "location_cue": s.location_cue, "time_cue": s.time_cue,
            "beats": [{"index": b.index, "kind": b.kind, "speaker": b.speaker,
                       "emotion": b.emotion, "text": b.text,
                       "actions": [a.text for a in b.actions]} for b in s.beats],
        } for s in self.scenes]}


# --------------------------------------------------------------------------- #
# Scene Graph (the contract handed to World/Director/Cinematic engines)
# --------------------------------------------------------------------------- #
@dataclass
class SceneSpec:
    id: str
    schema_version: int = SCHEMA_VERSION
    metadata: dict = field(default_factory=dict)
    narrative: dict = field(default_factory=dict)         # function, summary
    intent: dict = field(default_factory=dict)            # IntentGraph.to_dict()
    environment: dict = field(default_factory=dict)       # location/room/indoor
    time: str = "day"
    weather: str = "clear"
    lighting: str = "soft"
    mood: str = "neutral"
    characters: list = field(default_factory=list)        # semantic char states
    spatial_layout: dict = field(default_factory=dict)    # marks: name->left/center/right
    camera_targets: list = field(default_factory=list)    # semantic shots
    prop_requirements: list = field(default_factory=list) # semantic queries (NOT assets)
    animation_notes: list = field(default_factory=list)
    dialogue_timing: list = field(default_factory=list)
    transitions: dict = field(default_factory=lambda: {"in": "cut", "out": "cut"})
    sound: list = field(default_factory=list)
    music: str = "neutral"
    effects: list = field(default_factory=list)
    quality_metrics: dict = field(default_factory=dict)
    validation: dict = field(default_factory=lambda: {"status": "unvalidated", "issues": []})
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        out = {k: v for k, v in self.__dict__.items() if k != "extra"}
        out.update(self.extra)
        return out
