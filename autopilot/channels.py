"""Multi-channel brand registry.

Each channel is a self-contained brand identity so one engine can run 10+ faceless
channels with *consistent figures and palette per channel* and a distinct look
across channels. A channel bundles:

- ``palette``   — background / ink / accent / muted (figures use ``ink``, props use
                  ``accent``), so every video on a channel shares the same colours.
- ``figure``    — scale (embiggen), wobble and grain, so the hand-drawn figure reads
                  identically across that channel's whole catalogue.
- ``voice``     — Kokoro voice + speed (the channel's narrator).
- ``persona``   — fed into the scriptwriter system prompt so the writing stays on-brand.
- ``rotation`` / ``tags`` / ``hashtags`` / ``cta_style`` — topic + metadata defaults.

Channels live in ``autopilot/channels.json`` (auto-seeded from PRESETS on first use).
The default channel is **Inklings** (@Inklings1).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANNELS_PATH = Path(__file__).resolve().parent / "channels.json"
BRANDING_DIR = ROOT / "branding"

# Sensible defaults so a partial channel definition still renders.
DEFAULTS: dict = {
    "id": "channel",
    "name": "Channel",
    "handle": "@channel",
    "persona": (
        "calm, warm, second-person narration about the mind and meaning; plain "
        "language; short sentences that each land on their own."
    ),
    "palette": {
        "background": "#0e1320",
        "ink": "#f2ede1",
        "accent": "#ffb454",
        "muted": "#6f7791",
    },
    "figure": {"embiggen": 1.42, "wobble": 1.7, "grain": 0.05, "scenery": True,
               "transition": 0.35, "pace": 3.0},
    "voice": {"kokoro_voice": "am_liam", "kokoro_speed": 0.95},
    # Vivid accent colours cycled across props/labels so the screen stays lively.
    "colors": ["#ff5a5f", "#ffb454", "#22c1a4", "#4d8bff", "#c879ff", "#ff8fab", "#7ed957"],
    "default_length": "3-5",
    "default_format": "16:9",
    "default_style": "stick",
    "rotation": ["whatif", "howto", "otheryou", "reflection"],
    "tag_suffix": ["stick figure animation", "deep thoughts"],
    "hashtags": ["#deepthoughts", "#stickfigure", "#mindfulness"],
    "cta_style": "warm",
    "thumb": "bubbles",
}

# Default channel preset (Inklings @Inklings1).
PRESETS: list[dict] = [
    {
        "id": "inklings",
        "name": "Inklings",
        "handle": "@Inklings1",
        "persona": (
            "Inklings — hand-drawn, black-background stick-figure videos about the mind, "
            "meaning, time, and the quietly mind-bending. Calm, warm, emotionally resonant; "
            "second person; plain language; short sentences that each land on their own."
        ),
        "palette": {"background": "#0e1320", "ink": "#f2ede1", "accent": "#ffb454", "muted": "#6f7791"},
        "figure": {"embiggen": 1.42, "wobble": 1.7, "grain": 0.05, "scenery": True},
        "voice": {"kokoro_voice": "am_liam", "kokoro_speed": 0.92},
        "rotation": ["whatif", "reflection", "otheryou", "howto"],
        "tag_suffix": ["stick figure animation", "deep thoughts", "philosophy"],
        "hashtags": ["#deepthoughts", "#philosophy", "#mindfulness", "#sonder"],
        "cta_style": "warm",
        "thumb": "bubbles",
    },
]

_HEX_RE = re.compile(r"^#?[0-9a-fA-F]{6}$")


def _slugify_id(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "", name.lower())
    return s[:32] or "channel"


def _merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = {**out[k], **v}
        else:
            out[k] = v
    return out


def _normalize(raw: dict) -> dict:
    """Fill any missing fields from DEFAULTS so every channel is render-ready."""
    ch = _merge(DEFAULTS, raw or {})
    ch["id"] = _slugify_id(ch.get("id") or ch.get("name") or "channel")
    ch["palette"] = _merge(DEFAULTS["palette"], raw.get("palette", {}) if raw else {})
    ch["figure"] = _merge(DEFAULTS["figure"], raw.get("figure", {}) if raw else {})
    ch["voice"] = _merge(DEFAULTS["voice"], raw.get("voice", {}) if raw else {})
    return ch


def _load_raw() -> list[dict]:
    if CHANNELS_PATH.exists():
        try:
            data = json.loads(CHANNELS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list) and data:
                return data
        except Exception:  # noqa: BLE001
            pass
    CHANNELS_PATH.write_text(json.dumps(PRESETS, indent=2), encoding="utf-8")
    return list(PRESETS)


def list_channels() -> list[dict]:
    """All channels, presets merged with any user-added/overridden ones."""
    by_id: dict[str, dict] = {c["id"]: _normalize(c) for c in PRESETS}
    for raw in _load_raw():
        ch = _normalize(raw)
        by_id[ch["id"]] = ch
    return list(by_id.values())


def get_channel(channel_id: str | None) -> dict:
    if not channel_id:
        return list_channels()[0]
    cid = _slugify_id(channel_id)
    for ch in list_channels():
        if ch["id"] == cid:
            return ch
    return list_channels()[0]


def brand_dir(channel_id: str) -> Path:
    return BRANDING_DIR / _slugify_id(channel_id)


def _asset_paths(channel: dict) -> dict[str, str]:
    assets = channel.get("assets") or {}
    return {k: str(v) for k, v in assets.items() if v}


def add_channel(data: dict) -> dict:
    """Create or update a user channel, generate brand assets, and persist."""
    if not (data.get("name") or data.get("id")):
        raise ValueError("channel needs a name")
    generate_assets = data.get("generate_assets", True)
    image_provider = data.get("image_provider") or data.get("provider") or "auto"
    ch = _normalize(data)
    for key in ("background", "ink", "accent", "muted"):
        val = ch["palette"].get(key, "")
        if not _HEX_RE.match(str(val)):
            raise ValueError(f"palette.{key} must be a #rrggbb hex colour")
        ch["palette"][key] = "#" + str(val).lstrip("#")
    if generate_assets:
        from autopilot import channel_architect

        print(f"[channel] Generating profile, banner, and watermark for {ch['name']} …")
        ch["assets"] = channel_architect.generate_brand_assets(
            ch,
            brand_dir(ch["id"]),
            provider=image_provider,
        )
    elif data.get("assets"):
        ch["assets"] = data["assets"]
    existing = _load_raw()
    out, replaced = [], False
    for raw in existing:
        if _slugify_id(raw.get("id") or raw.get("name") or "") == ch["id"]:
            out.append(ch)
            replaced = True
        else:
            out.append(raw)
    if not replaced:
        out.append(ch)
    CHANNELS_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return ch


def apply_to_config(cfg: dict, channel: dict) -> dict:
    """Overlay a channel's brand onto a run config (palette, figure, voice, defaults)."""
    cfg = dict(cfg)
    pal = channel["palette"]
    cfg["channel_id"] = channel["id"]
    cfg["channel_name"] = channel["name"]
    cfg["handle"] = channel.get("handle", cfg.get("handle", ""))
    cfg["persona"] = channel.get("persona", "")
    cfg["cta_style"] = channel.get("cta_style", "warm")
    cfg["palette"] = pal
    cfg["background"] = pal["background"]
    cfg["ink"] = pal["ink"]
    cfg["accent"] = pal["accent"]
    cfg["muted"] = pal["muted"]
    fig = channel["figure"]
    cfg["embiggen"] = fig.get("embiggen", cfg.get("embiggen", 1.42))
    cfg["wobble"] = fig.get("wobble", 1.7)
    cfg["grain"] = fig.get("grain", 0.05)
    cfg["scenery"] = fig.get("scenery", True)
    cfg["transition"] = fig.get("transition", DEFAULTS["figure"]["transition"])
    cfg["pace"] = fig.get("pace", DEFAULTS["figure"]["pace"])
    cfg["colors"] = channel.get("colors") or DEFAULTS["colors"]
    cfg["rotation"] = channel.get("rotation", cfg.get("rotation"))
    cfg["tag_suffix"] = channel.get("tag_suffix", cfg.get("tag_suffix"))
    cfg["channel_hashtags"] = channel.get("hashtags", [])
    cfg["thumb_default"] = channel.get("thumb", "bubbles")
    assets = _asset_paths(channel)
    wm = assets.get("watermark")
    if wm:
        p = ROOT / wm if not Path(wm).is_absolute() else Path(wm)
        if p.exists():
            cfg["logo"] = str(p.resolve())
    return cfg
