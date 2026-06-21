"""ffmpeg command construction for the final assembly pass.

Every `build_*_cmd` function is a pure function returning an argv list —
no subprocess execution — so the command logic is unit-testable without
ffmpeg installed. `run()` is the only place that actually shells out.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from .config import ComposeConfig


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True)


def build_normalize_cmd(in_path: Path, out_path: Path, config: ComposeConfig) -> list[str]:
    """Scale/pad each clip to a common resolution+fps so concat doesn't choke."""
    w, h = config.resolution
    vf = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,fps={config.fps}"
    return [
        "ffmpeg", "-y", "-i", str(in_path),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-c:a", "aac",
        str(out_path),
    ]


def build_concat_cmd(concat_list_path: Path, out_path: Path) -> list[str]:
    return [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_list_path),
        "-c", "copy",
        str(out_path),
    ]


def write_concat_list(clip_paths: list[Path], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(f"file '{p.resolve()}'" for p in clip_paths) + "\n")
    return out_path


def build_caption_burn_cmd(in_path: Path, srt_path: Path, out_path: Path, config: ComposeConfig) -> list[str]:
    style = (
        f"FontName={Path(config.caption_font).stem},"
        f"FontSize={config.caption_font_size},"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,Outline=2,Alignment=2"
    )
    return [
        "ffmpeg", "-y", "-i", str(in_path),
        "-vf", f"subtitles={srt_path}:force_style='{style}'",
        "-c:a", "copy",
        str(out_path),
    ]


def build_music_mix_cmd(in_path: Path, music_path: Path, out_path: Path, config: ComposeConfig) -> list[str]:
    music_gain = f"volume={config.music_volume_db}dB"
    voice_gain = f"volume={config.voice_volume_db}dB"
    filter_complex = (
        f"[1:a]{music_gain},aloop=loop=-1:size=2e9[music];"
        f"[0:a]{voice_gain}[voice];"
        "[voice][music]amix=inputs=2:duration=first:dropout_transition=2[aout]"
    )
    return [
        "ffmpeg", "-y", "-i", str(in_path), "-i", str(music_path),
        "-filter_complex", filter_complex,
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac",
        "-shortest",
        str(out_path),
    ]


def build_logo_overlay_cmd(in_path: Path, logo_path: Path, out_path: Path) -> list[str]:
    return [
        "ffmpeg", "-y", "-i", str(in_path), "-i", str(logo_path),
        "-filter_complex", "overlay=W-w-30:30",
        "-c:a", "copy",
        str(out_path),
    ]
