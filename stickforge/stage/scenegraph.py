"""SceneGraph — the root container + lookup helpers.

Thin wrapper over a root :class:`SceneNode`: build a tree, find nodes/anchors by
name, and enumerate renderables back-to-front. The renderer consumes this; the
World/Director engines populate it.
"""
from __future__ import annotations

from ..core.geometry import Vec2
from .layers import Layer
from .node import SceneNode
from .transform import Transform2D


class SceneGraph:
    def __init__(self) -> None:
        self.root = SceneNode(name="root", layer=Layer.SKY)

    def add(self, node: SceneNode, parent: SceneNode | None = None) -> SceneNode:
        (parent or self.root).add(node)
        return node

    def spawn(self, name: str, world_pos: Vec2, layer: int = Layer.ACTORS,
              content: dict | None = None, parallax: float | None = None,
              anchors: dict | None = None) -> SceneNode:
        node = SceneNode(name=name,
                         transform=Transform2D.translate(world_pos.x, world_pos.y),
                         layer=layer, content=content, parallax=parallax,
                         anchors=anchors or {})
        self.root.add(node)
        return node

    def find(self, name: str) -> SceneNode | None:
        for n in self.root.walk():
            if n.name == name:
                return n
        return None

    def anchor(self, node_name: str, anchor_name: str) -> Vec2 | None:
        node = self.find(node_name)
        return node.anchor(anchor_name) if node else None

    def renderables(self) -> list[SceneNode]:
        return self.root.render_order()
