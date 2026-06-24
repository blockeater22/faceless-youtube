"""The render engine: story -> audio -> frames -> mp4 (per aspect ratio)."""
from __future__ import annotations

import math
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import anim, media, motion, scenery, tts
from . import captions as kinetic_captions
from .draw import Sketcher
from .figures import draw_figure, get_pose
from .model import RESOLUTIONS, Scene, Script, load_script

FONT_CANDIDATES = [
    Path(__file__).parent / "fonts" / "Kalam-Bold.ttf",
    Path(__file__).parent / "fonts" / "Bangers-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
]


@lru_cache(maxsize=16)
def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(str(path), size)
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


# --------------------------------------------------------------------------- #
# Drawing one frame
# --------------------------------------------------------------------------- #
def _entry_frac(keys: list[dict]) -> float:
    """Scene-fraction at which the actor first becomes visible (alpha > ~0)."""
    for k in sorted(keys, key=lambda k: k["t"]):
        a = k.get("alpha", 1.0)
        if a is None or a > 0.05:
            return k["t"]
    return keys[0]["t"]


def _shadow(frame: Image.Image, px: float, py: float, unit: float, style, alpha: float):
    """Soft contact shadow under the feet so the figure is grounded, not floating."""
    fy = py + 0.40 * unit
    rx, ry = 0.24 * unit, 0.05 * unit
    layer = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    a = int(170 * style.shadow * max(0.0, min(1.0, alpha)))
    ImageDraw.Draw(layer).ellipse([px - rx, fy - ry, px + rx, fy + ry], fill=(0, 0, 0, a))
    frame.alpha_composite(layer.filter(ImageFilter.GaussianBlur(max(2, int(0.02 * unit)))))


def _figure_halo(col: tuple[int, int, int], style, mindim: int):
    """Pick a contrasting outline colour (dark for light figures, light for dark
    ones) so coloured stick figures pop on any background — the bold sticker look."""
    extra = getattr(style, "outline", 0.0)
    if not extra:
        return None, 0.0
    lum = 0.299 * col[0] + 0.587 * col[1] + 0.114 * col[2]
    halo = (16, 18, 26) if lum > 140 else (255, 252, 245)
    return halo, style.ink_width * mindim * extra


def _draw_actor(frame: Image.Image, actor: dict, prog: float, size, mindim, style,
                seed, duration: float, abs_t: float):
    keys = actor.get("keys", [])
    if not keys:
        return
    s = anim.sample_keys(keys, prog, {"pos": "vec", "scale": "num", "alpha": "num"})
    alpha = s.get("alpha", 1.0)
    alpha = 1.0 if alpha is None else alpha
    if alpha <= 0.01:
        return
    pose = _sample_pose(keys, prog)
    face = _face_at(keys, prog, actor.get("face", "dots"))
    w, h = size
    px, py = s["pos"][0] * w, s["pos"][1] * h
    unit = s.get("scale", 0.3) * mindim
    col = style.color(actor.get("color", "ink"))

    draw_frac = 1.0
    if style.draw_in and duration:
        win = max(1e-6, style.draw_in_dur / duration)
        draw_frac = anim.clamp((prog - _entry_frac(keys)) / win)

    if style.shadow > 0 and draw_frac > 0.2:
        _shadow(frame, px, py, unit, style, alpha * draw_frac)

    halo, halo_extra = _figure_halo(col, style, mindim)
    sk = Sketcher(size, col, style.ink_width * mindim, style.wobble * (mindim / 1080), seed,
                  halo=halo, halo_extra=halo_extra)
    draw_figure(sk, (px, py), unit, pose, color=col, face=face,
                t=abs_t, phase=motion.phase_for(actor.get("id", "")),
                life=style.life, draw=draw_frac)
    sk.composite_onto(frame, alpha)


def _actor_pos(actors: list[dict], aid: str, t: float, size):
    for a in actors:
        if a.get("id") == aid and a.get("keys"):
            s = anim.sample_keys(a["keys"], t, {"pos": "vec"})
            return s["pos"]
    return None


