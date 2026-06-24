"""Vibrant, colourful backdrops so every scene is a bright *place*, not a void.

v1 was "a stick figure floating in black." v2 was "a stick figure floating in a
dark night." Neither pops on Shorts. This module draws a saturated, sunny world
that *changes per scene* — a colourful gradient sky, a glowing sun, soft rolling
hills, drifting clouds, and floating bokeh. A small library of themes rotates by
scene seed so the channel feels lively and varied instead of monotonous.

Heavy parts are cached per (size, seed); only the bokeh/clouds drift per frame.
"""
from __future__ import annotations

import math
import random
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

# --------------------------------------------------------------------------- #
# Theme library — each is a bright, high-contrast colour world. Tuples are RGB.
#   sky_top / sky_bottom : vertical gradient
#   sun                  : sun disc colour      sun_glow: halo colour
#   hill_far / hill_near : two rolling hill bands (near = ground the figure is on)
#   bokeh                : floating dot colour
# --------------------------------------------------------------------------- #
THEMES: list[dict] = [
    {  # sunset pop
        "sky_top": (255, 122, 89), "sky_bottom": (255, 205, 122),
        "sun": (255, 240, 200), "sun_glow": (255, 196, 120),
        "hill_far": (255, 150, 113), "hill_near": (214, 95, 110), "bokeh": (255, 240, 200),
    },
    {  # teal day
        "sky_top": (38, 198, 218), "sky_bottom": (197, 240, 230),
        "sun": (255, 248, 220), "sun_glow": (255, 235, 170),
        "hill_far": (120, 214, 196), "hill_near": (66, 178, 156), "bokeh": (255, 255, 255),
    },
    {  # candy dusk
        "sky_top": (155, 120, 236), "sky_bottom": (255, 176, 205),
        "sun": (255, 246, 230), "sun_glow": (255, 200, 230),
        "hill_far": (200, 150, 240), "hill_near": (150, 110, 210), "bokeh": (255, 245, 255),
    },
    {  # ocean morning
        "sky_top": (33, 94, 190), "sky_bottom": (95, 211, 220),
        "sun": (255, 250, 224), "sun_glow": (180, 235, 245),
        "hill_far": (90, 180, 210), "hill_near": (44, 120, 170), "bokeh": (235, 250, 255),
    },
    {  # meadow noon
        "sky_top": (90, 190, 245), "sky_bottom": (224, 245, 200),
        "sun": (255, 250, 210), "sun_glow": (255, 240, 160),
        "hill_far": (150, 210, 120), "hill_near": (96, 178, 88), "bokeh": (255, 255, 230),
    },
    {  # grape soda
        "sky_top": (58, 28, 113), "sky_bottom": (231, 109, 137),
        "sun": (255, 224, 178), "sun_glow": (255, 150, 160),
        "hill_far": (140, 80, 170), "hill_near": (92, 52, 130), "bokeh": (255, 220, 235),
    },
]


def _lerp(a: tuple, b: tuple, t: float) -> tuple:
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


@lru_cache(maxsize=8)
def _sky(size: tuple[int, int], top: tuple, bottom: tuple) -> Image.Image:
    w, h = size
    t, b = np.array(top, np.float32), np.array(bottom, np.float32)
    col = t[None, :] + (b - t)[None, :] * np.linspace(0, 1, h, dtype=np.float32)[:, None]
    arr = np.repeat(col[:, None, :], w, axis=1).astype(np.uint8)
    return Image.fromarray(arr, "RGB").convert("RGBA")


def _hill_band(size, gy: int, amp: int, color: tuple, phase: float, alpha: int = 255) -> Image.Image:
    """A soft rolling hill silhouette filling from y≈gy to the bottom."""
    w, h = size
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    pts = [(0, h)]
    for x in range(0, w + 1, max(8, w // 60)):
        y = gy + int(math.sin(x / w * math.tau * 1.5 + phase) * amp)
        pts.append((x, y))
    pts.append((w, h))
    d.polygon(pts, fill=color + (alpha,))
    return layer


@lru_cache(maxsize=24)
def _backdrop(size: tuple[int, int], seed: int, ground_y: float) -> Image.Image:
    w, h = size
    theme = THEMES[seed % len(THEMES)]
    img = _sky(size, theme["sky_top"], theme["sky_bottom"]).copy()
    rng = random.Random(seed * 2654435761 & 0xFFFFFFFF)
    gy = int(h * ground_y)

    # big soft sun with a warm halo, upper third (position varies by seed)
    sx = int(w * (0.20 + 0.6 * rng.random()))
    sy = int(h * (0.16 + 0.10 * rng.random()))
    sr = int(min(w, h) * 0.085)
    glow = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse(
        [sx - sr * 3.4, sy - sr * 3.4, sx + sr * 3.4, sy + sr * 3.4],
        fill=theme["sun_glow"] + (120,),
    )
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(int(sr * 0.9))))
    ImageDraw.Draw(img).ellipse([sx - sr, sy - sr, sx + sr, sy + sr], fill=theme["sun"] + (255,))

    # a couple of soft clouds
    for _ in range(3):
        cx, cy = int(rng.uniform(0, w)), int(rng.uniform(h * 0.08, gy * 0.7))
        cw = int(min(w, h) * rng.uniform(0.12, 0.22))
        cloud = Image.new("RGBA", size, (0, 0, 0, 0))
        cd = ImageDraw.Draw(cloud)
        for k in range(4):
            ox = int((k - 1.5) * cw * 0.42)
            rr = int(cw * (0.5 - 0.06 * abs(k - 1.5)))
            cd.ellipse([cx + ox - rr, cy - rr // 2, cx + ox + rr, cy + rr // 2],
                       fill=(255, 255, 255, 60))
        img.alpha_composite(cloud.filter(ImageFilter.GaussianBlur(int(cw * 0.10))))

    # two rolling hill bands: far (lighter, higher) then near (the ground plane)
    img.alpha_composite(_hill_band(size, int(gy - h * 0.05), int(h * 0.035),
                                   theme["hill_far"], phase=seed * 0.7, alpha=210))
    img.alpha_composite(_hill_band(size, gy, int(h * 0.02),
                                   theme["hill_near"], phase=seed * 1.3, alpha=255))
    return img


def draw_backdrop(frame: Image.Image, t: float, seed: int, ground_y: float = 0.80) -> None:
    """Composite the cached colour world, then a few per-frame drifting bokeh."""
    frame.alpha_composite(_backdrop(frame.size, seed, round(ground_y, 3)))
    w, h = frame.size
    theme = THEMES[seed % len(THEMES)]
    bk = theme["bokeh"]
    layer = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    rng = random.Random(seed ^ 0x9E3779B9)
    for i in range(16):
        bx, by = rng.random(), rng.random()
        x = ((bx + t * 0.012 * (0.4 + by)) % 1.05) * w
        y = (by * (ground_y - 0.04) + 0.04 * math.sin(t * 0.6 + i)) * h
        r = 2.0 + 6.0 * by
        a = int(70 + 60 * by)
        d.ellipse([x - r, y - r, x + r, y + r], fill=bk + (a,))
    frame.alpha_composite(layer.filter(ImageFilter.GaussianBlur(1)))
