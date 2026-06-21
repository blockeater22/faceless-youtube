"""End-to-end orchestration: topic + face video + voice sample -> final mp4.

generate() wires the other modules together in order. It needs a GPU,
the Anthropic API key, and SadTalker/Wav2Lip + Coqui TTS installed (see
../docs/SETUP.md) to actually run — none of that is exercised by the unit
tests, which instead cover each module's pure logic in isolation.
"""
from __future__ import annotations

from pathlib import Path

from . import broll, compose
from .audio import wav_duration_seconds
from .captions import build_srt
from .config import StudioConfig
from .face_animate import animate_sadtalker, animate_wav2lip, extract_best_frame
from .script_gen import Script, generate_script
from .voice_clone import clone_voice


def generate(
    face_video: Path,
    voice_sample: Path,
    topic: str,
    config: StudioConfig,
    sadtalker_dir: Path | None = None,
    wav2lip_dir: Path | None = None,
    wav2lip_checkpoint: Path | None = None,
    music_path: Path | None = None,
    broll_dir: Path = Path("assets/broll"),
) -> Path:
    work = config.work_dir
    work.mkdir(parents=True, exist_ok=True)

    script = generate_script(
        topic=topic,
        target_seconds=config.target_seconds,
        model=config.anthropic_model,
        api_key=config.anthropic_api_key,
    )

    voice = clone_voice(voice_sample, config.voice)

    best_frame = None
    if config.avatar.engine == "sadtalker":
        best_frame = extract_best_frame(face_video, work / "best_frame.png")

    clips: list[Path] = []
    timed_segments: list[tuple[str, float]] = []

    for i, segment in enumerate(script.segments):
        audio_path = voice.synth(segment.text, work / f"seg_{i:02d}.wav")
        duration = wav_duration_seconds(audio_path)
        timed_segments.append((segment.text, duration))

        if segment.kind == "avatar":
            if config.avatar.engine == "sadtalker":
                clip = animate_sadtalker(
                    best_frame, audio_path, work / f"avatar_{i:02d}", config.avatar, sadtalker_dir
                )
            else:
                clip = animate_wav2lip(
                    face_video, audio_path, work / f"avatar_{i:02d}.mp4", wav2lip_dir, wav2lip_checkpoint
                )
        else:
            raw_clip = broll.select_broll(segment.broll_keywords, duration, broll_dir, work, config.compose)
            clip = _dub_broll(raw_clip, audio_path, duration, work / f"broll_{i:02d}.mp4")

        normalized = work / f"norm_{i:02d}.mp4"
        compose.run(compose.build_normalize_cmd(clip, normalized, config.compose))
        clips.append(normalized)

    concat_list = compose.write_concat_list(clips, work / "concat.txt")
    assembled = work / "assembled.mp4"
    compose.run(compose.build_concat_cmd(concat_list, assembled))

    srt_path = work / "captions.srt"
    srt_path.write_text(build_srt(timed_segments))
    captioned = work / "captioned.mp4"
    compose.run(compose.build_caption_burn_cmd(assembled, srt_path, captioned, config.compose))

    current = captioned
    if music_path is not None:
        mixed = work / "mixed.mp4"
        compose.run(compose.build_music_mix_cmd(current, music_path, mixed, config.compose))
        current = mixed

    if config.compose.logo_path:
        final = config.out_dir / f"{_slugify(script.title)}.mp4"
        compose.run(compose.build_logo_overlay_cmd(current, Path(config.compose.logo_path), final))
    else:
        config.out_dir.mkdir(parents=True, exist_ok=True)
        final = config.out_dir / f"{_slugify(script.title)}.mp4"
        current.replace(final)

    return final


def _dub_broll(raw_clip: Path, audio_path: Path, duration: float, out_path: Path) -> Path:
    """Loop/trim a b-roll clip to `duration` and attach the narration audio."""
    import subprocess

    out_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", str(raw_clip),
            "-i", str(audio_path),
            "-map", "0:v", "-map", "1:a",
            "-t", str(duration),
            "-c:v", "libx264", "-c:a", "aac",
            str(out_path),
        ],
        check=True,
        capture_output=True,
    )
    return out_path


def _slugify(title: str) -> str:
    return "".join(c.lower() if c.isalnum() else "-" for c in title).strip("-")
