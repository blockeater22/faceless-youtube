"""The render engine: story -> audio -> frames -> mp4 (per aspect ratio)."""
from __future__ import annotations

import math
import subprocess
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import anim, media, tts
from .draw import Sketcher
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


# --------------------------------------------------------------------------- #
# Drawing one frame
# --------------------------------------------------------------------------- #
def _draw_actor(frame: Image.Image, actor: dict, t: float, size, mindim, style, seed):
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
    px, py = s["pos"][0] * w, s["pos"][1] * h
    unit = s.get("scale", 0.3) * mindim
    sk = Sketcher(size, style.color(actor.get("color", "ink")),
                  style.ink_width * mindim, style.wobble * (mindim / 1080), seed)
    draw_figure(sk, (px, py), unit, pose,
                color=style.color(actor.get("color", "ink")), face=face)
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


def render_frame(script: Script, scene: Scene, local_t: float, size, mindim, frame_idx) -> Image.Image:
    style = script.style
    bg = style.color(scene.bg) if scene.bg else style.color(style.background)
    frame = _background(size, bg, style.vignette).copy()
    seed = frame_idx // max(1, style.boil_every)
    prog = local_t / scene.duration if scene.duration else 1.0

    for prop in scene.props:
        if not prop.get("front"):
            _draw_prop(frame, prop, prog, size, mindim, style, seed, scene.actors)
    for actor in scene.actors:
        _draw_actor(frame, actor, prog, size, mindim, style, seed)
    for prop in scene.props:
        if prop.get("front"):
            _draw_prop(frame, prop, prog, size, mindim, style, seed, scene.actors)

    reveal = min(1.0, local_t / (scene.duration * 0.82)) if scene.duration else 1.0
    _draw_caption(frame, scene.caption if scene.caption is not None else scene.narration,
                  reveal, size, mindim, style)
    _draw_watermark(frame, script, size, mindim, style)

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
    master = adir / "master.wav"
    media.concat(padded, master)
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

        cmd = [media.ffmpeg_exe(), "-y",
               "-f", "rawvideo", "-pix_fmt", "rgb24",
               "-s", f"{size[0]}x{size[1]}", "-r", str(fps), "-i", "-",
               "-i", str(audio),
               "-map", "0:v", "-map", "1:a",
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
               "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
               "-movflags", "+faststart", "-shortest", str(out_path)]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
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
        err = proc.stderr.read().decode("utf-8", "ignore")
        if proc.wait() != 0:
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
