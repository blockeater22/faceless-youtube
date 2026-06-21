"""Small wav helpers used to drive timing for captions and b-roll trimming."""
from __future__ import annotations

import wave
from pathlib import Path


def wav_duration_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as wf:
        return wf.getnframes() / float(wf.getframerate())
