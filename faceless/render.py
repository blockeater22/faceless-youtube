"""The render engine: story -> audio -> frames -> mp4 (per aspect ratio)."""
from __future__ import annotations

import math
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import anim, icons, media, scenery, tts
from .draw import Sketcher
from .effects import draw_effects
from .figures import draw_figure, get_pose
from .model import RESOLUTIONS, Scene, Script, load_script

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
]


@lru_cache(maxsize=16)
def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size)


# --------------------------------------------------------------------------- #
# Static background (paper colour + vignette), cached per size
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=4)
def _background(size: tuple[int, int], bg: tuple[int, int, int], vignette: float) -> Image.Image:
    w, h = size
    base = np.zeros((h, w, 3), dtype=np.float32) + np.array(bg, dtype=np.float32)
    if vignette > 0:
        yy, xx = np.mgrid[0:h, 0:w]
        cx, cy = w / 2.0, h / 2.0
        r = np.sqrt(((xx - cx) / cx) ** 2 + ((yy - cy) / cy) ** 2) / math.sqrt(2)
        base *= (1.0 - vignette * np.clip(r, 0, 1) ** 2)[..., None]
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB").convert("RGBA")


@lru_cache(maxsize=4)
def _grain_stack(size: tuple[int, int], strength: float, n: int = 12) -> tuple:
    w, h = size
    rng = np.random.default_rng(7)
    return tuple((rng.normal(0, 1, (h, w, 1)) * (strength * 26)).astype(np.int16) for _ in range(n))


# --------------------------------------------------------------------------- #
# Sampling actors / props
# --------------------------------------------------------------------------- #
def _sample_pose(keys: list[dict], t: float) -> dict:
    keys = sorted(keys, key=lambda k: k["t"])
    if t <= keys[0]["t"]:
        return get_pose(keys[0].get("pose", "stand"))
    if t >= keys[-1]["t"]:
        return get_pose(keys[-1].get("pose", "stand"))
    for i in range(len(keys) - 1):
        k0, k1 = keys[i], keys[i + 1]
        if k0["t"] <= t <= k1["t"]:
            span = (k1["t"] - k0["t"]) or 1e-9
            ease = anim.EASINGS.get(k1.get("ease", "ease_in_out"), anim.ease_in_out)
            e = ease((t - k0["t"]) / span)
            return anim.blend_pose(get_pose(k0.get("pose", "stand")),
                                   get_pose(k1.get("pose", "stand")), e)
    return get_pose("stand")


def _face_at(keys: list[dict], t: float, default: str) -> str:
    face = default
    for k in sorted(keys, key=lambda k: k["t"]):
        if k["t"] <= t and "face" in k:
            face = k["face"]
    return face


def _pose_name_at(keys: list[dict], t: float) -> str:
    """The named pose currently in effect (the most recent keyframe's pose) -
    used to decide whether a figure is 'moving' for trailing speed lines."""
    name = "stand"
    for k in sorted(keys, key=lambda k: k["t"]):
        if k["t"] <= t and isinstance(k.get("pose"), str):
            name = k["pose"]
    return name


# --------------------------------------------------------------------------- #
# Drawing one frame
# --------------------------------------------------------------------------- #
def _idle_blink(abs_t: float, actor_id: str) -> bool:
    """A short eye-blink a few times a minute, with a per-actor phase offset so
    figures don't all blink in lockstep. ~one blink every 3.4s for 0.12s."""
    period, dur = 3.4, 0.12
    off = (hash(actor_id) % 1000) / 1000.0 * period
    return ((abs_t + off) % period) < dur


def _idle_breathe(abs_t: float, actor_id: str, unit: float) -> float:
    """A tiny vertical bob (returned in px) so a held pose still has life."""
    off = (hash(actor_id) % 997) / 997.0 * math.tau
    return math.sin(abs_t * 1.6 + off) * unit * 0.010


def _draw_marker(sk: Sketcher, tip, unit: float, color) -> None:
    """A simple marker/pen pointing at the active draw tip - the visual cue
    that the line is being drawn by hand (whiteboard look)."""
    tx, ty = tip
    L = unit * 0.42                       # pen length
    dx, dy = 0.5, -0.87                   # up-and-right
    bx, by = tx + dx * L, ty + dy * L     # back of the pen
    # barrel
    sk.draw.line([(tx, ty), (bx, by)], fill=color, width=max(3, int(unit * 0.05)), joint="curve")
    # nib (a little triangle at the tip)
    n = unit * 0.07
    sk.draw.polygon([(tx, ty), (tx + n * 0.9, ty - n * 1.4),
                     (tx - n * 0.5, ty - n * 1.6)], fill=color)
    # cap dot at the back
    r = unit * 0.035
    sk.draw.ellipse([bx - r, by - r, bx + r, by + r], fill=color)


