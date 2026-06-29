"""Blocking Graph contracts — the performance contract handed to the Director.

A :class:`BlockingGraph` holds, per scene: each actor's :class:`BlockingMark`
(where they stand and the posture/status that put them there), a time-ordered
list of :class:`PerformanceBeat` s (move/look/gesture/speak/react/pause/emotion/
interact — every beat carries a *motivation* note), the interpersonal distance
relationships, and validation. Versioned and extensible (dict payloads).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..core.geometry import Vec2

SCHEMA_VERSION = 1


@dataclass
class BlockingMark:
    actor: str
    zone: str = ""                 # the interaction zone claimed
    position: Vec2 = field(default_factory=lambda: Vec2(0.0, 0.0))
    facing: int = 1
    posture: str = "neutral"       # open | closed | small | aggressive | neutral
    status: float = 0.5            # social/power status that drove the choice 0..1
    body_language: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"actor": self.actor, "zone": self.zone,
                "position": [round(self.position.x, 1), round(self.position.y, 1)],
                "facing": self.facing, "posture": self.posture,
                "status": round(self.status, 2), "body_language": self.body_language}


@dataclass
class PerformanceBeat:
    t: float
    dur: float
    actor: str
    kind: str                      # enter|move|settle|pause|look|gesture|emotion|speak|react|sit|interact
    data: dict = field(default_factory=dict)
    priority: int = 5              # 1 highest; the Director uses this to choose focus
    note: str = ""                 # the directorial motivation ("why")

    def to_dict(self) -> dict:
        return {"t": round(self.t, 3), "dur": round(self.dur, 3),
                "actor": self.actor, "kind": self.kind, "data": self.data,
                "priority": self.priority, "note": self.note}


@dataclass
class BlockingGraph:
    scene_id: str
    schema_version: int = SCHEMA_VERSION
    duration: float = 0.0
    marks: dict = field(default_factory=dict)        # name -> BlockingMark
    beats: list = field(default_factory=list)        # PerformanceBeat (sorted by t)
    relationships: list = field(default_factory=list)  # (a, b, distance, relation)
    validation: dict = field(default_factory=lambda: {"status": "unvalidated", "issues": []})
    stats: dict = field(default_factory=dict)

    def actor_beats(self, name: str) -> list:
        return [b for b in self.beats if b.actor == name]

    def of_kind(self, kind: str) -> list:
        return [b for b in self.beats if b.kind == kind]

    def sort(self) -> None:
        self.beats.sort(key=lambda b: (b.t, b.priority))

    def to_dict(self) -> dict:
        return {"scene_id": self.scene_id, "schema_version": self.schema_version,
                "duration": round(self.duration, 3),
                "marks": {n: m.to_dict() for n, m in self.marks.items()},
                "beats": [b.to_dict() for b in self.beats],
                "relationships": self.relationships,
                "validation": self.validation, "stats": self.stats}
