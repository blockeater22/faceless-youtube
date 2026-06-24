#!/usr/bin/env python3
"""Generate eye-catching 1280x720 YouTube thumbnails for the 10 long-form
video essays (batch 4).

Why these score higher than the old dark thumbnails on vidIQ-style checks:
  * bright, saturated, high-contrast backgrounds (not dark navy)
  * a large expressive face as the focal point (emotion reads instantly)
  * a big hero number + 2-3 punchy words (low text density, huge type)
  * heavy black stroke on every element so it pops at small sizes
  * clear left/right composition (subject on one third, text on the rest)

Run:  python branding/make_longform_thumbnails.py
Output: branding/longform_thumbs/<slug>.png
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from faceless.draw import Sketcher                  # noqa: E402
from faceless.figures import draw_figure, get_pose  # noqa: E402
from faceless.render import _font                   # noqa: E402

W, H = 1280, 720
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
INK = (245, 241, 232)
OUT = Path(__file__).resolve().parent / "longform_thumbs"


def _lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def diagonal_gradient(top, bottom):
    """Bright diagonal gradient background (top-left -> bottom-right)."""
    yy, xx = np.mgrid[0:H, 0:W]
    t = ((xx / W) * 0.45 + (yy / H) * 0.55)
    t = np.clip(t, 0, 1)
    base = np.empty((H, W, 3), dtype=np.float32)
    for i in range(3):
        base[..., i] = top[i] + (bottom[i] - top[i]) * t
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB").convert("RGBA")


def radial_glow(img, center, radius, color, strength=0.55):
    """Add a soft bright glow behind the subject for contrast + focus."""
    cx, cy = center
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / radius
    g = np.clip(1.0 - r, 0, 1) ** 2 * strength
    arr = np.asarray(img.convert("RGB"), dtype=np.float32)
    for i in range(3):
        arr[..., i] = arr[..., i] * (1 - g) + color[i] * g
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB").convert("RGBA")


def _face_features(sk, cx, cy, R, face, feat):
    """Big expressive face drawn straight onto the head (eyes + mouth + brows)."""
    ex, ey = 0.36 * R, 0.10 * R
    eye_r = max(3.0, 0.11 * R)
    if face == "surprised":
        eye_r *= 1.25
    sk.dot((cx - ex, cy - ey), eye_r, color=feat)
    sk.dot((cx + ex, cy - ey), eye_r, color=feat)
    # eyebrows add a lot of emotion
    bw, by = 0.26 * R, 0.34 * R
    if face == "sad":      # worried, inner-up brows
        sk.line((cx - ex - bw * 0.5, cy - by + 0.10 * R), (cx - ex + bw * 0.5, cy - by - 0.04 * R), color=feat, width=sk.width * 0.7)
        sk.line((cx + ex - bw * 0.5, cy - by - 0.04 * R), (cx + ex + bw * 0.5, cy - by + 0.10 * R), color=feat, width=sk.width * 0.7)
    elif face in ("think", "neutral"):  # flat brows
        sk.line((cx - ex - bw * 0.5, cy - by), (cx - ex + bw * 0.5, cy - by), color=feat, width=sk.width * 0.7)
        sk.line((cx + ex - bw * 0.5, cy - by), (cx + ex + bw * 0.5, cy - by), color=feat, width=sk.width * 0.7)
    my, mw = 0.42 * R, 0.42 * R
    if face == "happy":
        sk.arc((cx, cy + my * 0.4), mw, 25, 155, color=feat, width=sk.width * 0.9)
    elif face == "sad":
        sk.arc((cx, cy + my * 1.35), mw, 205, 335, color=feat, width=sk.width * 0.9)
    elif face == "surprised":
        sk.circle((cx, cy + my), mw * 0.5, color=feat, width=sk.width * 0.8)
    else:  # think / neutral
        sk.line((cx - mw * 0.45, cy + my), (cx + mw * 0.45, cy + my), color=feat, width=sk.width * 0.8)


def hero(img, cx, cy, R, face, pose, fig_color, accent):
    """Big outlined bust (large head + shoulders) — the focal point.

    Drawn twice: a thick black outline pass, then a lighter fill pass on top,
    so the figure pops against the saturated background just like the text.
    """
    ny = cy + R * 1.00              # neck top (head bottom)
    sy = ny + R * 0.55             # shoulder height
    sw = R * 1.55                  # half shoulder span
    yoke = [(cx - sw, H + 80), (cx - sw * 0.55, sy), (cx, ny),
            (cx + sw * 0.55, sy), (cx + sw, H + 80)]
    # one raised hand for lively poses
    arm = None
    if pose in ("celebrate", "shrug"):
        arm = [(cx + sw * 0.55, sy), (cx + sw * 1.05, sy - R * 0.85)]
    elif pose == "think":          # hand to chin
        arm = [(cx + sw * 0.5, sy), (cx + R * 0.55, cy + R * 0.95)]

    def paint(color, lw_mul):
        sk = Sketcher((W, H), color, max(7, int(R * 0.10 * lw_mul)), R * 0.035, 11)
        sk.circle((cx, cy), R, color=color)
        sk.stroke(yoke, color=color)
        if arm:
            sk.stroke(arm, color=color)
        sk.composite_onto(img)

    paint(BLACK, 1.7)              # outline
    paint(fig_color, 1.0)         # fill
    # face features (dark, drawn last so they read clearly)
    fsk = Sketcher((W, H), BLACK, max(5, int(R * 0.085)), R * 0.02, 11)
    _face_features(fsk, cx, cy, R, face, BLACK)
    fsk.composite_onto(img)
    return img


def fit(text, start, max_w, min_size=44, step=3):
    s = start
    while s > min_size and _font(s).getlength(text) > max_w:
        s -= step
    return s


def text_line(d, text, x, y, size, color, anchor="lm", stroke=None):
    stroke = max(8, size // 8) if stroke is None else stroke
    d.text((x, y), text, font=_font(size), anchor=anchor,
           fill=color + (255,), stroke_width=stroke, stroke_fill=BLACK + (255,))


def make(spec):
    img = diagonal_gradient(spec["bg_top"], spec["bg_bot"])
    # glow + figure on the chosen side
    fx = W * spec.get("fig_x", 0.81)
    fy = H * spec.get("fig_y", 0.40)
    r = H * spec.get("head_r", 0.21)
    img = radial_glow(img, (fx, fy + r * 0.2), r * 3.2, spec["glow"], 0.5)
    img = hero(img, fx, fy, r, spec["face"], spec.get("pose", "stand"),
               spec.get("fig_color", INK), spec["accent"])

    d = ImageDraw.Draw(img)
    tx = W * spec.get("text_x", 0.045)
    max_w = W * spec.get("text_right", 0.62) - tx

    # optional big hero number badge
    lines = spec["lines"]                # list of (text, color_key)
    y = H * spec.get("text_y", 0.5)
    n = len(lines)

    if spec.get("number"):
        num = spec["number"]
        ns = int(H * 0.40)
        d.text((tx + ns * 0.30, H * 0.30), num, font=_font(ns), anchor="mm",
               fill=spec["accent"] + (255,), stroke_width=20, stroke_fill=BLACK + (255,))
        tx_lines = tx + ns * 0.62
        max_w = W * spec.get("text_right", 0.62) - tx_lines
        # auto-fit headline beside the number
        size = spec.get("size", 130)
        while size > 50:
            f = _font(size)
            widest = max(f.getlength(t) for t, _ in lines)
            if widest <= max_w:
                break
            size -= 3
        lh = int(size * 1.06)
        yy = H * 0.30 - lh * (n - 1) / 2
        for t, ck in lines:
            col = spec["accent"] if ck == "a" else WHITE
            text_line(d, t, tx_lines, yy, size, col, anchor="lm")
            yy += lh
        if spec.get("sub"):
            ss = fit(spec["sub"], 56, W * 0.94 - tx, 30)
            text_line(d, spec["sub"], tx, H * 0.86, ss, spec["accent"],
                      anchor="lm", stroke=max(5, ss // 9))
    else:
        # stacked headline centered vertically on the text column
        size = spec.get("size", 150)
        while size > 50:
            f = _font(size)
            widest = max(f.getlength(t) for t, _ in lines)
            if widest <= max_w:
                break
            size -= 3
        lh = int(size * 1.08)
        yy = (H - lh * n) / 2
        for t, ck in lines:
            col = spec["accent"] if ck == "a" else WHITE
            text_line(d, t, tx, yy, size, col, anchor="la")
            yy += lh
        if spec.get("sub"):
            ss = fit(spec["sub"], 54, W * 0.94 - tx, 30)
            text_line(d, spec["sub"], tx + 4, yy + lh * 0.1, ss, spec["accent"],
                      anchor="la", stroke=max(5, ss // 9))

    OUT.mkdir(exist_ok=True)
    path = OUT / f"{spec['slug']}.png"
    img.convert("RGB").save(path)
    print("wrote", path.name, "->", Image.open(path).size)


# bright, saturated, high-contrast palettes — distinct per video
SPECS = [
    {  # 1 — psychological effects (Mind Traps)
        "slug": "lf_psychological_effects",
        "bg_top": (124, 58, 237), "bg_bot": (49, 16, 110), "accent": (255, 214, 64),
        "glow": (167, 110, 255), "face": "surprised", "pose": "shrug",
        "number": "6", "lines": [("PSYCH", "w"), ("EFFECTS", "a")],
        "sub": "secretly running your life",
    },
    {  # 2 — harsh truths (Hard Truths)
        "slug": "lf_harsh_truths",
        "bg_top": (225, 45, 57), "bg_bot": (120, 12, 24), "accent": (255, 221, 92),
        "glow": (255, 96, 96), "face": "sad", "pose": "stand",
        "number": "6", "lines": [("HARSH", "w"), ("TRUTHS", "a")],
        "sub": "nobody tells you",
    },
    {  # 3 — feel behind (Hard Truths)
        "slug": "lf_feel_behind",
        "bg_top": (13, 148, 136), "bg_bot": (8, 51, 68), "accent": (255, 214, 64),
        "glow": (45, 212, 191), "face": "sad", "pose": "think",
        "lines": [("WHY YOU", "w"), ("FEEL", "w"), ("BEHIND", "a")],
        "size": 150,
    },
    {  # 4 — loneliness epidemic (Mind Traps)
        "slug": "lf_loneliness_epidemic",
        "bg_top": (59, 76, 138), "bg_bot": (18, 24, 54), "accent": (120, 210, 255),
        "glow": (96, 130, 220), "face": "sad", "pose": "stand",
        "lines": [("ALONE", "a"), ("IN A", "w"), ("CROWD", "w")],
        "size": 156,
    },
    {  # 5 — mindset shifts (Mindset Shifts)
        "slug": "lf_mindset_shifts",
        "bg_top": (16, 185, 129), "bg_bot": (6, 78, 59), "accent": (255, 224, 64),
        "glow": (52, 211, 153), "face": "happy", "pose": "celebrate",
        "number": "6", "lines": [("MINDSET", "w"), ("SHIFTS", "a")],
        "sub": "that change everything",
    },
    {  # 6 — smart procrastinate (Mind Traps)
        "slug": "lf_smart_procrastinate",
        "bg_top": (245, 158, 11), "bg_bot": (146, 64, 14), "accent": (200, 28, 40),
        "glow": (255, 196, 90), "face": "think", "pose": "think",
        "fig_color": (28, 28, 42),
        "lines": [("WHY SMART", "w"), ("PEOPLE", "w"), ("STALL", "a")],
        "size": 142,
    },
    {  # 7 — mental health habits (Mind Traps)
        "slug": "lf_mental_health_habits",
        "bg_top": (219, 39, 119), "bg_bot": (112, 16, 70), "accent": (255, 224, 64),
        "glow": (255, 110, 180), "face": "surprised", "pose": "stand",
        "lines": [("STOP", "w"), ("DOING", "w"), ("THESE", "a")],
        "sub": "6 habits wrecking your mind", "size": 158,
    },
    {  # 8 — rock bottom (Hard Truths)
        "slug": "lf_rock_bottom_lessons",
        "bg_top": (234, 88, 12), "bg_bot": (88, 20, 12), "accent": (255, 224, 64),
        "glow": (255, 140, 70), "face": "sad", "pose": "sit",
        "lines": [("ROCK", "w"), ("BOTTOM", "a")],
        "sub": "6 lessons success never teaches", "size": 176,
    },
    {  # 9 — comparing yourself (Mind Traps)
        "slug": "lf_comparing_yourself",
        "bg_top": (8, 145, 178), "bg_bot": (12, 45, 72), "accent": (255, 214, 64),
        "glow": (56, 189, 248), "face": "sad", "pose": "stand",
        "lines": [("STOP", "w"), ("COMPARING", "a"), ("YOURSELF", "w")],
        "size": 132,
    },
    {  # 10 — emotional maturity (Mindset Shifts)
        "slug": "lf_emotional_maturity",
        "bg_top": (147, 51, 234), "bg_bot": (59, 16, 96), "accent": (255, 224, 64),
        "glow": (180, 120, 255), "face": "happy", "pose": "stand",
        "number": "6", "lines": [("SIGNS", "w"), ("YOU'RE", "w"), ("MATURE", "a")],
        "sub": "more than you realize", "size": 120,
    },
]


if __name__ == "__main__":
    for spec in SPECS:
        make(spec)
    print(f"\n{len(SPECS)} thumbnails written to {OUT}")
