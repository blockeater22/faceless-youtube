"""Kokoro voice catalog and preview helpers for the local UI."""
from __future__ import annotations

from pathlib import Path

from faceless.model import Voice
from faceless.tts import synth

ROOT = Path(__file__).resolve().parent.parent
PREVIEW_DIR = ROOT / "output" / "voice_previews"

# Curated English voices for YouTube narration (ids must exist in voices-v1.0.bin).
VOICE_GROUPS: list[dict] = [
    {
        "label": "American — male",
        "voices": [
            {"id": "am_liam", "name": "Liam"},
            {"id": "am_michael", "name": "Michael"},
            {"id": "am_onyx", "name": "Onyx"},
            {"id": "am_adam", "name": "Adam"},
            {"id": "am_echo", "name": "Echo"},
            {"id": "am_eric", "name": "Eric"},
        ],
    },
    {
        "label": "American — female",
        "voices": [
            {"id": "af_heart", "name": "Heart"},
            {"id": "af_bella", "name": "Bella"},
            {"id": "af_sarah", "name": "Sarah"},
            {"id": "af_nova", "name": "Nova"},
            {"id": "af_river", "name": "River"},
            {"id": "af_sky", "name": "Sky"},
        ],
    },
    {
        "label": "British — male",
        "voices": [
            {"id": "bm_george", "name": "George"},
            {"id": "bm_daniel", "name": "Daniel"},
            {"id": "bm_lewis", "name": "Lewis"},
        ],
    },
    {
        "label": "British — female",
        "voices": [
            {"id": "bf_emma", "name": "Emma"},
            {"id": "bf_alice", "name": "Alice"},
            {"id": "bf_lily", "name": "Lily"},
        ],
    },
]

_NAME_BY_ID: dict[str, str] = {
    v["id"]: v["name"]
    for group in VOICE_GROUPS
    for v in group["voices"]
}


def voice_name(voice_id: str) -> str:
    return _NAME_BY_ID.get(voice_id) or voice_id.split("_", 1)[-1].replace("_", " ").title()


def preview_line(voice_id: str) -> str:
    return f"Hello Creator, I am {voice_name(voice_id)}."


def catalog_for_api() -> dict:
    return {"groups": VOICE_GROUPS, "default": "am_liam"}


def known_voice_ids() -> set[str]:
    return set(_NAME_BY_ID)


def ensure_preview(voice_id: str, speed: float = 1.0) -> Path:
    """Synthesize (or return cached) preview wav for ``voice_id``."""
    if voice_id not in known_voice_ids():
        raise ValueError(f"unknown voice: {voice_id}")
    speed = max(0.5, min(2.0, float(speed)))
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    key = f"{voice_id}_{speed:.2f}".replace(".", "p")
    out = PREVIEW_DIR / f"{key}.wav"
    if out.exists() and out.stat().st_size > 1000:
        return out
    voice = Voice(
        backend="kokoro",
        kokoro_voice=voice_id,
        kokoro_speed=speed,
        gap=0.0,
        polish=True,
    )
    synth(preview_line(voice_id), out, voice)
    return out
