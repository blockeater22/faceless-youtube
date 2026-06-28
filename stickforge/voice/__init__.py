"""Voice + lip-sync.

Two pieces, both usable without an audio toolchain:

  * lipsync — turn a line of text into a stream of mouth shapes (visemes) timed
    to a duration, so the mouth flaps in sync with speech. This drives the
    expression's ``mouth_open``/``mouth_curve`` and needs no audio at all.
  * engine — a pluggable TTS interface (a Registry of backends). The default
    ``silent`` backend just models timing (duration from word count); real
    backends (espeak/piper/elevenlabs) register here to produce actual audio.
"""
from .lipsync import visemes_for, VISEME_OPEN
from .engine import VoiceClip, VOICES, say, estimate_duration

__all__ = ["visemes_for", "VISEME_OPEN", "VoiceClip", "VOICES", "say",
           "estimate_duration"]
