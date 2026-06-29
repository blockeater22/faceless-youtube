"""World Graph contracts — the fully-instantiated, structured world.

A :class:`WorldGraph` is the output of the engine: world objects (each with a
transform, anchors, collision, semantic role, and an optional resolved asset id
— never a file path), interaction zones, a navigation graph, light sources, and
storytelling/optimization metadata. It converts to a ``stage.SceneGraph`` so the
renderer and Cinematic Engine operate on it directly.
"""
from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field

from ..core.geometry import Vec2
from ..stage import Layer, SceneGraph, Transform2D

SCHEMA_VERSION = 1


@dataclass
class WorldObject:
    id: str
    semantic_role: str                 # 'desk', 'chair', 'character:John', 'wall'
    role: str = "set"                  # focus | seat | set | decor | character | shell
    position: Vec2 = field(default_factory=lambda: Vec2(0.0, 0.0))
    rotation: float = 0.0
    scale: float = 1.0
    layer: int = Layer.MIDGROUND
    parent: str | None = None
    surface: str = "floor"
    bbox: list = field(default_factory=lambda: [1.0, 1.0])   # world units
    anchors: dict = field(default_factory=dict)
    asset_query: dict | None = None
    asset_id: str | None = None        # resolved from the registry (or None)
    solid: bool = True                 # blocks navigation?
    lit: bool = True
    lod: int = 0
    facing: int = 1
    data: dict = field(default_factory=dict)

    def interval(self) -> tuple[float, float]:
        half = self.bbox[0] * self.scale / 2.0
        return (self.position.x - half, self.position.x + half)

    def anchor_world(self, name: str) -> Vec2:
        a = self.anchors.get(name, [0.0, 0.0])
        return Vec2(self.position.x + a[0] * self.bbox[0] * self.scale,
                    self.position.y + a[1] * self.bbox[1] * self.scale)

    def to_dict(self) -> dict:
        return {"id": self.id, "semantic_role": self.semantic_role,
                "role": self.role, "position": [round(self.position.x, 1),
                round(self.position.y, 1)], "rotation": self.rotation,
                "scale": self.scale, "layer": int(self.layer),
                "parent": self.parent, "surface": self.surface,
                "bbox": self.bbox, "asset_id": self.asset_id,
                "asset_query": self.asset_query, "solid": self.solid,
                "lit": self.lit, "lod": self.lod, "facing": self.facing}


@dataclass
class InteractionZone:
    id: str
    kind: str                          # working | seating | conversation | entrance | path | camera_safe
    center: Vec2
    size: Vec2 = field(default_factory=lambda: Vec2(120.0, 120.0))
    tags: list = field(default_factory=list)
    capacity: int = 1

    def to_dict(self) -> dict:
        return {"id": self.id, "kind": self.kind,
                "center": [round(self.center.x, 1), round(self.center.y, 1)],
                "size": [self.size.x, self.size.y], "tags": self.tags,
                "capacity": self.capacity}


@dataclass
class NavNode:
    id: str
    position: Vec2
    kind: str = "waypoint"


class NavGraph:
    """A small weighted graph of walkable positions + Dijkstra pathfinding."""

    def __init__(self) -> None:
        self.nodes: dict[str, NavNode] = {}
        self.edges: dict[str, dict[str, float]] = {}

    def add(self, node: NavNode) -> NavNode:
        self.nodes[node.id] = node
        self.edges.setdefault(node.id, {})
        return node

    def link(self, a: str, b: str) -> None:
        if a in self.nodes and b in self.nodes:
            d = (self.nodes[a].position - self.nodes[b].position).length()
            self.edges[a][b] = d
            self.edges[b][a] = d

    def path(self, a: str, b: str) -> list[str]:
        if a not in self.nodes or b not in self.nodes:
            return []
        dist = {a: 0.0}
        prev: dict[str, str] = {}
        pq = [(0.0, a)]
        while pq:
            d, u = heapq.heappop(pq)
            if u == b:
                break
            if d > dist.get(u, math.inf):
                continue
            for v, w in self.edges.get(u, {}).items():
                nd = d + w
                if nd < dist.get(v, math.inf):
                    dist[v] = nd
                    prev[v] = u
                    heapq.heappush(pq, (nd, v))
        if b not in prev and a != b:
            return []
        out = [b]
        while out[-1] != a:
            out.append(prev[out[-1]])
        return list(reversed(out))

    def to_dict(self) -> dict:
        return {"nodes": {n: [round(v.position.x, 1), round(v.position.y, 1)]
                          for n, v in self.nodes.items()},
                "edges": {a: sorted(bs) for a, bs in self.edges.items()}}


@dataclass
class LightSource:
    id: str
    position: Vec2
    color: str = "#fff3da"
    intensity: float = 1.0
    kind: str = "key"                  # key | fill | ambient | practical

    def to_dict(self) -> dict:
        return {"id": self.id, "kind": self.kind,
                "position": [round(self.position.x, 1), round(self.position.y, 1)],
                "color": self.color, "intensity": round(self.intensity, 2)}


@dataclass
class WorldGraph:
    scene_id: str
    schema_version: int = SCHEMA_VERSION
    bounds: dict = field(default_factory=dict)          # room dimensions
    objects: list = field(default_factory=list)         # WorldObject
    zones: list = field(default_factory=list)           # InteractionZone
    nav: NavGraph = field(default_factory=NavGraph)
    lights: list = field(default_factory=list)          # LightSource
    weather: dict = field(default_factory=dict)
    story: dict = field(default_factory=dict)           # environmental storytelling
    validation: dict = field(default_factory=lambda: {"status": "unvalidated", "issues": []})
    stats: dict = field(default_factory=dict)

    def by_role(self, role: str) -> list[WorldObject]:
        return [o for o in self.objects if o.role == role]

    def find(self, semantic_role: str) -> WorldObject | None:
        return next((o for o in self.objects if o.semantic_role == semantic_role), None)

    def to_scene_graph(self) -> SceneGraph:
        """Project the world into the spatial scene graph for rendering."""
        g = SceneGraph()
        for o in self.objects:
            node = g.spawn(o.id, o.position, layer=o.layer,
                           content={"kind": "world_object", "object": o.to_dict()})
            node.transform = Transform2D.translate(o.position.x, o.position.y)
            node.anchors = {k: Vec2(v[0], v[1]) for k, v in o.anchors.items()}
        return g

    def to_dict(self) -> dict:
        return {"scene_id": self.scene_id, "schema_version": self.schema_version,
                "bounds": self.bounds,
                "objects": [o.to_dict() for o in self.objects],
                "zones": [z.to_dict() for z in self.zones],
                "nav": self.nav.to_dict(),
                "lights": [l.to_dict() for l in self.lights],
                "weather": self.weather, "story": self.story,
                "validation": self.validation, "stats": self.stats}
