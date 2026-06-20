"""ffmpeg discovery + small audio utilities shared by TTS and the renderer."""
from __future__ import annotations

import json
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def ffmpeg_exe() -> str:
    """Prefer system ffmpeg; fall back to the pip-bundled binary."""
    sys_ff = shutil.which("ffmpeg")
    if sys_ff:
        return sys_ff
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("ffmpeg not found (install ffmpeg or `pip install imageio-ffmpeg`)") from exc


@lru_cache(maxsize=1)
def ffprobe_exe() -> str | None:
    return shutil.which("ffprobe")


def run(args: list[str]) -> None:
    proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError(
            f"command failed ({proc.returncode}): {' '.join(args[:3])} ...\n"
            + proc.stderr.decode("utf-8", "ignore")[-1500:]
        )


def duration(path: str | Path) -> float:
    """Length of an audio/video file in seconds."""
    probe = ffprobe_exe()
    if probe:
        out = subprocess.run(
            [probe, "-v", "error", "-show_entries", "format=duration",
             "-of", "json", str(path)],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        ).stdout
        try:
            return float(json.loads(out)["format"]["duration"])
        except Exception:
            pass
    # fall back to ffmpeg's null muxer
    proc = subprocess.run([ffmpeg_exe(), "-i", str(path), "-f", "null", "-"],
                          stderr=subprocess.PIPE)
    for line in reversed(proc.stderr.decode("utf-8", "ignore").splitlines()):
        if "time=" in line:
            ts = line.split("time=")[1].split(" ")[0]
            h, m, s = ts.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    return 0.0


def make_silence(path: str | Path, seconds: float, sr: int = 44100) -> None:
    run([ffmpeg_exe(), "-y", "-f", "lavfi", "-i",
         f"anullsrc=r={sr}:cl=stereo", "-t", f"{max(0.01, seconds):.3f}",
         "-c:a", "pcm_s16le", str(path)])


def pad_to(src: str | Path, dst: str | Path, seconds: float, sr: int = 44100) -> None:
    """Re-encode ``src`` to exactly ``seconds`` (trim or pad with silence)."""
    run([ffmpeg_exe(), "-y", "-i", str(src),
         "-af", f"apad,atrim=0:{seconds:.3f},asetpts=N/SR/TB",
         "-ar", str(sr), "-ac", "2", "-c:a", "pcm_s16le", str(dst)])


def concat(parts: list[str | Path], dst: str | Path) -> None:
    """Concatenate same-format wavs via the concat demuxer."""
    dst = Path(dst)
    listfile = dst.with_suffix(".txt")
    listfile.write_text("".join(f"file '{Path(p).resolve()}'\n" for p in parts))
    run([ffmpeg_exe(), "-y", "-f", "concat", "-safe", "0",
         "-i", str(listfile), "-c", "copy", str(dst)])
    listfile.unlink(missing_ok=True)
