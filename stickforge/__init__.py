"""stickforge — a modular, data-driven stickman animation platform.

The engine is built as a stack of independent layers, each usable on its own
and extensible through registries (never hardcoded):

    core         pure math: geometry, easing, keyframe interpolation, registry
    assets       the Asset Library: typed, taggable, searchable, pack-loadable
    character    hierarchical Rig (forward kinematics) + Character assembly
    pose         named, blendable joint poses
    expression   blendable facial-feature emotions
    animation    keyframed clips + procedural "life" (breath/blink/sway)
    scene        scene graph, camera, and a multi-actor timeline
    render       pluggable renderers (SVG backend ships in-tree)
    export       frames -> self-contained HTML player / video (ffmpeg, optional)

Design rules (enforced throughout):
  * Nothing about a character, pose, expression, or animation is hardcoded into
    the renderer — it all flows from data that can live in JSON asset packs.
  * Every catalogue (asset types, renderers, exporters, easings) is a registry,
    so plugins add capabilities without editing the core.
  * The core has zero third-party dependencies; rasterization/video are
    optional backends that degrade gracefully when their tools are absent.
"""

__version__ = "0.1.0"

from .core.geometry import Vec2  # noqa: F401
from .core.registry import Registry  # noqa: F401

__all__ = ["Vec2", "Registry", "__version__"]
