"""Animate a talking-head clip from the user's face video + a synthesized line.

Two engines, both wrapping third-party repos that must be installed
separately (see ../docs/SETUP.md) — this module only shells out to them:

- "sadtalker": animates a single still frame to match the audio. We extract
  the sharpest frame from the user's 15s clip and feed that + audio in;
  SadTalker handles head motion, blinks and lip-sync from there.
- "wav2lip": re-times the mouth on the *original* face video (looped/trimmed
  to the audio length) so the user's real head motion is kept, at the cost
  of being constrained to ~15s of source motion.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from .config import AvatarConfig


def extract_best_frame(face_video: Path, out_path: Path, sample_fps: float = 2.0) -> Path:
    """Pick the sharpest frame from `face_video` as the SadTalker reference still."""
    import numpy as np
    from PIL import Image

    frames_dir = out_path.parent / "_frame_candidates"
    frames_dir.mkdir(parents=True, exist_ok=True)
    pattern = frames_dir / "f_%04d.png"
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(face_video), "-vf", f"fps={sample_fps}", str(pattern)],
        check=True,
        capture_output=True,
    )

    candidates = sorted(frames_dir.glob("f_*.png"))
    if not candidates:
        raise RuntimeError(f"no frames extracted from {face_video}")

    def sharpness(img_path: Path) -> float:
        arr = np.asarray(Image.open(img_path).convert("L"), dtype=float)
        gy, gx = np.gradient(arr)
        return float((gx**2 + gy**2).mean())

    best = max(candidates, key=sharpness)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    best.replace(out_path)
    return out_path


def animate_sadtalker(
    face_image: Path, audio_path: Path, out_dir: Path, config: AvatarConfig, sadtalker_dir: Path
) -> Path:
    """Run SadTalker's inference.py to produce a talking-head clip."""
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(sadtalker_dir / "inference.py"),
        "--driven_audio", str(audio_path),
        "--source_image", str(face_image),
        "--result_dir", str(out_dir),
        "--fps", str(config.fps),
    ]
    if config.still_mode:
        cmd.append("--still")
    if config.enhancer:
        cmd += ["--enhancer", config.enhancer]
    subprocess.run(cmd, check=True, cwd=str(sadtalker_dir))

    produced = sorted(out_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime)
    if not produced:
        raise RuntimeError(f"SadTalker produced no output in {out_dir}")
    return produced[-1]


def animate_wav2lip(
    face_video: Path, audio_path: Path, out_path: Path, wav2lip_dir: Path, checkpoint: Path
) -> Path:
    """Run Wav2Lip inference to re-sync the mouth on the original face video."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(wav2lip_dir / "inference.py"),
        "--checkpoint_path", str(checkpoint),
        "--face", str(face_video),
        "--audio", str(audio_path),
        "--outfile", str(out_path),
    ]
    subprocess.run(cmd, check=True, cwd=str(wav2lip_dir))
    return out_path
