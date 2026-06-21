"""SRT caption generation from script segments + their synthesized audio durations.

Pure/stdlib only — no ffmpeg or model deps — so it's fully unit-testable.
"""
from __future__ import annotations

from dataclasses import dataclass

MAX_WORDS_PER_CAPTION = 8


def format_timestamp(seconds: float) -> str:
    if seconds < 0:
        raise ValueError("timestamp must be non-negative")
    total_ms = round(seconds * 1000)
    hours, rem_ms = divmod(total_ms, 3_600_000)
    minutes, rem_ms = divmod(rem_ms, 60_000)
    secs, ms = divmod(rem_ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def chunk_words(text: str, max_words: int = MAX_WORDS_PER_CAPTION) -> list[str]:
    words = text.split()
    return [
        " ".join(words[i : i + max_words])
        for i in range(0, len(words), max_words)
    ] or [text]


@dataclass
class Cue:
    start: float
    end: float
    text: str


def build_cues(segments: list[tuple[str, float]]) -> list[Cue]:
    """segments: list of (text, duration_seconds), in playback order."""
    cues: list[Cue] = []
    clock = 0.0
    for text, duration in segments:
        chunks = chunk_words(text)
        per_chunk = duration / len(chunks)
        for chunk in chunks:
            cues.append(Cue(start=clock, end=clock + per_chunk, text=chunk))
            clock += per_chunk
    return cues


def render_srt(cues: list[Cue]) -> str:
    lines = []
    for i, cue in enumerate(cues, start=1):
        lines.append(str(i))
        lines.append(f"{format_timestamp(cue.start)} --> {format_timestamp(cue.end)}")
        lines.append(cue.text)
        lines.append("")
    return "\n".join(lines)


def build_srt(segments: list[tuple[str, float]]) -> str:
    return render_srt(build_cues(segments))
