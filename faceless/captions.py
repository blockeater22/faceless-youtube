"""Kinetic word-by-word captions synced to narration timing.

Used by the stick-figure renderer (PIL) and the AI-image slideshow (ASS/ffmpeg).
Word boundaries are aligned to speech energy in the TTS wav when available, with
length-weighted fallback otherwise.
"""
from __future__ import annotations

import math
import re
import wave
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

# Rotating accent colours for the active spoken word.
KINETIC_PALETTE = (
    "#FF6B6B", "#FFD93D", "#6BCB77", "#4D96FF", "#FF6FD8", "#FFB454", "#9B59B6",
)


@dataclass
class WordTiming:
    word: str
    start: float
    end: float
    emphasis: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def parse_emphasis(raw: str | None) -> set[str]:
    if not raw:
        return set()
    out = set()
    for part in re.split(r"[,;/]+", raw):
        for w in part.split():
            clean = w.strip(".,!?\"'").lower()
            if clean:
                out.add(clean)
    return out


def _norm(word: str) -> str:
    return word.strip(".,!?\"'").lower()


def _word_weight(word: str) -> float:
    core = _norm(word) or word
    w = max(1.0, len(core))
    if word.endswith((".", "!", "?")):
        w += 1.8
    elif word.endswith(","):
        w += 0.9
    elif core in {"ai", "you", "your", "why", "how", "what", "if"}:
        w += 0.6
    return w


def estimate_word_timings(
    text: str,
    duration: float,
    emphasis: str | None = None,
    *,
    lead_in: float = 0.04,
) -> list[WordTiming]:
    words = text.split()
    if not words:
        return []
    emph = parse_emphasis(emphasis)
    duration = max(0.12, duration)
    weights = [_word_weight(w) for w in words]
    total = sum(weights) or 1.0
    usable = max(0.08, duration - lead_in)
    t = lead_in
    out: list[WordTiming] = []
    for word, wt in zip(words, weights):
        seg = usable * (wt / total)
        out.append(WordTiming(word, t, t + seg, _norm(word) in emph))
        t += seg
    if out:
        out[-1].end = duration
    return out


