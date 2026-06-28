"""SceneNode — a node in the scene graph.

A node has a local :class:`Transform2D`, a parent, children, a draw ``layer``, a
``parallax`` factor, an optional ``content`` payload (what to draw), and named
**anchors** (local points other nodes/cameras can reference, e.g. an actor's
"hand" or a table's "surface"). World transforms compose down the tree.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..core.geometry import Vec2
from .layers import Layer, PARALLAX
from .transform import Transform2D


@dataclass
class SceneNode:
    name: str = "node"
    transform: Transform2D = field(default_factory=Transform2D.identity)
    layer: int = Layer.ACTORS
    parallax: float | None = None          # None -> use the layer default
    content: dict | None = None            # {"kind": "...", ...}
    anchors: dict[str, Vec2] = field(default_factory=dict)
    children: list["SceneNode"] = field(default_factory=list)
    parent: "SceneNode | None" = field(default=None, repr=False)

    # -- tree ------------------------------------------------------------- #
    def add(self, child: "SceneNode") -> "SceneNode":
        child.parent = self
        self.children.append(child)
        return child

    def world_transform(self) -> Transform2D:
        t = self.transform
        p = self.parent
        while p is not None:
            t = p.transform @ t
            p = p.parent
        return t

    def world_pos(self) -> Vec2:
        return self.world_transform().apply(Vec2(0.0, 0.0))

    def anchor(self, name: str) -> Vec2:
        """World position of a named anchor (origin if unknown)."""
        local = self.anchors.get(name, Vec2(0.0, 0.0))
        return self.world_transform().apply(local)

    @property
    def effective_parallax(self) -> float:
        if self.parallax is not None:
            return self.parallax
        return PARALLAX.get(self.layer, 1.0)

    # -- traversal -------------------------------------------------------- #
    def walk(self):
        """Yield this node then all descendants (depth-first)."""
        yield self
        for c in self.children:
            yield from c.walk()

    def render_order(self) -> list["SceneNode"]:
        """All nodes with content, sorted back-to-front by layer (stable)."""
        nodes = [n for n in self.walk() if n.content is not None]
        return sorted(nodes, key=lambda n: n.layer)
