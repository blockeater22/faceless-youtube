"""Atmospheric backdrops so a scene is a *place*, not an empty void.

The single loudest complaint about v1 was "it's a stick figure floating in
black." This draws a cohesive night world — gradient sky, a moon, a star field,
a horizon/ground the figure stands on, and slow drifting motes — behind every
scene. Heavy parts are cached per (size, seed); only the motes animate per frame.
"""
from __future__ import annotations

import math
import random
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


@lru_cache(maxsize=8)
def _sky(size: tuple[int, int], top: tuple, bottom: tuple) -> Image.Image:
    w, h = size
    t, b = np.array(top, np.float32), np.array(bottom, np.float32)
    col = t[None, :] + (b - t)[None, :] * np.linspace(0, 1, h, dtype=np.float32)[:, None]
    arr = np.repeat(col[:, None, :], w, axis=1).astype(np.uint8)
    return Image.fromarray(arr, "RGB").convert("RGBA")


@lru_cache(maxsize=24)
def _backdrop(size: tuple[int, int], seed: int, ground_y: float) -> Image.Image:
    w, h = size
    rng = np.random.default_rng(seed)
    cool = seed % 3 != 0
    top = (17, 23, 44) if cool else (30, 22, 42)      # subtle per-scene hue shift
    img = _sky(size, top, (12, 16, 28)).copy()
    d = ImageDraw.Draw(img)
    gy = int(h * ground_y)

    # star field (above the horizon)
    for _ in range(70):
        x, y = int(rng.uniform(0, w)), int(rng.uniform(0, gy * 0.92))
        r = rng.uniform(0.6, 2.3)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(238, 240, 255, int(rng.uniform(55, 175))))

    # moon + soft glow, upper area
    mx, my, mr = int(w * (0.66 + 0.22 * rng.random())), int(h * (0.16 + 0.08 * rng.random())), int(h * 0.058)
    glow = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([mx - mr * 2.6, my - mr * 2.6, mx + mr * 2.6, my + mr * 2.6],
                                 fill=(255, 226, 172, 46))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(46)))
    d.ellipse([mx - mr, my - mr, mx + mr, my + mr], fill=(246, 240, 226, 235))

    # ground: a slightly lifted plane + horizon line
    grd = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(grd).rectangle([0, gy, w, h], fill=(9, 12, 20, 205))
    img.alpha_composite(grd)
    d.line([(0, gy), (w, gy)], fill=(120, 132, 156, 95), width=2)
    return img


def draw_backdrop(frame: Image.Image, t: float, seed: int, ground_y: float = 0.80) -> None:
    """Composite the cached night world, then a few per-frame drifting motes."""
    frame.alpha_composite(_backdrop(frame.size, seed, round(ground_y, 3)))
    w, h = frame.size
    d = ImageDraw.Draw(frame)
    rng = random.Random(seed ^ 0x9E3779B9)
    for i in range(14):
        bx, by = rng.random(), rng.random()
        x = ((bx + t * 0.008 * (0.5 + by)) % 1.0) * w
        y = (by * (ground_y - 0.05) + 0.03 * math.sin(t * 0.5 + i)) * h
        r = 1.0 + 1.7 * by
        d.ellipse([x - r, y - r, x + r, y + r], fill=(205, 214, 235, 42))