def _draw_actor(frame: Image.Image, actor: dict, t: float, size, mindim, style, seed,
                abs_t: float = 0.0, local_t: float = 0.0):
    keys = actor.get("keys", [])
    if not keys:
        return
    s = anim.sample_keys(keys, t, {"pos": "vec", "scale": "num", "alpha": "num"})
    alpha = s.get("alpha", 1.0)
    if alpha <= 0.01:
        return
    pose = _sample_pose(keys, t)
    face = _face_at(keys, t, actor.get("face", "dots"))
    w, h = size
    aid = actor.get("id", "")
    px, py = s["pos"][0] * w, s["pos"][1] * h
    unit = s.get("scale", 0.3) * mindim
    # whiteboard draw-on: figure draws itself on over the first draw_on seconds
    # of the scene (local_t is scene-local; abs_t is global, for blink/breathe)
    draw_on = style.draw_on
    reveal = anim.clamp(local_t / draw_on) if draw_on > 0 else 1.0
    drawing = reveal < 1.0
    # idle life: a held pose breathes slightly and blinks now and then (only
    # once it's fully drawn, so it doesn't wobble mid-stroke)
    blink = False
    if not drawing:
        py += _idle_breathe(abs_t, aid, unit)
        blink = _idle_blink(abs_t, aid)
    fig_color = style.color(actor.get("color", "ink"))
    sk = Sketcher(size, fig_color,
                  style.ink_width * mindim, style.wobble * (mindim / 1080), seed)
    head_c, hr = draw_figure(sk, (px, py), unit, pose, color=fig_color, face=face,
                             blink=blink, reveal=reveal)
    pose_name = _pose_name_at(keys, t)
    # effect glyphs only after the figure is fully drawn
    if not drawing:
        draw_effects(sk, head_c, hr, (px, py), unit, face, pose_name,
                     actor.get("fx"), style.color("accent"), fig_color, t)
    elif sk.last_tip is not None:
        _draw_marker(sk, sk.last_tip, unit, fig_color)
    sk.composite_onto(frame, alpha)


def _actor_pos(actors: list[dict], aid: str, t: float, size):
    for a in actors:
        if a.get("id") == aid and a.get("keys"):
            s = anim.sample_keys(a["keys"], t, {"pos": "vec"})
            return s["pos"]
    return None


