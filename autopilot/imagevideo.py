"""Render a script as an AI-image slideshow with Ken Burns motion + captions.

This is the 'image' visual style (vs. the procedural stick-figure engine in
faceless/). Per beat it:  synthesizes narration (faceless.tts, e.g. Kokoro
Liam)  ->  generates one image (autopilot.images: Pollinations/Cloudflare/HF)
->  makes a clip of exactly the narration's length with a slow zoom/pan.
Clips are concatenated, the voiceover muxed in, and captions burned on top.

No paid services: Pollinations needs no key, Kokoro runs locally.
"""
from __future__ import annotations

import json
import subprocess
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from autopilot import provider_router  # noqa: E402
from faceless import captions as kinetic_captions  # noqa: E402
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
    if beat.get("image_prompt"):
        return beat["image_prompt"]
    if beat.get("image"):
        return beat["image"]
    line = beat["narration"].strip().rstrip(".")
    return f"A symbolic, atmospheric scene illustrating: {line}"


# A strong shared anchor keeps every image in a video looking like one set:
# same medium, same palette discipline, clean background, no text artifacts.
DEFAULT_IMAGE_STYLE = (
    "consistent flat modern vector illustration, single cohesive art style across the "
    "whole series, bright bold colorful shapes on a clean white background, friendly, "
    "minimal, high contrast, crisp"
)
_IMAGE_NEGATIVE = "text, watermark, logo, blurry, deformed, extra limbs, photoreal clutter"


def _style_for(beat: dict, image_style: str | None) -> str | None:
    anchor = image_style.strip() if (image_style and image_style.strip()) else DEFAULT_IMAGE_STYLE
    parts = [p.strip() for p in (beat.get("visual_style"), anchor) if p and p.strip()]
    negative = beat.get("negative_prompt") or _IMAGE_NEGATIVE
    parts.append(f"Avoid: {negative}")
    return ". ".join(parts)


def _base_seed(title: str) -> int:
    """Stable per-video seed so a script reproduces, but each video has its own look."""
    import hashlib
    return int(hashlib.sha1((title or "video").encode("utf-8")).hexdigest()[:6], 16) % 100000


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


def _ffmpeg_filter_path(path: Path) -> str:
    """Escape a path for use inside an ffmpeg filter expression."""
    return path.resolve().as_posix().replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def _caption_font_name() -> str:
    bangers = ROOT / "faceless" / "fonts" / "Bangers-Regular.ttf"
    return "Bangers" if bangers.exists() else "DejaVu Sans"


def _spoken_duration(wav: Path, voice: Voice) -> float:
    gap = max(0.0, getattr(voice, "gap", 0.0))
    return max(0.12, _wav_dur(wav) - gap)


def _write_ass_captions(beats, wavs, spoken_durs, path: Path, *, width: int, height: int,
                        caption_size: int, voice: Voice) -> None:
    t = 0.0
    segments = []
    for b, wav, spoken in zip(beats, wavs, spoken_durs):
        dur = _wav_dur(wav)
        segments.append({
            "start": t,
            "end": t + dur,
            "spoken_dur": spoken,
            "text": b.get("narration", ""),
            "caption_emphasis": b.get("caption_emphasis") or "",
            "wav": str(wav),
            "word_timings": [
                wt.to_dict()
                for wt in kinetic_captions.build_word_timings(
                    wav,
                    b.get("narration", ""),
                    spoken,
                    b.get("caption_emphasis") or "",
                )
            ],
        })
        t += dur
    kinetic_captions.write_ass_karaoke(
        segments,
        path,
        width=width,
        height=height,
        font_size=caption_size,
        font_name=_caption_font_name(),
        margin_v=68 if height > width else 88,
    )


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
                       caption_size: int = 22,
                       provider_order: list[str] | tuple[str, ...] | None = None,
                       logo_path: str | Path | None = None) -> list[Path]:
    """Build slideshow video(s) from a {title, hook, beats} script. Returns paths."""
    voice = voice or Voice(backend="kokoro", kokoro_voice="am_liam", kokoro_speed=0.9)
    beats = script["beats"]
    outdir.mkdir(parents=True, exist_ok=True)
    work = outdir / "_imgwork"
    (work / "audio").mkdir(parents=True, exist_ok=True)
    (work / "img").mkdir(parents=True, exist_ok=True)

    base_seed = _base_seed(script.get("title", ""))

    # 1) narration + durations (shared across formats)
    print(f"Synthesizing {len(beats)} lines with {voice.backend}:{voice.kokoro_voice} ...")
    wavs, durs, spoken_durs = [], [], []
    for i, b in enumerate(beats):
        wav = work / "audio" / f"{i:03d}.wav"
        synth(b["narration"], wav, voice)
        wavs.append(wav)
        full = _wav_dur(wav)
        spoken = _spoken_duration(wav, voice)
        durs.append(full)
        spoken_durs.append(spoken)

    # 2) one master voiceover track (concat)
    concat_a = work / "audio_list.txt"
    concat_a.write_text("".join(f"file '{w.resolve()}'\n" for w in wavs))
    master_a = work / "voice.wav"
    run([ffmpeg_exe(), "-y", "-f", "concat", "-safe", "0", "-i", str(concat_a),
         "-c", "copy", str(master_a)])

    # 3) word-by-word ASS captions (shared kinetic typography engine)
    ass = work / "captions.ass"

    outputs = []
    for fmt in formats:
        w, h = SIZES.get(fmt, SIZES["16:9"])
        clip_dir = work / f"clips_{fmt.replace(':', 'x')}"
        clip_dir.mkdir(exist_ok=True)
        print(f"[{fmt}] generating {len(beats)} images via '{provider}' + Ken Burns ...")
        clips = []
        image_log = []
        for i, b in enumerate(beats):
            img = work / "img" / f"{fmt.replace(':', 'x')}_{i:03d}.png"
            if not img.exists():
                result = provider_router.generate_scene_image(
                    _image_prompt(b, script["title"]),
                    img,
                    width=w,
                    height=h,
                    provider=provider,
                    provider_order=provider_order,
                    style=_style_for(b, image_style),
                    model=image_model,
                    seed=base_seed + i,
                    cache_dir=work / "img_cache",
                )
                image_log.append({
                    "beat": i,
                    "provider": result.provider,
                    "cache_hit": result.cache_hit,
                    "prompt_hash": result.prompt_hash,
                })
            clip = clip_dir / f"{i:03d}.mp4"
            _ken_burns_clip(img, durs[i], w, h, fps, zoom_in=(i % 2 == 0), out=clip)
            clips.append(clip)

        concat_v = clip_dir / "list.txt"
        concat_v.write_text("".join(f"file '{c.resolve()}'\n" for c in clips))
        silent = clip_dir / "silent.mp4"
        run([ffmpeg_exe(), "-y", "-f", "concat", "-safe", "0", "-i", str(concat_v),
             "-c", "copy", str(silent)])

        # mux voiceover + burn word-by-word ASS captions
        slug = _slug(script["title"])
        out = outdir / f"{slug}_{fmt.replace(':', 'x')}.mp4"
        _write_ass_captions(
            beats, wavs, spoken_durs, ass,
            width=w, height=h, caption_size=max(36, caption_size), voice=voice,
        )
        wm = Path(logo_path) if logo_path else None
        if wm and not wm.is_absolute():
            wm = ROOT / wm
        _mux_with_captions(
            silent=silent,
            master_a=master_a,
            out=out,
            ass_path=_ffmpeg_filter_path(ass),
            fonts_dir=_ffmpeg_filter_path(ROOT / "faceless" / "fonts"),
            beats=beats,
            durs=durs,
            caption_size=max(36, caption_size),
            wm=wm if wm and wm.exists() else None,
            width=w,
            height=h,
        )
        outputs.append(out)
        (clip_dir / "image_log.json").write_text(
            json.dumps(image_log, indent=2), encoding="utf-8"
        )
        print(f"[{fmt}] -> {out.name}  ({out.stat().st_size/1e6:.1f} MB, "
              f"{sum(durs):.0f}s)")
    return outputs


