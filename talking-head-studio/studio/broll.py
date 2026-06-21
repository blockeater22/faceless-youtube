"""Pick b-roll footage for a 'broll' segment and time it to the narration audio.

Looks for filename matches in `assets/broll/` first (drop your own stock
clips there, named with the keywords you expect to search, e.g.
`city-skyline-01.mp4`). Falls back to a plain color card so the pipeline
never breaks on a missing asset — swap in a stock-footage API call here
later if you want fully automatic sourcing.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from .config import ComposeConfig


def find_local_clip(keywords: list[str], broll_dir: Path) -> Path | None:
    candidates = list(broll_dir.glob("*.mp4"))
    for keyword in keywords:
        key = keyword.lower().replace(" ", "-")
        for clip in candidates:
            if key in clip.stem.lower():
                return clip
    return None


def build_fallback_card(out_path: Path, duration: float, config: ComposeConfig, color: str = "0x1a1a2e") -> Path:
    """A plain color card, used when no matching b-roll clip is found."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    w, h = config.resolution
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=c={color}:s={w}x{h}:d={duration}:r={config.fps}",
            str(out_path),
        ],
        check=True,
        capture_output=True,
    )
    return out_path


def select_broll(keywords: list[str], duration: float, broll_dir: Path, work_dir: Path, config: ComposeConfig) -> Path:
    clip = find_local_clip(keywords, broll_dir)
    if clip is not None:
        return clip
    fallback_name = f"fallback_{'-'.join(keywords) or 'card'}.mp4"
    return build_fallback_card(work_dir / fallback_name, duration, config)
