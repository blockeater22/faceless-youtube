"""Render a script as an AI-image slideshow with Ken Burns motion + captions.

This is the 'image' visual style (vs. the procedural stick-figure engine in
faceless/). Per beat it:  synthesizes narration (faceless.tts, e.g. Kokoro
Liam)  ->  generates one image (autopilot.images: Pollinations/Cloudflare/HF)
->  makes a clip of exactly the narration's length with a slow zoom/pan.
Clips are concatenated, the voiceover muxed in, and captions burned on top.

No paid services: Pollinations needs no key, Kokoro runs locally.
"""
from __future__ import annotations

import subprocess
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from autopilot import images as _images  # noqa: E402
from faceless.media import ffmpeg_exe, run  # noqa: E402
from faceless.model import Voice  # noqa: E402
from faceless.tts import synth  # noqa: E402

# aspect -> (w, h). 16:9 long-form, 9:16 Shorts.
SIZES = {"16:9": (1280, 720), "9:16": (720, 1280)}


def _wav_dur(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / float(w.getframerate())


def _image_prompt(beat: dict, title: str) -> str:
    """A FLUX-friendly visual prompt for one beat. Prefer an explicit `image`
    field; otherwise build one from the narration (no people-by-name, no text)."""
    if beat.get("image"):
        return beat["image"]
    line = beat["narration"].strip().rstrip(".")
    return f"A symbolic, atmospheric scene illustrating: {line}"


def _srt_time(t: float) -> str:
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int((s % 1) * 1000):03d}"


def _wrap(text: str, width: int = 42) -> str:
    out, line = [], ""
    for word in text.split():
        if len(line) + len(word) + 1 > width:
            out.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    out.append(line)
    return "\\N".join(out[:3])  # ASS line break; cap at 3 lines


def _write_srt(beats, durs, path: Path) -> None:
    lines, t = [], 0.0
    for i, (b, d) in enumerate(zip(beats, durs), 1):
        lines.append(f"{i}\n{_srt_time(t)} --> {_srt_time(t + d)}\n"
                     f"{_wrap(b['narration'])}\n")
        t += d
    path.write_text("\n".join(lines), encoding="utf-8")


def _ken_burns_clip(img: Path, dur: float, w: int, h: int, fps: int,
                    zoom_in: bool, out: Path) -> None:
    frames = max(1, int(dur * fps))
    z = ("min(zoom+0.0006,1.14)" if zoom_in else "if(eq(on,1),1.14,max(zoom-0.0006,1.0))")
    vf = (f"scale={w*2}:{h*2}:force_original_aspect_ratio=increase,"
          f"crop={w*2}:{h*2},"
          f"zoompan=z='{z}':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
          f":s={w}x{h}:fps={fps},setsar=1,format=yuv420p")
    run([ffmpeg_exe(), "-y", "-loop", "1", "-i", str(img), "-t", f"{dur:.3f}",
         "-vf", vf, "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-pix_fmt", "yuv420p", str(out)])


def render_image_video(script: dict, outdir: Path, *, formats=("16:9",), fps: int = 24,
                       voice: Voice | None = None, provider: str = "pollinations",
                       image_style: str | None = None, image_model: str | None = None,
                       caption_size: int = 22) -> list[Path]:
    """Build slideshow video(s) from a {title, hook, beats} script. Returns paths."""
    voice = voice or Voice(backend="kokoro", kokoro_voice="am_liam", kokoro_speed=0.9)
    beats = script["beats"]
    outdir.mkdir(parents=True, exist_ok=True)
    work = outdir / "_imgwork"
    (work / "audio").mkdir(parents=True, exist_ok=True)
    (work / "img").mkdir(parents=True, exist_ok=True)

    # 1) narration + durations (shared across formats)
    print(f"Synthesizing {len(beats)} lines with {voice.backend}:{voice.kokoro_voice} ...")
    wavs, durs = [], []
    for i, b in enumerate(beats):
        wav = work / "audio" / f"{i:03d}.wav"
        synth(b["narration"], wav, voice)
        wavs.append(wav)
        durs.append(_wav_dur(wav))

    # 2) one master voiceover track (concat)
    concat_a = work / "audio_list.txt"
    concat_a.write_text("".join(f"file '{w.resolve()}'\n" for w in wavs))
    master_a = work / "voice.wav"
    run([ffmpeg_exe(), "-y", "-f", "concat", "-safe", "0", "-i", str(concat_a),
         "-c", "copy", str(master_a)])

    # 3) captions
    srt = work / "captions.srt"
    _write_srt(beats, durs, srt)

    outputs = []
    for fmt in formats:
        w, h = SIZES.get(fmt, SIZES["16:9"])
        clip_dir = work / f"clips_{fmt.replace(':', 'x')}"
        clip_dir.mkdir(exist_ok=True)
        print(f"[{fmt}] generating {len(beats)} images via '{provider}' + Ken Burns ...")
        clips = []
        for i, b in enumerate(beats):
            img = work / "img" / f"{fmt.replace(':', 'x')}_{i:03d}.png"
            if not img.exists():
                _images.generate_image(_image_prompt(b, script["title"]), img,
                                       width=w, height=h, provider=provider,
                                       style=image_style, model=image_model, seed=1000 + i)
            clip = clip_dir / f"{i:03d}.mp4"
            _ken_burns_clip(img, durs[i], w, h, fps, zoom_in=(i % 2 == 0), out=clip)
            clips.append(clip)

        concat_v = clip_dir / "list.txt"
        concat_v.write_text("".join(f"file '{c.resolve()}'\n" for c in clips))
        silent = clip_dir / "silent.mp4"
        run([ffmpeg_exe(), "-y", "-f", "concat", "-safe", "0", "-i", str(concat_v),
             "-c", "copy", str(silent)])

        # mux voiceover + burn captions
        slug = _slug(script["title"])
        out = outdir / f"{slug}_{fmt.replace(':', 'x')}.mp4"
        style = (f"FontName=DejaVu Sans,Fontsize={caption_size},PrimaryColour=&H00FFFFFF,"
                 f"OutlineColour=&H00101010,BorderStyle=1,Outline=2,Shadow=1,"
                 f"Alignment=2,MarginV=60")
        run([ffmpeg_exe(), "-y", "-i", str(silent), "-i", str(master_a),
             "-vf", f"subtitles={srt.as_posix()}:force_style='{style}'",
             "-map", "0:v:0", "-map", "1:a:0", "-shortest",
             "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "192k", str(out)])
        outputs.append(out)
        print(f"[{fmt}] -> {out.name}  ({out.stat().st_size/1e6:.1f} MB, "
              f"{sum(durs):.0f}s)")
    return outputs


def _slug(text: str) -> str:
    import re
    s = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return s[:48] or "video"