def _subtitles_filter_missing(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "subtitles" in msg and ("no such filter" in msg or "filter not found" in msg)


def _mux_with_captions(
    *,
    silent: Path,
    master_a: Path,
    out: Path,
    ass_path: str,
    fonts_dir: str,
    beats: list,
    durs: list[float],
    caption_size: int,
    wm: Path | None,
    width: int,
    height: int,
) -> None:
    """Mux voiceover + ASS captions (+ optional watermark), with SRT fallback."""
    has_wm = bool(wm and wm.exists())
    scale = max(48, int(min(width, height) * 0.10))
    sub = f"subtitles=filename='{ass_path}':fontsdir='{fonts_dir}'"

    if has_wm:
        vf = (
            f"[0:v]{sub}[v0];"
            f"[2:v]scale={scale}:{scale}:force_original_aspect_ratio=decrease[wm];"
            f"[v0][wm]overlay=20:20:format=auto[vout]"
        )
        mux_cmd = [ffmpeg_exe(), "-y", "-i", str(silent), "-i", str(master_a), "-i", str(wm),
                   "-filter_complex", vf, "-map", "[vout]", "-map", "1:a:0", "-shortest",
                   "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                   "-c:a", "aac", "-b:a", "192k", str(out)]
    else:
        mux_cmd = [ffmpeg_exe(), "-y", "-i", str(silent), "-i", str(master_a),
                   "-vf", sub, "-map", "0:v:0", "-map", "1:a:0", "-shortest",
                   "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                   "-c:a", "aac", "-b:a", "192k", str(out)]

    try:
        run(mux_cmd)
        return
    except RuntimeError as exc:
        if not _subtitles_filter_missing(exc):
            raise
        print(f"  [captions] {ffmpeg_exe()} lacks subtitles filter; trying SRT fallback")

    srt = silent.parent.parent / "captions.srt"
    _write_srt(beats, durs, srt)
    style = (f"FontName=DejaVu Sans,Fontsize={caption_size},PrimaryColour=&H00FFFFFF,"
             f"OutlineColour=&H00101010,BorderStyle=1,Outline=2,Shadow=1,"
             f"Alignment=2,MarginV=60")
    srt_sub = f"subtitles=filename='{_ffmpeg_filter_path(srt)}':force_style='{style}'"
    if has_wm:
        vf = (
            f"[0:v]{srt_sub}[v0];"
            f"[2:v]scale={scale}:{scale}:force_original_aspect_ratio=decrease[wm];"
            f"[v0][wm]overlay=20:20:format=auto[vout]"
        )
        run([ffmpeg_exe(), "-y", "-i", str(silent), "-i", str(master_a), "-i", str(wm),
             "-filter_complex", vf, "-map", "[vout]", "-map", "1:a:0", "-shortest",
             "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "192k", str(out)])
    else:
        run([ffmpeg_exe(), "-y", "-i", str(silent), "-i", str(master_a),
             "-vf", srt_sub, "-map", "0:v:0", "-map", "1:a:0", "-shortest",
             "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "192k", str(out)])


def _slug(text: str) -> str:
    import re
    s = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return s[:48] or "video"