def _draw_prop(frame, prop, t, size, mindim, style, seed, actors):
    keys = prop.get("keys", [{"t": 0}])
    s = anim.sample_keys(keys, t, {"pos": "vec", "scale": "num", "alpha": "num",
                                   "p1": "vec", "p2": "vec"})
    alpha = s.get("alpha")
    alpha = 1.0 if alpha is None else alpha
    if alpha <= 0.01:
        return
    w, h = size
    scale = s.get("scale")
    scale = 1.0 if scale is None else scale
    color = style.color(prop.get("color", "ink"))
    ptype = prop.get("type", "label")

    pos = s.get("pos")
    if prop.get("follow") and pos is not None:
        base = _actor_pos(actors, prop["follow"], t, size) or pos
        off = prop.get("offset", [0, 0])
        pos = [base[0] + off[0], base[1] + off[1]]

    def XY(p):
        return (p[0] * w, p[1] * h)

    if ptype == "label":
        layer = Image.new("RGBA", size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        fs = int(prop.get("size", 0.06) * mindim * scale)
        font = _font(max(8, fs))
        d.text(XY(pos), prop.get("text", ""), font=font, fill=color + (int(255 * alpha),),
               anchor="mm", stroke_width=max(1, fs // 14), stroke_fill=(0, 0, 0, int(180 * alpha)))
        frame.alpha_composite(layer)
        return

    sk = Sketcher(size, color, style.ink_width * mindim, style.wobble * (mindim / 1080), seed)
    if ptype == "circle":
        sk.circle(XY(pos), prop.get("r", 0.1) * mindim * scale, color=color)
    elif ptype == "rect":
        cw, ch = prop.get("w", 0.2) * w * scale / 2, prop.get("h", 0.2) * h * scale / 2
        x, y = XY(pos)
        pts = [(x - cw, y - ch), (x + cw, y - ch), (x + cw, y + ch), (x - cw, y + ch), (x - cw, y - ch)]
        sk.stroke(pts, color=color)
    elif ptype == "line":
        sk.line(XY(s["p1"]), XY(s["p2"]), color=color)
    elif ptype == "arrow":
        p1, p2 = XY(s["p1"]), XY(s["p2"])
        sk.line(p1, p2, color=color)
        ang = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
        head = 0.035 * mindim
        for da in (math.radians(150), math.radians(-150)):
            sk.line(p2, (p2[0] + head * math.cos(ang + da), p2[1] + head * math.sin(ang + da)), color=color)
    elif ptype == "icon":
        layer = Image.new("RGBA", size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        r = prop.get("r", 0.12) * mindim * scale
        cx, cy = XY(pos)
        icons.draw_icon(d, prop.get("name", "star"), cx, cy, r, color + (int(255 * alpha),))
        frame.alpha_composite(layer)
        return
    elif ptype == "object":
        layer = Image.new("RGBA", size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        sz = prop.get("size", 0.34) * mindim * scale
        cx, cy = XY(pos)
        tint = style.color(prop["color"]) if "color" in prop else None
        scenery.draw_object(d, prop.get("name", "armchair"), cx, cy, sz, tint)
        if alpha < 1.0:
            a = layer.getchannel("A").point(lambda v: int(v * alpha))
            layer.putalpha(a)
        frame.alpha_composite(layer)
        return
    elif ptype == "path":
        raw = prop.get("points", [])
        anchor = prop.get("anchor")
        if anchor is not None:
            # rigid shape: points are offsets in min-dim units (aspect-safe)
            ax, ay = anchor[0] * w, anchor[1] * h
            u = prop.get("unit", 0.3) * mindim * scale
            pts = [(ax + p[0] * u, ay + p[1] * u) for p in raw]
        else:
            pts = [XY(p) for p in raw]  # frame-relative (ok for full-width lines)
        if len(pts) >= 2:
            sk.stroke(pts, color=color)
    sk.composite_onto(frame, alpha)


def _draw_caption(frame, text, reveal, size, mindim, style):
    if not text:
        return
    w, h = size
    cfg = style.caption or {}
    fs = int(cfg.get("size", 0.047) * mindim)
    font = _font(fs)
    words = text.split()
    n_vis = max(0, min(len(words), math.ceil(reveal * len(words))))
    if n_vis == 0:
        return
    vis = words[:n_vis]
    max_w = w * 0.86

    # word-wrap the visible words
    lines, cur = [], []
    for word in vis:
        trial = " ".join(cur + [word])
        if font.getlength(trial) > max_w and cur:
            lines.append(cur)
            cur = [word]
        else:
            cur.append(word)
    if cur:
        lines.append(cur)

    line_h = int(fs * 1.28)
    block_h = line_h * len(lines)
    base_y = (0.80 if h >= w else 0.855) * h - block_h / 2

    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    ink = style.color(cfg.get("color", "#ffffff"))
    accent = style.color("accent")
    stroke = max(2, fs // 11)
    newest = n_vis - 1
    idx = 0
    for li, line in enumerate(lines):
        total = font.getlength(" ".join(line))
        x = (w - total) / 2
        y = base_y + li * line_h
        for word in line:
            col = accent if idx == newest else ink
            d.text((x, y), word, font=font, fill=col + (255,),
                   stroke_width=stroke, stroke_fill=(0, 0, 0, 235))
            x += font.getlength(word + " ")
            idx += 1
    frame.alpha_composite(layer)


def _chunk_phrase(text: str, max_chars: int = 16) -> list[list[str]]:
    """Group words into short on-screen phrases (kinetic-typography pacing)."""
    words = text.split()
    chunks, cur, cur_len = [], [], 0
    for word in words:
        wl = len(word) + 1
        if cur and cur_len + wl > max_chars:
            chunks.append(cur)
            cur, cur_len = [], 0
        cur.append(word)
        cur_len += wl
    if cur:
        chunks.append(cur)
    return chunks or [[]]


def _draw_kinetic_caption(frame, text, local_t, duration, size, mindim, style, emphasis=False):
    """Big colourful, phrase-by-phrase centre-screen text (white-bg explainer
    style) - one short phrase pops in at a time instead of a scrolling line.

    ``emphasis`` punches the type up for the SOP "reframe" beat (the payoff
    line) so it reads as a deliberate pattern-interrupt rather than the same
    flat pop-in every other beat gets."""
    if not text or not duration:
        return
    w, h = size
    cfg = style.caption or {}
    chunks = _chunk_phrase(text, cfg.get("max_chars", 16))
    n = len(chunks)
    prog = anim.clamp(local_t / duration)
    idx = min(n - 1, int(prog * n))
    phase = anim.clamp(prog * n - idx)

    pop_in, fade_out = 0.22, 0.85
    overshoot = 1.22 if emphasis else 1.0
    if phase < pop_in:
        e = anim.ease_out_back(phase / pop_in)
        alpha = anim.clamp(phase / pop_in * 1.3)
        scale = (0.55 + 0.45 * e) * overshoot if e < 1.0 else overshoot
    elif phase > fade_out:
        alpha = anim.clamp((1.0 - phase) / (1.0 - fade_out))
        scale = 1.0
    else:
        alpha, scale = 1.0, 1.0

    words = chunks[idx]
    if not words or alpha <= 0.01:
        return

    fs = max(8, int(cfg.get("size", 0.10) * mindim * scale))
    font = _font(fs)
    palette = [style.color(c) for c in (style.palette or [style.accent])]
    gap = font.getlength(" ")
    upper = [word.upper() for word in words]
    widths = [font.getlength(word) for word in upper]
    total_w = sum(widths) + gap * (len(words) - 1)
    # Fit-to-width guard: never let a phrase clip past the frame edges. The
    # reframe-beat emphasis overshoot in particular can blow a wide phrase out
    # of bounds, so shrink the font to fit a 92% safe area when needed.
    max_w = w * 0.92
    if total_w > max_w:
        fs = max(8, int(fs * max_w / total_w))
        font = _font(fs)
        gap = font.getlength(" ")
        widths = [font.getlength(word) for word in upper]
        total_w = sum(widths) + gap * (len(words) - 1)
    x = w / 2 - total_w / 2
    y = h * cfg.get("y", 0.46)

    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    base_idx = sum(len(c) for c in chunks[:idx])
    shadow_off = max(1, fs // 28)
    for i, wu in enumerate(upper):
        col = palette[(base_idx + i) % len(palette)]
        d.text((x + shadow_off, y + shadow_off * 1.4), wu, font=font, anchor="lm",
                fill=(0, 0, 0, int(35 * alpha)))
        d.text((x, y), wu, font=font, anchor="lm", fill=col + (int(255 * alpha),))
        x += widths[i] + gap
    frame.alpha_composite(layer)


def _apply_camera(frame: Image.Image, scene: Scene, prog: float, size) -> Image.Image:
    """Ken-Burns style push-in/pan over a scene, sampled from ``scene.camera``
    keyframes. A no-op (returns ``frame`` unchanged) for the ~90 pre-existing
    stories that don't set ``camera`` - default zoom is 1.0 (no crop)."""
    keys = scene.camera
    if not keys:
        return frame
    s = anim.sample_keys(keys, prog, {"zoom": "num", "pan": "vec"})
    zoom = s.get("zoom") or 1.0
    if zoom <= 1.001:
        return frame
    pan = s.get("pan") or [0.5, 0.5]
    w, h = size
    cw, ch = w / zoom, h / zoom
    cx, cy = anim.clamp(pan[0]) * w, anim.clamp(pan[1]) * h
    x0 = anim.clamp(cx - cw / 2, 0, w - cw)
    y0 = anim.clamp(cy - ch / 2, 0, h - ch)
    crop = frame.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch)))
    return crop.resize(size, Image.LANCZOS)


@lru_cache(maxsize=8)
def _load_logo(path: str, px: int) -> Image.Image:
    return Image.open(path).convert("RGBA").resize((px, px), Image.LANCZOS)


def _draw_watermark(frame, script, size, mindim, style):
    w, h = size
    logo = style.logo
    if logo and Path(logo).exists():
        # corner badge (+ handle text) burned into the frame
        px = int(style.logo_scale * mindim)
        im = _load_logo(logo, px)
        if style.logo_opacity < 1:
            im = im.copy()
            im.putalpha(im.getchannel("A").point(lambda v: int(v * style.logo_opacity)))
        m = int(0.035 * mindim)
        x = m if "l" in style.logo_pos else w - px - m
        y = m if "t" in style.logo_pos else h - px - m
        frame.alpha_composite(im, (x, y))
        if script.handle and "l" in style.logo_pos:
            fs = max(10, int(px * 0.30))
            d = ImageDraw.Draw(frame)
            d.text((x + px + int(px * 0.14), y + px / 2), script.handle, font=_font(fs),
                   anchor="lm", fill=style.color("muted") + (int(235 * style.logo_opacity),),
                   stroke_width=max(1, fs // 12), stroke_fill=(0, 0, 0, 150))
        return
    if script.handle:  # fallback: centered text handle at top
        fs = int(0.026 * mindim)
        d = ImageDraw.Draw(frame)
        d.text((w / 2, 0.055 * h), script.handle, font=_font(fs),
               fill=style.color("muted") + (170,), anchor="mm")


def _draw_hook(frame, text, abs_t, dur, size, mindim, style):
    """Big punch-in hook text for the opening seconds - the Shorts retention lever."""
    if not text or abs_t >= dur:
        return
    w, h = size
    fade = 0.30
    if abs_t < 0.12:                       # snap in (slight overshoot), fully visible immediately
        p = abs_t / 0.12
        alpha, scale = 1.0, 1.14 - 0.14 * p
    elif abs_t > dur - fade:               # quick fade out
        alpha, scale = max(0.0, (dur - abs_t) / fade), 1.0
    else:
        alpha, scale = 1.0, 1.0

    fs = max(14, int(0.088 * mindim * scale))
    font = _font(fs)
    max_w = w * 0.84
    lines, cur = [], []
    for word in text.upper().split():
        if font.getlength(" ".join(cur + [word])) > max_w and cur:
            lines.append(" ".join(cur)); cur = [word]
        else:
            cur.append(word)
    if cur:
        lines.append(" ".join(cur))

    line_h = int(fs * 1.16)
    cy = int(h * 0.33)
    y = cy - line_h * len(lines) // 2
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a = int(255 * alpha)
    stroke = max(3, fs // 8)
    for ln in lines:
        d.text((w / 2, y), ln, font=font, anchor="ma", fill=(255, 255, 255, a),
               stroke_width=stroke, stroke_fill=(0, 0, 0, int(235 * alpha)))
        y += line_h
    frame.alpha_composite(layer)


def render_frame(script: Script, scene: Scene, local_t: float, size, mindim, frame_idx) -> Image.Image:
    style = script.style
    bg = style.color(scene.bg) if scene.bg else style.color(style.background)
    frame = _background(size, bg, style.vignette).copy()
    seed = frame_idx // max(1, style.boil_every)
    prog = local_t / scene.duration if scene.duration else 1.0

    for prop in scene.props:
        if not prop.get("front"):
            _draw_prop(frame, prop, prog, size, mindim, style, seed, scene.actors)
    abs_t_scene = frame_idx / max(1, style.fps)
    for actor in scene.actors:
        _draw_actor(frame, actor, prog, size, mindim, style, seed, abs_t_scene, local_t)
    for prop in scene.props:
        if prop.get("front"):
            _draw_prop(frame, prop, prog, size, mindim, style, seed, scene.actors)

    frame = _apply_camera(frame, scene, prog, size)

    abs_t = frame_idx / max(1, style.fps)
    in_hook = bool(script.hook) and abs_t < script.hook_dur
    if not in_hook:   # hook card replaces the caption while it's up
        cap_text = scene.caption if scene.caption is not None else scene.narration
        if (style.caption or {}).get("mode") == "kinetic":
            _draw_kinetic_caption(frame, cap_text, local_t, scene.duration, size, mindim, style,
                                   emphasis=scene.beat == "reframe")
        else:
            reveal = min(1.0, local_t / (scene.duration * 0.82)) if scene.duration else 1.0
            _draw_caption(frame, cap_text, reveal, size, mindim, style)
    _draw_watermark(frame, script, size, mindim, style)
    if in_hook:
        _draw_hook(frame, script.hook, abs_t, script.hook_dur, size, mindim, style)

    out = frame.convert("RGB")
    if style.grain > 0:
        arr = np.asarray(out).astype(np.int16)
        arr = np.clip(arr + _grain_stack(size, style.grain)[frame_idx % 12], 0, 255)
        out = Image.fromarray(arr.astype(np.uint8), "RGB")
    return out


# --------------------------------------------------------------------------- #
# Audio + orchestration
# --------------------------------------------------------------------------- #
def build_audio(script: Script, workdir: Path) -> Path:
    """Synthesize each scene, set scene durations, and return the master wav."""
    adir = workdir / "_audio"
    adir.mkdir(parents=True, exist_ok=True)
    padded = []
    for i, scene in enumerate(script.scenes):
        raw = adir / f"scene_{i:02d}.wav"
        tts.synth(scene.narration, raw, script.voice)
        scene.audio = str(raw)
        spoken = media.duration(raw)
        scene.duration = round(max(scene.min_dur, spoken), 3)
        clip = adir / f"scene_{i:02d}_p.wav"
        media.pad_to(raw, clip, scene.duration)
        padded.append(clip)
        print(f"  scene {i:02d} '{scene.id}': {scene.duration:.2f}s  \"{scene.narration[:48]}\"")
    concatenated = adir / "concat.wav"
    media.concat(padded, concatenated)
    master = adir / "master.wav"
    media.loudnorm(concatenated, master)
    return master


def scene_at(script: Script, t: float):
    acc = 0.0
    for i, sc in enumerate(script.scenes):
        if t < acc + sc.duration or i == len(script.scenes) - 1:
            return i, t - acc
        acc += sc.duration
    return len(script.scenes) - 1, 0.0


def render(script: Script, outdir: str | Path, formats: list[str], audio: Path) -> list[Path]:
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    fps = script.style.fps
    total = sum(s.duration for s in script.scenes)
    n_frames = max(1, round(total * fps))
    results = []

    for fmt in formats:
        size = RESOLUTIONS[fmt]
        mindim = min(size)
        slug = fmt.replace(":", "x")
        out_path = outdir / f"{outdir.name}_{slug}.mp4"
        print(f"\n  rendering {fmt} ({size[0]}x{size[1]}) -> {out_path.name}  [{n_frames} frames]")

        cmd = [media.ffmpeg_exe(), "-y", "-nostats", "-loglevel", "error",
               "-f", "rawvideo", "-pix_fmt", "rgb24",
               "-s", f"{size[0]}x{size[1]}", "-r", str(fps), "-i", "-",
               "-i", str(audio),
               "-map", "0:v", "-map", "1:a",
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
               "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
               "-movflags", "+faststart", "-shortest", str(out_path)]
        # ffmpeg stderr -> a real temp file, NOT a pipe. If we used a pipe and
        # only drained it after the frame loop, ffmpeg's stderr could fill the
        # 64KB OS buffer mid-encode, block, stop reading frames, and deadlock the
        # writer (this happened on long videos). A file never blocks.
        errf = tempfile.TemporaryFile()
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=errf)
        try:
            for f in range(n_frames):
                si, local_t = scene_at(script, f / fps)
                img = render_frame(script, script.scenes[si], local_t, size, mindim, f)
                proc.stdin.write(img.tobytes())
                if f % 96 == 0:
                    print(f"    {f:4d}/{n_frames}  ({100*f//n_frames:3d}%)", flush=True)
            proc.stdin.close()
        except BrokenPipeError:
            pass
        rc = proc.wait()
        errf.seek(0)
        err = errf.read().decode("utf-8", "ignore")
        errf.close()
        if rc != 0:
            raise RuntimeError("ffmpeg encode failed:\n" + err[-1800:])
        results.append(out_path)
        print(f"    done -> {out_path}")
    return results


def build(story_path: str | Path, formats: list[str] | None = None,
          outroot: str | Path = "output", voice_overrides: dict | None = None) -> list[Path]:
    script = load_script(story_path)
    for k, v in (voice_overrides or {}).items():
        if v is not None:
            setattr(script.voice, k, v)
    formats = formats or ["9:16", "16:9"]
    name = Path(story_path).stem
    workdir = Path(outroot) / name
    workdir.mkdir(parents=True, exist_ok=True)
    print(f"Story: {script.title!r}  ({len(script.scenes)} scenes) -> {formats}")
    print("Synthesizing narration:")
    audio = build_audio(script, workdir)
    return render(script, workdir, formats, audio)
