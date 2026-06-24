"""Shared helpers for high-CTR YouTube thumbnails.

Thumbnail-scoring tools (vidIQ etc.) reward a few concrete things: a big,
clearly emotional face; bold high-contrast text with very few words; vivid,
contrasting colours; and one obvious focal point instead of clutter. These
helpers wrap the faceless engine's stick-figure/icon primitives into that
shape so every thumbnail script gets it for free instead of hand-rolling a
flat navy panel + thin headline.

Run any script in this folder directly to regenerate its PNG.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from faceless.draw import Sketcher                 # noqa: E402
from faceless.figures import draw_figure, get_pose  # noqa: E402
from faceless.icons import draw_icon                # noqa: E402
from faceless.render import _font                    # noqa: E402

W, H = 1280, 720


def radial_bg(w: int, h: int, hot: tuple, cool: tuple,
              center: tuple = (0.32, 0.42), radius: float = 1.05) -> Image.Image:
    """Vivid radial-gradient background: a bright ``hot`` colour bursting from
    ``center``, fading to a darker ``cool`` edge. Gives the face/headline a
    built-in spotlight and far more contrast than a flat panel."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = center[0] * w, center[1] * h
    maxr = radius * math.hypot(max(cx, w - cx), max(cy, h - cy))
    r = np.clip(np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / maxr, 0, 1)[..., None]
    hot_a, cool_a = np.array(hot, dtype=np.float32), np.array(cool, dtype=np.float32)
    rgb = hot_a * (1 - r) + cool_a * r
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB").convert("RGBA")


def big_face(img: Image.Image, cx: float, cy: float, unit: float, pose: str = "arms_up",
             face: str = "surprised", color=(20, 16, 30), lw: float = 16, wobble: float = 5) -> None:
    """A large, bold-stroked figure sized/weighted for thumbnail scale: thicker
    lines and bigger features than a video frame, so the emotion reads
    instantly even at a small preview size."""
    sk = Sketcher((W, H), color, lw, wobble, 11)
    draw_figure(sk, (cx, cy), unit, get_pose(pose), color=color, face=face, lw=lw)
    sk.composite_onto(img)


def stroke_text(d: ImageDraw.ImageDraw, xy, text: str, font, fill: tuple,
                 stroke_fill=(0, 0, 0, 255), stroke_width: int = 14, anchor: str = "lm") -> None:
    f = fill if len(fill) == 4 else fill + (255,)
    d.text(xy, text, font=font, fill=f, anchor=anchor, stroke_width=stroke_width, stroke_fill=stroke_fill)


def highlight_bar(d: ImageDraw.ImageDraw, x0, y0, x1, y1, color, radius: int = 14) -> None:
    c = color if len(color) == 4 else color + (255,)
    d.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=c)


def badge(img: Image.Image, cx: float, cy: float, r: float, bg: tuple, text: str,
          text_color: tuple = (255, 255, 255), ring: tuple = (255, 255, 255), ring_w: int = 10) -> None:
    """A bold circular badge for a hero number or short tag - the kind of
    high-contrast, glanceable focal point that out-performs plain text."""
    d = ImageDraw.Draw(img)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=bg + (255,))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=ring + (255,), width=ring_w)
    size = int(r * 1.15)
    f = _font(size)
    while f.getlength(text) > r * 1.5 and size > 30:
        size -= 4
        f = _font(size)
    d.text((cx, cy), text, font=f, anchor="mm", fill=text_color + (255,))


def prop_icon(img: Image.Image, name: str, cx: float, cy: float, r: float, color: tuple) -> None:
    """A small, bright, relatable icon (lightbulb, brain, heart...) used as a
    second focal accent near the headline."""
    d = ImageDraw.Draw(img)
    c = color if len(color) == 4 else color + (255,)
    draw_icon(d, name, cx, cy, r, c)


def fit_size(text: str, max_w: float, start: int, floor: int = 36, step: int = 3) -> int:
    s = start
    while s > floor and _font(s).getlength(text) > max_w:
        s -= step
    return s
