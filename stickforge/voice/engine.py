"""A pluggable text-to-speech interface.

The engine models *timing* always (so lip-sync and beat durations line up) and
produces *audio* only if a backend can. The default ``silent`` backend makes no
sound — it just estimates how long the line takes to say. Real backends
(espeak, piper, ElevenLabs, …) register into :data:`VOICES` and return an audio
path; the rest of the pipeline (lip-sync, subtitles) is identical either way.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from ..core.registry import Registry

VOICES: "Registry" = Registry("voice-backend")


@dataclass
class VoiceClip:
    text: str
    duration: float
    audio: str | None = None        # path to rendered audio, if any
    backend: str = "silent"


def estimate_duration(text: str, wpm: float = 150.0) -> float:
    """Reading time for a line at ``wpm`` words/min, with a short tail pause."""
    words = max(1, len(re.findall(r"[A-Za-z0-9']+", text)))
    return max(0.7, words / (wpm / 60.0) + 0.35)


@VOICES.register("silent")
def _silent(text: str, **kw) -> VoiceClip:
    return VoiceClip(text=text, duration=estimate_duration(text), audio=None,
                     backend="silent")


def say(text: str, backend: str = "silent", **kw) -> VoiceClip:
    """Synthesize (or, for ``silent``, just time) a line of dialogue."""
    fn = VOICES.get(backend) if backend in VOICES else VOICES.get("silent")
    return fn(text, **kw)
