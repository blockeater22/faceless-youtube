"""Rendering: pluggable backends that turn a Scene at time t into pixels/markup.

The SVG backend ships in-tree and has zero dependencies. New backends (raster,
GL, a different art style) register themselves in :data:`RENDERERS`.
"""

from ..core.registry import Registry
from .config import RenderConfig
from .svg import SvgRenderer, ATTACHMENTS
from .illustrated import IllustratedRenderer

RENDERERS: "Registry" = Registry("renderer")
RENDERERS.register("illustrated", IllustratedRenderer)   # house style (default)
RENDERERS.register("svg", SvgRenderer)                   # legacy line-stickman

DEFAULT_RENDERER = "illustrated"

__all__ = ["RenderConfig", "SvgRenderer", "IllustratedRenderer",
           "RENDERERS", "DEFAULT_RENDERER", "ATTACHMENTS"]
