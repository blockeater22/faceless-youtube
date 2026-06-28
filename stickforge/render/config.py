"""Render configuration: canvas size and global drawing style."""
from __future__ import annotations

from dataclasses import dataclass

# Named output resolutions (min dimension 1080 so line weights match across all).
RESOLUTIONS: dict[str, tuple[int, int]] = {
    "9:16": (1080, 1920),
    "16:9": (1920, 1080),
    "1:1": (1080, 1080),
    "preview": (540, 960),
}


@dataclass
class RenderConfig:
    width: int = 1080
    height: int = 1920
    background: str = "#0e1320"
    ink: str = "#f2ede1"
    ink_width: float = 0.0060        # fraction of min(W, H)
    wobble: float = 1.6              # hand-drawn jitter, px at 1080 min-dim
    boil_every: int = 2              # re-seed wobble every N frames ("on twos")
    caption_color: str = "#f2ede1"
    caption_size: float = 0.040      # fraction of min(W, H)

    @classmethod
    def for_format(cls, fmt: str = "9:16", **kw) -> "RenderConfig":
        w, h = RESOLUTIONS.get(fmt, RESOLUTIONS["9:16"])
        return cls(width=w, height=h, **kw)

    @property
    def min_dim(self) -> int:
        return min(self.width, self.height)

    @property
    def stroke_px(self) -> float:
        return self.ink_width * self.min_dim