def _draw_glow_effect(frame, center, color, alpha, scale, size, mindim, prop, actors, t):
    """Motivated colour/light: a soft glow halo tied to the prop.

    Ray/burst *line* effects were removed — they read as messy stringy lines in
    video. Any prop that previously asked for "rays"/"burst" now gets a clean
    soft glow instead.
    """
    if not prop.get("glow") and not prop.get("rays") and prop.get("effect") not in ("glow", "rays", "burst"):
        return
    x, y = center
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a = int(120 * max(0.0, min(1.0, alpha)))
    radius = prop.get("glow_radius", 0.18) * mindim * scale
    for i, mult in enumerate((1.0, 1.55, 2.15)):
        rr = radius * mult
        aa = int(a / (i + 1.4))
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=color + (aa,))
    frame.alpha_composite(layer.filter(ImageFilter.GaussianBlur(max(6, int(0.035 * mindim)))))


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
        if pos is not None:
            _draw_glow_effect(frame, XY(pos), color, alpha, scale, size, mindim, prop, actors, t)
        layer = Image.new("RGBA", size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        fs = int(prop.get("size", 0.06) * mindim * scale)
        font = _font(max(8, fs))
        d.text(XY(pos), prop.get("text", ""), font=font, fill=color + (int(255 * alpha),),
               anchor="mm", stroke_width=max(1, fs // 14), stroke_fill=(0, 0, 0, int(180 * alpha)))
        frame.alpha_composite(layer)
        return

    sk = Sketcher(size, color, style.ink_width * mindim, style.wobble * (mindim / 1080), seed)
    if pos is not None:
        _draw_glow_effect(frame, XY(pos), color, alpha, scale, size, mindim, prop, actors, t)
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
    elif ptype == "icon":
        from .icons import draw_icon
        draw_icon(sk, prop.get("name", "star"), XY(pos),
                  prop.get("size", 0.12) * mindim * scale, color=color)
    sk.composite_onto(frame, alpha)


def _draw_caption(frame, text, local_t: float, spoken_dur: float, size, mindim, style,
                  *, emphasis: str = "", word_timings=None):
    """Word-by-word captions synced to spoken narration time (not padded silence)."""
    kinetic_captions.draw_kinetic_caption(
        frame,
        text,
        local_t,
        spoken_dur,
        size,
        mindim,
        style,
        font_loader=_font,
        emphasis=emphasis or None,
        word_timings=word_timings,
    )


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
    if abs_t < 0.12:                       # snap in (slight overshoot)
        p = abs_t / 0.12
        alpha, scale = min(1.0, p * 1.6), 1.14 - 0.14 * p
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
    cy = int(h * 0.40)
    y = cy - line_h * len(lines) // 2
    block_h = line_h * len(lines)
    block_w = min(max_w, max((font.getlength(ln) for ln in lines), default=0))

    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a = int(255 * alpha)

    # soft accent glow behind the text — instant energy on the opening second
    burst = Image.new("RGBA", size, (0, 0, 0, 0))
    bd = ImageDraw.Draw(burst)
    bx, by = w / 2, cy + block_h * 0.04
    br = max(block_w, block_h) * 1.15
    for i, mult in enumerate((1.0, 0.7, 0.45)):
        rr = br * (0.7 + 0.5 * i)
        bd.ellipse([bx - rr, by - rr * 0.7, bx + rr, by + rr * 0.7],
                   fill=style.color("accent") + (int(34 * alpha * mult),))
    frame.alpha_composite(burst.filter(ImageFilter.GaussianBlur(int(0.05 * mindim))))

    # rounded contrast card so the text always reads
    pad_x, pad_y = int(0.05 * w), int(0.03 * h)
    card = [w / 2 - block_w / 2 - pad_x, y - pad_y,
            w / 2 + block_w / 2 + pad_x, y + block_h + pad_y]
    d.rounded_rectangle(card, radius=int(0.03 * mindim), fill=(14, 16, 26, int(150 * alpha)))

    stroke = max(3, fs // 8)
    for ln in lines:
        d.text((w / 2, y), ln, font=font, anchor="ma", fill=(255, 255, 255, a),
               stroke_width=stroke, stroke_fill=(0, 0, 0, int(235 * alpha)))
        y += line_h
    frame.alpha_composite(layer)


def _hook_pad(script: Script) -> float:
    return script.hook_dur if script.hook else 0.0


def render_frame(script: Script, scene: Scene | None, local_t: float, size, mindim,
                 frame_idx: int, *, hook_only: bool = False) -> Image.Image:
    style = script.style
    if scene and scene.bg:
        bg = style.color(scene.bg)
    else:
        bg = style.color(style.background)
    frame = _background(size, bg, style.vignette).copy()
    seed = frame_idx // max(1, style.boil_every)
    abs_t = frame_idx / max(1, style.fps)

    if hook_only or scene is None:
        if getattr(style, "scenery", True):
            scenery.draw_backdrop(frame, abs_t, motion.scene_seed("hook"))
        _draw_watermark(frame, script, size, mindim, style)
        if script.hook:
            _draw_hook(frame, script.hook, abs_t, script.hook_dur, size, mindim, style)
        out = frame.convert("RGB")
        if style.grain > 0:
            arr = np.asarray(out).astype(np.int16)
            arr = np.clip(arr + _grain_stack(size, style.grain)[frame_idx % 12], 0, 255)
            out = Image.fromarray(arr.astype(np.uint8), "RGB")
        return out

    prog = local_t / scene.duration if scene.duration else 1.0
    if getattr(style, "scenery", True) and not scene.bg:
        scenery.draw_backdrop(frame, abs_t, motion.scene_seed(scene.id))
    for prop in scene.props:
        if not prop.get("front"):
            _draw_prop(frame, prop, prog, size, mindim, style, seed, scene.actors)
    for actor in scene.actors:
        _draw_actor(frame, actor, prog, size, mindim, style, seed, scene.duration, abs_t)
    for prop in scene.props:
        if prop.get("front"):
            _draw_prop(frame, prop, prog, size, mindim, style, seed, scene.actors)

    # camera move on the 'world'; the UI (captions/watermark/hook) is drawn after,
    # so it stays fixed and crisp while the drawing slowly zooms/drifts.
    if style.cam > 0:
        frame = motion.camera(frame, prog, motion.scene_seed(scene.id), style.cam)

    in_hook = bool(script.hook) and abs_t < script.hook_dur
    if not in_hook:
        spoken = scene.spoken_dur or max(0.12, scene.duration - getattr(script.voice, "gap", 0.0))
        cap_text = scene.caption if scene.caption is not None else scene.narration
        _draw_caption(
            frame, cap_text, local_t, spoken, size, mindim, style,
            emphasis=getattr(scene, "caption_emphasis", "") or "",
            word_timings=getattr(scene, "word_timings", None) or None,
        )
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
# Prop timing — sync pop-in to the spoken word, not a fixed early fraction
# --------------------------------------------------------------------------- #
def _word_appear_fraction(narration: str, sync_word: str,
                          word_timings=None, spoken_dur: float = 0.0) -> float:
    if not sync_word or not narration:
        return 0.45
    hint = sync_word.lower().strip(".,!?\"'")
    if word_timings and spoken_dur > 0:
        for wt in word_timings:
            word = wt.get("word", "") if isinstance(wt, dict) else wt.word
            start = wt.get("start", 0.0) if isinstance(wt, dict) else wt.start
            if hint in word.lower().strip(".,!?\"'"):
                return min(0.95, max(0.05, start / spoken_dur))
    words = narration.split()
    for i, w in enumerate(words):
        if hint in w.lower().strip(".,!?\"'"):
            return min(0.95, max(0.05, (i + 0.15) / max(1, len(words))))
    return 0.45


def _retime_prop(prop: dict, appear_frac: float) -> None:
    keys = prop.get("keys") or []
    pos = keys[-1].get("pos", [0.5, 0.3]) if keys else [0.5, 0.3]
    pos = list(pos)
    t0 = max(0.0, appear_frac - 0.02)
    t1 = min(0.98, appear_frac + 0.08)
    prop["keys"] = [
        {"t": round(t0, 3), "pos": pos, "alpha": 0, "scale": 0.35},
        {"t": round(t1, 3), "pos": [pos[0], pos[1] - 0.02], "alpha": 1, "scale": 1.0, "ease": "pop"},
        {"t": 1.0, "pos": [pos[0], pos[1] - 0.02], "alpha": 1, "scale": 1.0},
    ]


def _sync_scene_props(scene) -> None:
    spoken = scene.spoken_dur or scene.duration or 1.0
    for prop in scene.props:
        sync = prop.get("sync_word")
        if sync:
            _retime_prop(
                prop,
                _word_appear_fraction(
                    scene.narration, sync, getattr(scene, "word_timings", None), spoken,
                ),
            )


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
        gap = max(0.0, getattr(script.voice, "gap", 0.0))
        scene.spoken_dur = round(max(0.12, spoken - gap), 3)
        scene.duration = round(max(scene.min_dur, spoken), 3)
        scene.word_timings = [
            wt.to_dict()
            for wt in kinetic_captions.build_word_timings(
                raw,
                scene.narration,
                scene.spoken_dur,
                getattr(scene, "caption_emphasis", "") or "",
            )
        ]
        _sync_scene_props(scene)
        clip = adir / f"scene_{i:02d}_p.wav"
        media.pad_to(raw, clip, scene.duration)
        padded.append(clip)
        print(f"  scene {i:02d} '{scene.id}': {scene.duration:.2f}s  \"{scene.narration[:48]}\"")
    master = adir / "master.wav"
    media.concat(padded, master)
    pad = _hook_pad(script)
    if pad > 0:
        hook_sil = adir / "hook_pad.wav"
        media.make_silence(hook_sil, pad)
        hooked = adir / "master_hooked.wav"
        media.concat([hook_sil, master], hooked)
        master = hooked
    return master


def scene_at(script: Script, t: float):
    pad = _hook_pad(script)
    if t < pad:
        return None, t
    t -= pad
    acc = 0.0
    for i, sc in enumerate(script.scenes):
        if t < acc + sc.duration or i == len(script.scenes) - 1:
            return i, t - acc
        acc += sc.duration
    return len(script.scenes) - 1, 0.0


def _apply_transition(img, script, si, local_t, size, mindim, frame_idx, trans):
    """Fade a scene up from / down to the paper at its edges, so consecutive scenes
    cross through a clean beat instead of a hard cut. Cheap (one extra bg frame)."""
    scene = script.scenes[si]
    half = trans / 2.0
    left = scene.duration - local_t
    fade_in = local_t < half and si > 0
    fade_out = left < half and si < len(script.scenes) - 1
    if not (fade_in or fade_out):
        return img
    frac = (local_t / half) if fade_in else (left / half)
    frac = max(0.0, min(1.0, frac))
    bg = script.style.color(script.style.background)
    paper = _background(size, bg, script.style.vignette).convert("RGB")
    return Image.blend(paper, img, frac)


def render(script: Script, outdir: str | Path, formats: list[str], audio: Path) -> list[Path]:
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    fps = script.style.fps
    audio_dur = media.duration(audio)
    total = _hook_pad(script) + sum(s.duration for s in script.scenes)
    timeline = max(total, audio_dur)
    n_frames = max(1, int(math.ceil(timeline * fps - 1e-9)))
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
        trans = max(0.0, getattr(script.style, "transition", 0.0))
        try:
            for f in range(n_frames):
                si, local_t = scene_at(script, f / fps)
                if si is None:
                    img = render_frame(script, None, local_t, size, mindim, f, hook_only=True)
                else:
                    img = render_frame(script, script.scenes[si], local_t, size, mindim, f)
                    if trans > 0:
                        img = _apply_transition(img, script, si, local_t, size, mindim, f, trans)
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


def _mix_music(vo: Path, music: str, out: Path, gain_db: float) -> Path:
    """Loop + lower a music track and side-chain duck it under the voice, then mix."""
    filt = (f"[1:a]volume={gain_db}dB[m];"
            f"[m][0:a]sidechaincompress=threshold=0.05:ratio=8:attack=20:release=350[mc];"
            f"[0:a][mc]amix=inputs=2:duration=first:dropout_transition=0[a]")
    media.run([media.ffmpeg_exe(), "-y", "-i", str(vo),
               "-stream_loop", "-1", "-i", str(music),
               "-filter_complex", filt, "-map", "[a]",
               "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", str(out)])
    return Path(out)


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
    music = script.style.music
    if music and Path(music).exists():
        try:
            audio = _mix_music(audio, music, workdir / "_audio" / "master_mix.wav",
                               script.style.music_gain)
            print(f"  mixed music bed under VO: {music}")
        except Exception as exc:  # noqa: BLE001
            print(f"  [music] mix failed ({exc}); using voice only")
    return render(script, workdir, formats, audio)
