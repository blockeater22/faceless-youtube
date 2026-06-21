"""Pipeline-wide paths and tunables."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = REPO_ROOT / "assets"
MODELS_DIR = REPO_ROOT / "models"  # third-party checkpoints; gitignored


@dataclass
class VoiceConfig:
    model_name: str = "tts_models/multilingual/multi-dataset/xtts_v2"
    language: str = "en"


@dataclass
class AvatarConfig:
    # "sadtalker": single reference frame + audio -> animated head (works from any
    # one still, so a 15s clip is plenty — we just pick the sharpest frame).
    # "wav2lip": re-times the mouth on the *original* looped face clip, keeping
    # your real head motion but constrained to ~15s of footage looping.
    engine: str = "sadtalker"
    fps: int = 25
    still_mode: bool = True
    enhancer: str = "gfpgan"


@dataclass
class ComposeConfig:
    resolution: tuple[int, int] = (1920, 1080)
    fps: int = 30
    caption_font: str = "assets/fonts/Inter-Bold.ttf"
    caption_font_size: int = 64
    music_volume_db: float = -22.0
    voice_volume_db: float = 0.0
    logo_path: str | None = None


@dataclass
class StudioConfig:
    anthropic_model: str = "claude-sonnet-4-6"
    target_seconds: int = 60
    work_dir: Path = field(default_factory=lambda: Path("output/_work"))
    out_dir: Path = field(default_factory=lambda: Path("output"))
    voice: VoiceConfig = field(default_factory=VoiceConfig)
    avatar: AvatarConfig = field(default_factory=AvatarConfig)
    compose: ComposeConfig = field(default_factory=ComposeConfig)

    @property
    def anthropic_api_key(self) -> str | None:
        return os.environ.get("ANTHROPIC_API_KEY")
