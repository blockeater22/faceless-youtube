"""The spatial foundation — the layer every future engine builds on.

Nothing here knows about pixels until the very last step. Content lives in
**world space**; a :class:`SceneGraph` of :class:`SceneNode` s positions it with
composable :class:`Transform2D` s and named :class:`anchors`; a
:class:`Camera2D` is the *only* thing that projects world space to screen
pixels, honouring per-:mod:`layer` parallax.

    World space ──(scene graph: nodes + transforms + anchors + layers)──>
    Camera2D ──(project)──> screen pixels

Engines layer on top without re-deriving geometry:
  * World Engine     adds environment/prop nodes on background/ground layers.
  * Cinematic Engine drives the Camera2D (framing, shots, moves).
  * Director/Universe place and reference nodes by name and anchor.
"""
from .transform import Transform2D
from .layers import Layer, PARALLAX
from .world import World, Viewport, REFERENCE
from .node import SceneNode
from .camera import Camera2D
from .scenegraph import SceneGraph

__all__ = [
    "Transform2D", "Layer", "PARALLAX", "World", "Viewport", "REFERENCE",
    "SceneNode", "Camera2D", "SceneGraph",
]
