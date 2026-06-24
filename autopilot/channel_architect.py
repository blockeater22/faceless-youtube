"""AI Channel Generation.

Researches a trending niche and generates a fully realized brand identity
for a new YouTube channel, including name, colors, styles, and descriptions.
On save, also builds profile picture, YouTube banner, and video watermark assets.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from autopilot import gemini_pool
from autopilot.provider_router import generate_scene_image

ROOT = Path(__file__).resolve().parent.parent

SYSTEM = """You are a senior YouTube channel architect and brand strategist.
The user wants to launch a new, high-RPM faceless channel.
Pick a highly specific, trending niche (e.g., psychology of wealth, stoicism, dark history, deep tech).
Then, design a complete, premium brand identity for this new channel.

Rules for output:
1. "name": A catchy, premium 1-2 word channel name (e.g., "Quark", "Zenn", "MindSpark").
2. "handle": A likely available YouTube handle (e.g., "@Quark5050", "@Zenn0009").
3. "description": A 2-sentence YouTube "About" description.
4. "persona": The scriptwriter system prompt persona (e.g., "Calm, analytical narrator explaining the psychology of human behavior. Short sentences.").
5. "palette": An object with 4 hex colors: "background" (should fit the mood, e.g. white for clean, dark navy for space, sepia for history), "ink" (contrasting text/figure color), "accent" (bright pop color), "muted" (secondary text).
6. "colors": A list of 4-6 hex codes for the vivid props/labels that cycle each scene.
7. "figure": An object with "embiggen" (e.g. 1.4), "wobble" (1.0 to 2.5), "grain" (0.01 to 0.05), "transition" (0.2 to 0.4), "pace" (2.5 to 3.5).
8. "rotation": A list of 3-4 content pillars/themes for this channel.
9. "logo_prompt": An image generation prompt for a minimalist, premium vector logo on a solid background matching the palette.
10. "banner_prompt": An image generation prompt for a YouTube banner background.

