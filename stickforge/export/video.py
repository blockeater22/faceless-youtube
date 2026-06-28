"""Optional MP4 export via a SVG rasterizer + ffmpeg.

Rasterization is delegated to whatever is available (cairosvg, then
rsvg-convert, then Inkscape); video muxing to ffmpeg. When none are present the
caller gets a clear :class:`VideoUnavailable` instead of a crash — the HTML
player remains the always-available path.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


class VideoUnavailable(RuntimeError):
    """Raised when no rasterizer/ffmpeg toolchain is available."""


def _rasterizer():
    try:
        import cairosvg  # noqa: F401
        return "cairosvg"
    except Exception:
        pass
    if shutil.which("rsvg-convert"):
        return "rsvg-convert"
    if shutil.which("inkscape"):
        return "inkscape"
    return None


def _svg_to_png(svg: str, png_path: Path, rasterizer: str) -> None:
    if rasterizer == "cairosvg":
        import cairosvg
        cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=str(png_path))
    elif rasterizer == "rsvg-convert":
        subprocess.run(["rsvg-convert", "-o", str(png_path)],
                       input=svg.encode("utf-8"), check=True)
    elif rasterizer == "inkscape":
        svg_path = png_path.with_suffix(".svg")
        svg_path.write_text(svg, encoding="utf-8")
        subprocess.run(["inkscape", str(svg_path), "--export-type=png",
                        "--export-filename", str(png_path)], check=True)


def write_video(frames: list[str], out_path: str | Path, fps: int = 24) -> Path:
    rasterizer = _rasterizer()
    if rasterizer is None or not shutil.which("ffmpeg"):
        raise VideoUnavailable(
            "MP4 export needs a SVG rasterizer (cairosvg / rsvg-convert / "
            "inkscape) and ffmpeg. None were found — use the HTML player "
            "(write_html_player) or install: pip install cairosvg + apt ffmpeg.")

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for i, svg in enumerate(frames):
            _svg_to_png(svg, tmp / f"f_{i:05d}.png", rasterizer)
        subprocess.run([
            "ffmpeg", "-y", "-framerate", str(fps),
            "-i", str(tmp / "f_%05d.png"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", str(out),
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out
