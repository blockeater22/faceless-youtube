"""SemanticWorldBuilder — orchestrates the full pipeline.

    SceneSpec ──▶ storytelling ──▶ room ──▶ shell ──▶ props (constraint-placed,
    registry-resolved) ──▶ decoration ──▶ characters ──▶ zones ──▶ navigation
    ──▶ lighting ──▶ weather ──▶ optimize ──▶ validate ──▶ WorldGraph
"""
from __future__ import annotations

import random

from ..core.geometry import Vec2
from ..stage import Layer
from .lighting import build_lighting
from .navigation import build_nav
from .optimize import optimize
from .placement import DecorationEngine, PropPlacementEngine, METER
from .rooms import generate_room
from .schema import WorldGraph, WorldObject
from .storytelling import derive
from .validate import validate_world
from .weather import build_weather
from .zones import generate_zones

_POS_FRAC = {"left": -0.30, "center": 0.0, "right": 0.30,
             "far_left": -0.42, "far_right": 0.42}


class SemanticWorldBuilder:
    def build(self, spec, registry=None, seed: int = 0) -> WorldGraph:
        if registry is None:
            from ..registry import default_registry
            registry = default_registry()
        rng = random.Random((seed * 2654435761) ^ (hash(spec.id) & 0xFFFFFFFF))

        story = derive(spec)
        room = generate_room(spec, story, rng)
        world = WorldGraph(scene_id=spec.id)
        world.story = story
        world.bounds = {"width": round(room.width, 1), "floor_y": room.floor_y,
                        "wall_y": room.wall_y, "left": round(room.left, 1),
                        "right": round(room.right, 1), "indoor": room.indoor,
                        "env": room.env, "room_type": room.room_type,
                        "door_x": room.door_x, "window_x": room.window_x}

        shell = self._shell(spec, room)
        props, floor_iv = PropPlacementEngine().place(spec, room, story, registry, rng)
        decor = DecorationEngine().add(spec, room, story, props, floor_iv, registry, rng)
        chars = self._characters(spec, room)
        world.objects = shell + props + decor + chars

        world.zones = generate_zones(room, world.objects, spec)
        world.nav = build_nav(room, world.zones, world.objects)
        world.lights = build_lighting(room, spec, story, world.objects)
        world.weather = build_weather(spec, room)
        world.stats = optimize(world, room, seed)
        validate_world(world)
        return world

    def _shell(self, spec, room) -> list[WorldObject]:
        out = [WorldObject(id=f"{spec.id}.floor", semantic_role="floor",
                           role="shell", surface="floor",
                           position=Vec2(0, room.floor_y),
                           bbox=[room.width, 20], solid=False, layer=Layer.GROUND)]
        if room.indoor:
            out.append(WorldObject(id=f"{spec.id}.wall", semantic_role="wall",
                                   role="shell", surface="wall",
                                   position=Vec2(0, room.wall_y),
                                   bbox=[room.width, room.wall_height], solid=False,
                                   layer=Layer.BACKGROUND))
            out.append(WorldObject(id=f"{spec.id}.ceiling", semantic_role="ceiling",
                                   role="shell", surface="ceiling",
                                   position=Vec2(0, room.floor_y - room.wall_height),
                                   bbox=[room.width, 20], solid=False,
                                   layer=Layer.BACKGROUND))
        return out

    def _characters(self, spec, room) -> list[WorldObject]:
        out = []
        present = spec.characters or []
        n = len(present)
        for i, c in enumerate(present):
            frac = _POS_FRAC.get(c.get("position", "center"),
                                 (i - (n - 1) / 2) * 0.25)
            out.append(WorldObject(
                id=f"{spec.id}.char.{c['name']}",
                semantic_role=f"character:{c['name']}", role="character",
                surface="floor", position=Vec2(room.width * frac, room.floor_y),
                bbox=[1.0 * METER, 2.6 * METER], solid=False, layer=Layer.ACTORS,
                facing=1 if c.get("facing") != "left" else -1,
                data={"emotion": c.get("emotion", "neutral"),
                      "action": c.get("action", "idle"),
                      "role": c.get("role", "character")}))
        return out


def build_world(spec, registry=None, seed: int = 0) -> WorldGraph:
    """Build a fully-instantiated World Graph from a semantic Scene Graph."""
    return SemanticWorldBuilder().build(spec, registry=registry, seed=seed)