Return ONLY a raw JSON object."""


def generate_channel_concept() -> dict:
    """Generate a channel concept using Gemini."""
    if not gemini_pool.has_key():
        raise RuntimeError("Gemini API key is required to generate a channel concept.")

    prompt = "Create a brand new, highly engaging faceless YouTube channel concept."
    return gemini_pool.generate_json(
        prompt=prompt,
        system_instruction=SYSTEM,
        model=None,
    )


def _hex_rgb(hex_color: str) -> tuple[int, int, int]:
    s = str(hex_color).lstrip("#")
    return tuple(int(s[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _brand_font(size: int):
    bangers = ROOT / "faceless" / "fonts" / "Bangers-Regular.ttf"
    if bangers.exists():
        from PIL import ImageFont
        return ImageFont.truetype(str(bangers), size)
    from PIL import ImageFont
    return ImageFont.load_default()


def _default_logo_prompt(channel: dict) -> str:
    pal = channel.get("palette") or {}
    name = channel.get("name", "Channel")
    return (
        f"Minimalist premium vector logo icon for YouTube channel {name}, "
        f"flat design, accent {pal.get('accent', '#ffb454')}, ink {pal.get('ink', '#f2ede1')}, "
        f"solid {pal.get('background', '#0e1320')} background, symbolic mark, no text, no letters"
    )


def _default_banner_prompt(channel: dict) -> str:
    pal = channel.get("palette") or {}
    name = channel.get("name", "Channel")
    return (
        f"Wide cinematic abstract YouTube channel banner background for {name}, "
        f"moody atmosphere, colors {pal.get('background', '#0e1320')} and {pal.get('accent', '#ffb454')}, "
        f"premium, atmospheric, no text, no logos"
    )


def _fallback_profile(channel: dict, out_path: Path) -> None:
    pal = channel.get("palette") or {}
    bg = _hex_rgb(pal.get("background", "#0e1320"))
    accent = _hex_rgb(pal.get("accent", "#ffb454"))
    ink = _hex_rgb(pal.get("ink", "#f2ede1"))
    size = 800
    im = Image.new("RGBA", (size, size), bg + (255,))
    draw = ImageDraw.Draw(im)
    draw.ellipse((80, 80, size - 80, size - 80), fill=accent + (255,))
    letter = (channel.get("name") or "C")[0].upper()
    font = _brand_font(int(size * 0.38))
    draw.text((size / 2, size / 2), letter, font=font, fill=ink + (255,), anchor="mm")
    im.save(out_path)


def _fallback_banner(channel: dict, out_path: Path) -> None:
    pal = channel.get("palette") or {}
    bg = _hex_rgb(pal.get("background", "#0e1320"))
    accent = _hex_rgb(pal.get("accent", "#ffb454"))
    ink = _hex_rgb(pal.get("ink", "#f2ede1"))
    w, h = 2560, 1440
    im = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(im)
    for y in range(h):
        t = y / max(h - 1, 1)
        col = tuple(int(bg[i] * (1 - t) + accent[i] * t) for i in range(3))
        draw.line([(0, y), (w, y)], fill=col)
    name = channel.get("name", "Channel")
    font = _brand_font(140)
    draw.text((w * 0.08, h * 0.42), name, font=font, fill=ink)
    handle = channel.get("handle", "")
    if handle:
        draw.text((w * 0.08, h * 0.58), handle, font=_brand_font(64), fill=accent)
    im.save(out_path)


def _watermark_from_profile(profile_path: Path, out_path: Path, *, accent: str) -> None:
    """Corner badge used on rendered videos — circular crop with soft shadow."""
    src = Image.open(profile_path).convert("RGBA")
    src = src.resize((512, 512), Image.LANCZOS)
    mask = Image.new("L", (512, 512), 0)
    ImageDraw.Draw(mask).ellipse((8, 8, 504, 504), fill=255)
    src.putalpha(mask)
    pad = 64
    canvas = Image.new("RGBA", (512 + pad * 2, 512 + pad * 2), (0, 0, 0, 0))
    shadow = Image.new("RGBA", src.size, (0, 0, 0, 0))
    shadow.paste(src, (0, 0), src)
    shadow = shadow.filter(ImageFilter.GaussianBlur(10))
    canvas.alpha_composite(shadow, (pad + 6, pad + 8))
    ring = ImageDraw.Draw(canvas)
    ring.ellipse(
        (pad - 4, pad - 4, pad + 512 + 4, pad + 512 + 4),
        outline=_hex_rgb(accent) + (220,),
        width=6,
    )
    canvas.alpha_composite(src, (pad, pad))
    canvas.save(out_path)


def _try_generate_image(prompt: str, out_path: Path, *, width: int, height: int,
                        provider: str, style: str, cache_dir: Path) -> bool:
    try:
        generate_scene_image(
            prompt,
            out_path,
            width=width,
            height=height,
            provider=provider,
            style=style,
            cache_dir=cache_dir,
        )
        return out_path.exists() and out_path.stat().st_size > 500
    except Exception as exc:  # noqa: BLE001
        print(f"  [brand] image gen failed ({out_path.name}): {exc}")
        return False


def generate_brand_assets(channel: dict, outdir: Path, *, provider: str = "auto") -> dict:
    """Generate profile picture, YouTube banner, and video watermark PNGs."""
    outdir = Path(outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    cache_dir = outdir / "_cache"

    profile_path = outdir / "profile.png"
    banner_path = outdir / "banner.png"
    watermark_path = outdir / "watermark.png"

    logo_prompt = channel.get("logo_prompt") or _default_logo_prompt(channel)
    banner_prompt = channel.get("banner_prompt") or _default_banner_prompt(channel)
    pal = channel.get("palette") or {}

    if not _try_generate_image(
        logo_prompt,
        profile_path,
        width=800,
        height=800,
        provider=provider,
        style="flat vector logo icon, minimalist, premium, clean, no text, no letters",
        cache_dir=cache_dir,
    ):
        _fallback_profile(channel, profile_path)

    banner_tmp = outdir / "_banner_src.png"
    if _try_generate_image(
        banner_prompt,
        banner_tmp,
        width=1280,
        height=720,
        provider=provider,
        style="youtube banner background, wide cinematic, abstract, premium, no text",
        cache_dir=cache_dir,
    ):
        Image.open(banner_tmp).convert("RGB").resize((2560, 1440), Image.LANCZOS).save(banner_path)
        banner_tmp.unlink(missing_ok=True)
    else:
        _fallback_banner(channel, banner_path)

    _watermark_from_profile(profile_path, watermark_path, accent=pal.get("accent", "#ffb454"))

    def _rel(p: Path) -> str:
        try:
            return p.resolve().relative_to(ROOT.resolve()).as_posix()
        except ValueError:
            return p.resolve().as_posix()

    assets = {
        "profile": _rel(profile_path),
        "banner": _rel(banner_path),
        "watermark": _rel(watermark_path),
    }
    return assets
