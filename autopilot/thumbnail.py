"""High-CTR YouTube thumbnail generator for stick and AI-image videos.

Stick mode: bold multi-colour Bangers headline + faceless figure + red focal ring.
Image mode: Pollinations/FLUX background from the hook scene + giant text overlay.
"""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from faceless.draw import Sketcher  # noqa: E402
from faceless.figures import draw_figure, get_pose  # noqa: E402
from faceless.render import _background, _font  # noqa: E402

# Default palette — overridden per channel via config.palette / config.colors
DEFAULT_BG = (8, 10, 18)
DEFAULT_INK = (250, 246, 238)
DEFAULT_ACCENT = (255, 180, 84)
DEFAULT_MUTED = (118, 126, 150)
RED = (240, 46, 46)
KINETIC = ("#FF6B6B", "#FFD93D", "#6BCB77", "#4D96FF", "#FF6FD8", "#FFB454", "#FFFFFF")


def _hex(s: str) -> tuple[int, int, int]:
    s = s.lstrip("#")
    return tuple(int(s[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _palette(config: dict | None) -> dict[str, tuple[int, int, int]]:
    cfg = config or {}
    pal = cfg.get("palette") or {}
    colors = cfg.get("colors") or []
    kinetic = [_hex(c) if isinstance(c, str) else tuple(c) for c in colors] if colors else [_hex(c) for c in KINETIC]
    return {
        "bg": _hex(pal.get("background", cfg.get("background", "#080a12"))),
        "ink": _hex(pal.get("ink", cfg.get("ink", "#faf6ee"))),
        "accent": _hex(pal.get("accent", cfg.get("accent", "#ffb454"))),
        "muted": _hex(pal.get("muted", cfg.get("muted", "#767e96"))),
        "kinetic": kinetic,
    }


def _thumb_font(size: int):
    """Prefer Bangers for YouTube CTR; fall back to render fonts."""
    bangers = ROOT / "faceless" / "fonts" / "Bangers-Regular.ttf"
    if bangers.exists():
        from PIL import ImageFont
        return ImageFont.truetype(str(bangers), size)
    return _font(size)


def _hook_beat(script: dict | None) -> dict | None:
    if not script:
        return None
    for b in script.get("beats", []):
        if b.get("template") == "hook":
            return b
    beats = script.get("beats") or []
    return beats[0] if beats else None


def extract_thumbnail_copy(script: dict | None, topic: dict | None, hook_fallback: str = "") -> str:
    """2–6 word ALL-CAPS headline optimised for mobile thumbnails."""
    if script:
        if script.get("thumbnail_text"):
            return _clean_headline(script["thumbnail_text"])
        hook = (script.get("hook") or "").strip()
        if hook and len(hook.split()) <= 7:
            return _clean_headline(hook)
        beat = _hook_beat(script)
        if beat:
            if beat.get("text"):
                line1 = beat["text"].strip().upper()
                emph = (beat.get("caption_emphasis") or "").replace(",", " ").split()
                punch = [w.strip(".,!?\"'").upper() for w in emph if w.strip()][:2]
                if punch and punch[0] not in line1:
                    return f"{line1}\n{' '.join(punch)}"
                return line1
            words = [
                w.strip(".,!?\"'").upper()
                for w in beat.get("narration", "").split()
                if len(w.strip(".,!?\"'")) > 2
            ][:4]
            if len(words) >= 2:
                mid = max(1, len(words) // 2)
                return f"{' '.join(words[:mid])}\n{' '.join(words[mid:])}"
        title = (script.get("title") or "").strip()
        if title:
            bits = [w.upper() for w in re.findall(r"[A-Za-z0-9']+", title) if len(w) > 2][:5]
            if bits:
                mid = max(1, len(bits) // 2)
                return f"{' '.join(bits[:mid])}\n{' '.join(bits[mid:])}"
    brief = (topic or {}).get("brief", hook_fallback or "WATCH THIS")
    words = [w.upper() for w in re.findall(r"[A-Za-z0-9']+", brief) if len(w) > 2][:5]
    if words:
        mid = max(1, len(words) // 2)
        return f"{' '.join(words[:mid])}\n{' '.join(words[mid:])}"
    return _clean_headline(hook_fallback or "WATCH THIS")


def _clean_headline(text: str) -> str:
    text = re.sub(r"\s+", " ", text.strip().upper())
    if len(text) > 42:
        words = text.split()
        mid = max(1, len(words) // 2)
        text = f"{' '.join(words[:mid])}\n{' '.join(words[mid:])}"
    return text[:48]


def _wrap_line(text: str, size: int, max_w: float) -> list[str]:
    words, lines, cur = text.split(), [], []
    for w in words:
        trial = " ".join(cur + [w])
        if _thumb_font(size).getlength(trial) > max_w and cur:
            lines.append(" ".join(cur))
            cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(" ".join(cur))
    return lines or [text]


def _fit_headline(text: str, max_w: float, big: int = 118, min_size: int = 58) -> tuple[list[str], int]:
    size = big
    while size >= min_size:
        lines = []
        for block in text.split("\n"):
            lines.extend(_wrap_line(block, size, max_w))
        if len(lines) <= 3 and all(_thumb_font(size).getlength(ln) <= max_w for ln in lines):
            return lines, size
        size -= 4
    return _wrap_line(text.replace("\n", " "), min_size, max_w), min_size


def _draw_kinetic_headline(
    d: ImageDraw.ImageDraw,
    text: str,
    x: float,
    y: float,
    max_w: float,
    palette: dict,
    *,
    big: int = 118,
    anchor_top: bool = True,
) -> int:
    """Multi-colour word stack; returns bottom y."""
    lines, size = _fit_headline(text, max_w, big=big)
    lh = int(size * 1.05)
    cy = y
    word_idx = 0
    colors = palette["kinetic"]
    for li, line in enumerate(lines):
        words = line.split()
        total = sum(_thumb_font(size).getlength(w + " ") for w in words) - _thumb_font(size).getlength(" ")
        cx = x if anchor_top else x - total / 2
        for wi, word in enumerate(words):
            col = palette["accent"] if (li == len(lines) - 1 and wi == len(words) - 1) else colors[word_idx % len(colors)]
            stroke = max(6, size // 9)
            d.text(
                (cx, cy),
                word,
                font=_thumb_font(size),
                fill=col + (255,),
                stroke_width=stroke,
                stroke_fill=(0, 0, 0, 255),
            )
            cx += _thumb_font(size).getlength(word + " ")
            word_idx += 1
        cy += lh
    return int(cy)


def _ring(d, cx, cy, rx, ry):
    d.ellipse([cx - rx - 4, cy - ry - 4, cx + rx + 4, cy + ry + 4], outline=(0, 0, 0, 255), width=18)
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], outline=RED + (255,), width=12)


def _arrow(d, p1, p2, width=14, head=38):
    d.line([p1, p2], fill=RED + (255,), width=width)
    ang = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
    for da in (math.radians(150), math.radians(-150)):
        d.line(
            [p2, (p2[0] + head * math.cos(ang + da), p2[1] + head * math.sin(ang + da))],
            fill=RED + (255,),
            width=width,
        )


def _glow(img, cx, cy, r, color=(255, 210, 140, 90)):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(48)))


def _gradient_bg(size: tuple[int, int], palette: dict) -> Image.Image:
    w, h = size
    bg, accent = palette["bg"], palette["accent"]
    arr = np.zeros((h, w, 3), dtype=np.float32)
    for y in range(h):
        t = y / max(1, h - 1)
        arr[y, :, 0] = bg[0] * (1 - t) + accent[0] * t * 0.22
        arr[y, :, 1] = bg[1] * (1 - t) + accent[1] * t * 0.18
        arr[y, :, 2] = bg[2] * (1 - t) + accent[2] * t * 0.12
    # subtle radial vignette
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy = w / 2, h / 2
    r = np.sqrt(((xx - cx) / cx) ** 2 + ((yy - cy) / cy) ** 2)
    arr *= (1.0 - 0.35 * np.clip(r, 0, 1) ** 2)[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB").convert("RGBA")


def _bottom_scrim(img: Image.Image, strength: float = 0.55) -> None:
    w, h = img.size
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for y in range(h):
        t = max(0.0, (y - h * 0.45) / (h * 0.55))
        a = int(255 * strength * t * t)
        d.line([(0, y), (w, y)], fill=(0, 0, 0, a))
    img.alpha_composite(layer)


def _accent_bar(img: Image.Image, palette: dict) -> None:
    w, h = img.size
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rectangle([0, 0, w, 10], fill=palette["accent"] + (255,))
    d.rectangle([0, h - 8, w, h], fill=palette["accent"] + (180,))
    img.alpha_composite(layer)


def _draw_icon_large(img, name: str, cx: float, cy: float, unit: float, color):
    from faceless.icons import draw_icon
    sk = Sketcher(img.size, color, max(6, unit * 0.08), 2.2, 3)
    draw_icon(sk, name, (cx, cy), unit, color=color)
    sk.composite_onto(img, 1.0)


def _figure_from_beat(img, beat: dict | None, pos, unit: float, palette: dict, default_pose="think"):
    pose = (beat or {}).get("pose", default_pose)
    face = (beat or {}).get("face", "neutral")
    sk = Sketcher(img.size, palette["ink"], max(7, unit * 0.012), 2.4, 7)
    draw_figure(sk, pos, unit, get_pose(pose), color=palette["ink"], face=face)
    sk.composite_onto(img)


def _layout_split(img, headline: str, palette: dict, beat: dict | None):
    w, h = img.size
    panels = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    pd = ImageDraw.Draw(panels)
    pd.rectangle([0, 0, w // 2, h], fill=(0, 0, 0, 110))
    pd.rectangle([w // 2, 0, w, h], fill=palette["accent"] + (38,))
    img.alpha_composite(panels)
    _glow(img, int(w * 0.74), int(h * 0.52), int(h * 0.32))
    ImageDraw.Draw(img).line([(w // 2, 0), (w // 2, h)], fill=palette["muted"] + (180,), width=5)
    _figure_from_beat(img, beat, (w * 0.265, h * 0.88), h * 0.64, palette, "think")
    _figure_from_beat(img, None, (w * 0.735, h * 0.88), h * 0.66, palette, "celebrate")
    d = ImageDraw.Draw(img)
    _ring(d, int(w * 0.735), int(h * 0.50), int(w * 0.15), int(h * 0.34))
    _arrow(d, (w * 0.40, h * 0.28), (w * 0.56, h * 0.38))
    _draw_kinetic_headline(d, headline, w * 0.04, h * 0.10, w * 0.92, palette, big=108)


def _layout_bigface(img, headline: str, palette: dict, beat: dict | None):
    w, h = img.size
    unit = h * 1.14
    hx, hy = w * 0.28, h * 1.06
    cx, cy, hr = hx, hy - 0.50 * unit, 0.13 * unit
    _glow(img, cx, cy, hr * 2.2, palette["accent"] + (70,))
    _figure_from_beat(img, beat, (hx, hy), unit, palette, "stand")
    d = ImageDraw.Draw(img)
    _ring(d, cx, cy, hr * 1.30, hr * 1.30)
    _draw_kinetic_headline(d, headline, w * 0.48, h * 0.28, w * 0.48, palette, big=124)


def _layout_stars(img, headline: str, palette: dict, beat: dict | None):
    w, h = img.size
    unit = h * 0.76
    hx, hy = w * 0.28, h * 0.92
    cx, cy, hr = hx, hy - 0.50 * unit, 0.13 * unit
    _glow(img, cx, cy, hr * 2.0)
    d0 = ImageDraw.Draw(img)
    for sx, sy, s in [(0.62, 0.14, 44), (0.76, 0.22, 34), (0.88, 0.13, 38), (0.68, 0.32, 28)]:
        d0.text((sx * w, sy * h), "✦", font=_thumb_font(s), anchor="mm", fill=palette["accent"] + (255,))
    _figure_from_beat(img, beat, (hx, hy), unit, palette, "look_up")
    d = ImageDraw.Draw(img)
    _ring(d, int(cx), int(cy), int(hr * 1.34), int(hr * 1.34))
    if beat and beat.get("icon"):
        _draw_icon_large(img, beat["icon"], w * 0.78, h * 0.38, h * 0.14, palette["accent"])
    _draw_kinetic_headline(d, headline, w * 0.44, h * 0.26, w * 0.52, palette, big=112)


def _layout_bubbles(img, headline: str, palette: dict, beat: dict | None):
    w, h = img.size
    _figure_from_beat(img, beat, (w * 0.24, h * 0.88), h * 0.62, palette, "think")
    sk = Sketcher((w, h), palette["ink"], 8, 2.6, 11)
    for cx, cy, r, col in [(0.12, 0.32, 0.062, palette["accent"]), (0.28, 0.18, 0.052, palette["muted"])]:
        sk.circle((cx * w, cy * h), r * w, color=col, width=6, amp=4.5)
    sk.composite_onto(img)
    d = ImageDraw.Draw(img)
    sym = "?" if not beat else {"phone": "!", "eye": "...", "heart": "♥"}.get(beat.get("icon", ""), "?")
    d.text((0.12 * w, 0.32 * h), sym, font=_thumb_font(int(w * 0.062)), anchor="mm",
           fill=palette["accent"] + (255,), stroke_width=4, stroke_fill=(0, 0, 0, 255))
    if beat and beat.get("icon"):
        _draw_icon_large(img, beat["icon"], w * 0.78, h * 0.36, h * 0.16, palette["accent"])
    _ring(d, int(w * 0.24), int(h * 0.54), int(w * 0.11), int(h * 0.17))
    _draw_kinetic_headline(d, headline, w * 0.44, h * 0.26, w * 0.52, palette, big=112)


def _layout_impact(img, headline: str, palette: dict, beat: dict | None):
    """Text-dominant layout — best for image-mode fallback."""
    w, h = img.size
    _bottom_scrim(img, 0.35)
    if beat and beat.get("icon"):
        _draw_icon_large(img, beat["icon"], w * 0.82, h * 0.38, h * 0.18, palette["accent"])
        _glow(img, int(w * 0.82), int(h * 0.38), int(h * 0.22), palette["accent"] + (60,))
    d = ImageDraw.Draw(img)
    _draw_kinetic_headline(d, headline, w * 0.06, h * 0.18, w * 0.88, palette, big=132)


def _make_stick_thumbnail(headline: str, kind: str, out_path: Path, script: dict | None, palette: dict) -> Path:
    w, h = 1280, 720
    img = _gradient_bg((w, h), palette)
    beat = _hook_beat(script)
    layouts = {
        "split": _layout_split,
        "bigface": _layout_bigface,
        "stars": _layout_stars,
        "bubbles": _layout_bubbles,
        "impact": _layout_impact,
    }
    layouts.get(kind, _layout_bubbles)(img, headline, palette, beat)
    _accent_bar(img, palette)
    img.convert("RGB").save(out_path)
    return out_path


def _thumbnail_bg_prompt(script: dict | None, topic: dict | None) -> str:
    beat = _hook_beat(script)
    if beat and beat.get("image_prompt"):
        return (
            f"YouTube thumbnail background, {beat['image_prompt']}, "
            "single bold focal subject, cinematic, high contrast, dramatic lighting, "
            "NO text, NO words, NO letters, NO watermark, 16:9"
        )
    brief = (topic or {}).get("brief") or (script or {}).get("title") or "abstract mind"
    return (
        f"YouTube thumbnail background illustrating: {brief}, "
        "cinematic, dramatic, one symbolic object, dark moody atmosphere, "
        "NO text, NO words, NO watermark, 16:9"
    )


def _make_ai_thumbnail(headline: str, out_path: Path, script: dict | None, topic: dict | None, palette: dict) -> Path:
    w, h = 1280, 720
    tmp = out_path.with_suffix(".bg.png")
    try:
        from autopilot.images import generate_image

        generate_image(
            _thumbnail_bg_prompt(script, topic),
            tmp,
            width=w,
            height=h,
            provider="pollinations",
            style="cinematic thumbnail, bold composition, shallow depth of field",
            fallback=False,
        )
        img = Image.open(tmp).convert("RGBA").resize((w, h), Image.LANCZOS)
    except Exception as exc:
        print(f"  [thumbnail] AI background failed ({exc}); using stick impact layout")
        return _make_stick_thumbnail(headline, "impact", out_path, script, palette)

    _bottom_scrim(img, 0.62)
    beat = _hook_beat(script)
    if beat and beat.get("icon"):
        _draw_icon_large(img, beat["icon"], w * 0.84, h * 0.34, h * 0.15, palette["accent"])
    d = ImageDraw.Draw(img)
    _draw_kinetic_headline(d, headline, w * 0.05, h * 0.52, w * 0.90, palette, big=128)
    _accent_bar(img, palette)
    img.convert("RGB").save(out_path)
    tmp.unlink(missing_ok=True)
    return out_path


def make_thumbnail(
    hook: str,
    kind: str,
    out_path: str | Path,
    *,
    script: dict | None = None,
    topic: dict | None = None,
    config: dict | None = None,
    visual_style: str = "stick",
) -> Path:
    """Render a 1280×720 YouTube thumbnail next to the video."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    palette = _palette(config)
    headline = extract_thumbnail_copy(script, topic, hook)
    print(f"  [thumbnail] '{headline.replace(chr(10), ' | ')}' ({visual_style}/{kind})")

    if visual_style == "image":
        return _make_ai_thumbnail(headline, out_path, script, topic, palette)
    return _make_stick_thumbnail(headline, kind, out_path, script, palette)
