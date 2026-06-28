"""Scene graph + a simple sequencing Timeline.

A :class:`Scene` places one or more :class:`Actor` s (a character + a clip) on a
background, under a camera, for a fixed duration. A :class:`Timeline` plays a
list of scenes back-to-back. Everything is resolved to render-ready state by
sampling at a global time — the renderer never mutates scene data.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..animation.clip import AnimationClip, Posing
from ..animation.procedural import apply_life, phase_for
from ..character.character import Character, build_character
from ..core.geometry import Vec2
from .camera import Camera


@dataclass
class Actor:
    character: Character
    clip: AnimationClip
    pos: tuple[float, float] = (0.5, 0.62)   # hip anchor, fractions of (W, H)
    unit_scale: float = 0.34                  # U as a fraction of min(W, H)
    start: float = 0.0                        # seconds into the scene
    life: float = 1.0
    facing: int = 1                           # +1 right, -1 flips horizontally
    id: str = "actor"

    def posing_at(self, scene_t: float) -> Posing:
        local = scene_t - self.start
        base = self.clip.sample(local)
        return apply_life(base, local, phase_for(self.id), self.life)


@dataclass
class Scene:
    id: str = "scene"
    duration: float = 3.0
    background: dict = field(default_factory=dict)
    actors: list[Actor] = field(default_factory=list)
    props: list[dict] = field(default_factory=list)
    camera: Camera = field(default_factory=Camera)
    caption: str = ""

    @classmethod
    def from_spec(cls, spec: dict, library=None) -> "Scene":
        """Build a scene from a JSON-style spec, resolving characters/clips.

        Actors reference a character (inline spec or library id via
        ``character``) and a clip (inline ``clip`` spec or library id via
        ``clip_id``).
        """
        actors: list[Actor] = []
        for a in spec.get("actors", []):
            char_src = a["character"]
            if isinstance(char_src, str) and library is not None:
                char_src = library.get(char_src)
            character = build_character(char_src, library)

            if "clip" in a:
                clip = AnimationClip.from_spec(a["clip"], a.get("id", "clip"))
            elif "clip_id" in a and library is not None:
                clip = AnimationClip.from_spec(library.get(a["clip_id"]).data,
                                               a["clip_id"])
            else:
                clip = AnimationClip(duration=spec.get("duration", 3.0))

            actors.append(Actor(
                character=character,
                clip=clip,
                pos=tuple(a.get("pos", (0.5, 0.62))),
                unit_scale=float(a.get("unit_scale", 0.34)),
                start=float(a.get("start", 0.0)),
                life=float(a.get("life", 1.0)),
                facing=int(a.get("facing", 1)),
                id=a.get("id", "actor"),
            ))

        return cls(
            id=spec.get("id", "scene"),
            duration=float(spec.get("duration", 3.0)),
            background=dict(spec.get("background", {})),
            actors=actors,
            props=list(spec.get("props", [])),
            camera=Camera.from_spec(spec.get("camera", {})),
            caption=spec.get("caption", ""),
        )


@dataclass
class Timeline:
    """Plays scenes sequentially; resolves a global time to (scene, local_t)."""

    scenes: list[Scene] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return sum(s.duration for s in self.scenes)

    def at(self, t: float) -> tuple[Scene, float]:
        acc = 0.0
        for s in self.scenes:
            if t < acc + s.duration or s is self.scenes[-1]:
                return s, t - acc
            acc += s.duration
        return self.scenes[-1], self.scenes[-1].duration
