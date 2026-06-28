"""Sample a Scene or Timeline into a sequence of SVG frames."""
from __future__ import annotations

from pathlib import Path

from ..render import RENDERERS, DEFAULT_RENDERER
from ..render.config import RenderConfig


def _duration(target) -> float:
    return target.duration


def render_frames(target, config: RenderConfig | None = None,
                  fps: int = 24, backend: str = DEFAULT_RENDERER) -> list[str]:
    """Render a Scene or Timeline to a list of SVG document strings.

    ``backend`` selects a renderer from the registry (default: the illustrated
    house style; ``"svg"`` is the legacy line-stickman). A Timeline (anything
    exposing ``.at(t) -> (scene, local_t)``) is sampled per-scene so each
    scene's camera/clips run on their own local clock; a bare Scene is sampled
    on a single clock.
    """
    renderer = RENDERERS.get(backend)(config or RenderConfig())
    dur = _duration(target)
    n = max(1, int(round(dur * fps)))
    frames: list[str] = []
    is_timeline = hasattr(target, "at") and hasattr(target, "scenes")
    for i in range(n):
        t = i / fps
        if is_timeline:
            scene, local = target.at(t)
            frames.append(renderer.render_frame(scene, local, i))
        else:
            frames.append(renderer.render_frame(target, t, i))
    return frames


def write_svg_frames(frames: list[str], out_dir: str | Path,
                     stem: str = "frame") -> list[Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, svg in enumerate(frames):
        p = out / f"{stem}_{i:05d}.svg"
        p.write_text(svg, encoding="utf-8")
        paths.append(p)
    return paths
