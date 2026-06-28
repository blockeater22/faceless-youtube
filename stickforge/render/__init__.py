"""Rendering: pluggable backends that turn a Scene at time t into pixels/markup.

The SVG backend ships in-tree and has zero dependencies. New backends (raster,
GL, a different art style) register themselves in :data:`RENDERERS`.
"""

from ..core.registry import Registry
from .config import RenderConfig
from .svg import SvgRenderer, ATTACHMENTS

RENDERERS: "Registry" = Registry("renderer")
RENDERERS.register("svg", SvgRenderer)

__all__ = ["RenderConfig", "SvgRenderer", "RENDERERS", "ATTACHMENTS"]
