"""Performance continuity — actors persist across scenes (ECS-style state).

Carries each character's last position/facing, emotional momentum, energy/
fatigue, relationships, and owned objects, so performances never reset
unnaturally between scenes. ``update_character_state`` folds a finished Blocking
Graph back into the store.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..core.geometry import Vec2


@dataclass
class CharacterState:
    name: str
    position: Vec2 | None = None
    facing: int = 1
    emotion: str = "neutral"
    energy: float = 1.0
    fatigue: float = 0.0
    relationships: dict = field(default_factory=dict)
    owns: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"name": self.name,
                "position": None if self.position is None
                else [round(self.position.x, 1), round(self.position.y, 1)],
                "facing": self.facing, "emotion": self.emotion,
                "energy": round(self.energy, 2), "fatigue": round(self.fatigue, 2),
                "owns": self.owns}


def update_character_state(state: dict, graph, spec) -> dict:
    """Fold a finished scene's blocking into the persistent state store."""
    state = dict(state or {})
    for name, mark in graph.marks.items():
        cs = state.get(name) or CharacterState(name)
        cs.position = mark.position
        cs.facing = mark.facing
        cs.emotion = next((c.get("emotion", cs.emotion)
                           for c in (spec.characters or []) if c["name"] == name),
                          cs.emotion)
        cs.energy = max(0.2, cs.energy - 0.05)          # mild fatigue accrual
        cs.fatigue = min(1.0, cs.fatigue + 0.05)
        for b in graph.actor_beats(name):
            if b.kind == "interact" and b.data.get("object"):
                if b.data["object"] not in cs.owns:
                    cs.owns.append(b.data["object"])
        state[name] = cs
    return state
