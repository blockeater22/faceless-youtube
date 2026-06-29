"""The Procedural World Simulation Engine.

The bridge between *story understanding* and *cinematic direction*. It consumes
a semantic Scene Graph (``narrative.SceneSpec``), resolves its requirements
against the Asset Intelligence Engine (``registry``), and instantiates a fully
specified **World Graph** in the spatial foundation (``stage``): every object
positioned/rotated/scaled/layered/parented, with anchors, collision, interaction
zones, a navigation graph, lighting, and environmental-storytelling parameters.

It never generates images and never uses hardcoded coordinate templates — worlds
are *composed* from constraint-based layout over reusable assets, seeded for
unlimited variation. Output is structured data the renderer/Cinematic Engine
consume.

Entry point: :func:`build_world`.
"""
from .schema import (WorldObject, InteractionZone, NavNode, NavGraph,
                     LightSource, WorldGraph, SCHEMA_VERSION)
from .builder import build_world, SemanticWorldBuilder
from .rooms import generate_room, ROOM_GENERATORS, Room
from .validate import validate_world

__all__ = [
    "WorldObject", "InteractionZone", "NavNode", "NavGraph", "LightSource",
    "WorldGraph", "SCHEMA_VERSION", "build_world", "SemanticWorldBuilder",
    "generate_room", "ROOM_GENERATORS", "Room", "validate_world",
]