def _read_mono_wav(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as w:
        sr = w.getframerate()
        nch = w.getnchannels()
        raw = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    if nch > 1:
        raw = raw.reshape(-1, nch).mean(axis=1).astype(np.int16)
    return raw.astype(np.float32), sr


def align_words_to_audio(
    words: list[str],
    weights: list[float],
    samples: np.ndarray,
    sr: int,
    duration: float,
    *,
    lead_in: float = 0.04,
) -> list[float]:
    """Return word start times (seconds) aligned to speech energy."""
    hop = max(1, int(sr * 0.02))
    n = max(1, len(samples) // hop)
    energy = np.zeros(n, dtype=np.float64)
    for i in range(n):
        chunk = samples[i * hop : (i + 1) * hop]
        if len(chunk):
            energy[i] = float(np.sqrt(np.mean(chunk * chunk)))
    if energy.max() <= 1e-6:
        return []
    thr = max(energy.max() * 0.07, 1.0)
    voiced = energy >= thr
    if not voiced.any():
        return []
    first = int(np.argmax(voiced))
    last = int(len(voiced) - 1 - np.argmax(voiced[::-1]))
    seg = energy[first : last + 1]
    cum = np.cumsum(seg)
    if cum[-1] <= 0:
        return []
    total_w = sum(weights) or 1.0
    hop_t = hop / sr
    t0 = first * hop_t
    t1 = min(duration, (last + 1) * hop_t)
    starts = [max(lead_in, t0)]
    running = 0.0
    for wt in weights[:-1]:
        running += wt
        target = running / total_w
        idx = int(np.searchsorted(cum / cum[-1], target, side="right"))
        idx = min(idx, len(seg) - 1)
        starts.append(min(duration, t0 + idx * hop_t))
    for i in range(1, len(starts)):
        starts[i] = max(starts[i], starts[i - 1] + 0.03)
    if starts[-1] >= duration:
        scale = (duration - lead_in) / max(1e-6, starts[-1] - lead_in)
        starts = [lead_in + (s - lead_in) * scale for s in starts]
    return starts[: len(words)]


def build_word_timings(
    wav_path: str | Path | None,
    text: str,
    duration: float,
    emphasis: str | None = None,
) -> list[WordTiming]:
    words = text.split()
    if not words:
        return []
    emph = parse_emphasis(emphasis)
    duration = max(0.12, duration)
    weights = [_word_weight(w) for w in words]
    bounds: list[float] | None = None
    if wav_path and Path(wav_path).exists():
        try:
            samples, sr = _read_mono_wav(Path(wav_path))
            bounds = align_words_to_audio(words, weights, samples, sr, duration)
        except Exception:
            bounds = None
    if not bounds or len(bounds) != len(words):
        est = estimate_word_timings(text, duration, emphasis)
        return est
    out: list[WordTiming] = []
    for i, word in enumerate(words):
        start = bounds[i]
        end = bounds[i + 1] if i + 1 < len(words) else duration
        out.append(WordTiming(word, start, end, _norm(word) in emph))
    return out


def visible_word_count(timings: list[WordTiming], t: float) -> int:
    if not timings:
        return 0
    n = 0
    for wt in timings:
        if t >= wt.start - 1e-6:
            n += 1
        else:
            break
    return n


def active_word_index(timings: list[WordTiming], t: float) -> int:
    n = visible_word_count(timings, t)
    return max(0, n - 1)


def word_progress(timings: list[WordTiming], t: float) -> float:
    """0..1 progress through the currently spoken word."""
    idx = active_word_index(timings, t)
    if not timings:
        return 0.0
    wt = timings[idx]
    span = max(1e-6, wt.end - wt.start)
    return max(0.0, min(1.0, (t - wt.start) / span))


def _hex_rgb(value) -> tuple[int, int, int]:
    if isinstance(value, (list, tuple)) and len(value) >= 3:
        return tuple(int(v) for v in value[:3])  # type: ignore[return-value]
    s = str(value).lstrip("#")
    return tuple(int(s[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _palette_colors(style, cfg: dict) -> list[tuple[int, int, int]]:
    custom = cfg.get("palette") or cfg.get("colors")
    if custom:
        return [_hex_rgb(c) for c in custom]
    accent = _hex_rgb(style.color(cfg.get("accent", "accent")))
    return [_hex_rgb(c) for c in KINETIC_PALETTE] + [accent]


def draw_kinetic_caption(
    frame,
    text: str,
    local_t: float,
    spoken_dur: float,
    size,
    mindim: int,
    style,
    *,
    font_loader,
    emphasis: str | None = None,
    word_timings: list[WordTiming] | list[dict] | None = None,
) -> None:
    """Draw cumulative word-by-word captions with a multi-colour active word."""
    if not text:
        return
    from PIL import Image, ImageDraw

    if word_timings and word_timings and isinstance(word_timings[0], dict):
        timings = [WordTiming(**wt) for wt in word_timings]
    elif word_timings:
        timings = list(word_timings)  # type: ignore[arg-type]
    else:
        timings = estimate_word_timings(text, spoken_dur, emphasis)

    if not timings:
        return

    w, h = size
    cfg = style.caption or {}
    fs = int(cfg.get("size", 0.058) * mindim)
    font = font_loader(max(8, fs))
    max_w = w * 0.88
    n_vis = visible_word_count(timings, local_t)
    if n_vis <= 0:
        return
    vis = timings[:n_vis]
    newest = n_vis - 1
    wprog = word_progress(timings, local_t)

    lines: list[list[WordTiming]] = []
    cur: list[WordTiming] = []
    for wt in vis:
        trial = " ".join(w.word for w in cur + [wt])
        if font.getlength(trial) > max_w and cur:
            lines.append(cur)
            cur = [wt]
        else:
            cur.append(wt)
    if cur:
        lines.append(cur)

    line_h = int(fs * 1.32)
    block_h = line_h * len(lines)
    base_y = (0.78 if h >= w else 0.84) * h - block_h / 2
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    ink = style.color(cfg.get("color", "#ffffff"))
    palette = _palette_colors(style, cfg)
    stroke = max(2, fs // 10)
    idx = 0

    for li, line in enumerate(lines):
        total = font.getlength(" ".join(wt.word for wt in line))
        x = (w - total) / 2
        y = base_y + li * line_h
        for wt in line:
            is_active = idx == newest
            if is_active:
                col = palette[idx % len(palette)]
                if wt.emphasis:
                    col = style.color("accent")
            else:
                col = ink
            if is_active and wprog < 0.35:
                scale = 1.0 + math.sin(wprog * math.pi / 0.35) * 0.28
                pop_font = font_loader(int(fs * scale))
                off_y = y - (int(fs * scale) - fs) / 2
                pop_x = x - (pop_font.getlength(wt.word) - font.getlength(wt.word)) / 2
                angle = math.sin(wprog * math.pi * 3) * 4.0
                word_img = Image.new(
                    "RGBA",
                    (max(4, int(pop_font.getlength(wt.word) * 1.6)), int(line_h * 1.6)),
                    (0, 0, 0, 0),
                )
                wd = ImageDraw.Draw(word_img)
                wd.text(
                    (word_img.width / 2, word_img.height / 2),
                    wt.word,
                    font=pop_font,
                    fill=col + (255,),
                    stroke_width=int(stroke * scale),
                    stroke_fill=(0, 0, 0, 235),
                    anchor="mm",
                )
                word_img = word_img.rotate(angle, resample=Image.BICUBIC, expand=False)
                layer.alpha_composite(
                    word_img,
                    (
                        int(pop_x + font.getlength(wt.word) / 2 - word_img.width / 2),
                        int(off_y + fs / 2 - word_img.height / 2),
                    ),
                )
            else:
                d.text(
                    (x, y),
                    wt.word,
                    font=font,
                    fill=col + (255,),
                    stroke_width=stroke,
                    stroke_fill=(0, 0, 0, 235),
                )
            x += font.getlength(wt.word + " ")
            idx += 1
    frame.alpha_composite(layer)


def _ass_time(seconds: float) -> str:
    h, rem = divmod(max(0.0, seconds), 3600)
    m, s = divmod(rem, 60)
    cs = int(round((s % 1) * 100))
    return f"{int(h)}:{int(m):02d}:{int(s):02d}.{cs:02d}"


def _ass_color(rgb: tuple[int, int, int]) -> str:
    r, g, b = rgb
    return f"&H{b:02x}{g:02x}{r:02x}"


def write_ass_karaoke(
    segments: list[dict],
    path: Path,
    *,
    width: int,
    height: int,
    font_size: int = 52,
    font_name: str = "Bangers",
    margin_v: int = 72,
    palette: list[str] | None = None,
) -> None:
    """Write an ASS file with per-word karaoke + multi-colour tags for ffmpeg."""
    colors = [_hex_rgb(c) for c in (palette or KINETIC_PALETTE)]
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},&H00FFFFFF,&H000088FF,&H00101010,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,40,40,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    for seg in segments:
        text = seg.get("text", "").strip()
        if not text:
            continue
        start = float(seg["start"])
        end = float(seg["end"])
        spoken = float(seg.get("spoken_dur") or max(0.12, end - start))
        emph = seg.get("caption_emphasis")
        timings = seg.get("word_timings")
        if timings and isinstance(timings[0], dict):
            wts = [WordTiming(**wt) for wt in timings]
        elif timings:
            wts = list(timings)
        else:
            wts = build_word_timings(seg.get("wav"), text, spoken, emph)
        if not wts:
            continue
        parts = []
        for i, wt in enumerate(wts):
            cs = max(1, int(round((wt.end - wt.start) * 100)))
            if wt.emphasis:
                col = _ass_color(_hex_rgb("#FFB454"))
            else:
                col = _ass_color(colors[i % len(colors)])
            parts.append(f"{{\\1c{col}\\k{cs}}}{wt.word}")
        payload = " ".join(parts)
        lines.append(
            f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Default,,0,0,0,,{payload}\n"
        )
    path.write_text("".join(lines), encoding="utf-8")
