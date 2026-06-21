"""Voice cloning + per-segment synthesis via Coqui TTS (XTTS v2).

XTTS clones a voice from a few seconds of reference audio with no
fine-tuning step, so the user's audio sample can be used directly as the
`speaker_wav` on every synthesis call.

Requires a GPU for reasonable speed and the `TTS` package
(`pip install TTS`, see ../docs/SETUP.md). Importing this module does not
require GPU/model weights; only `ClonedVoice.synth` does.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import VoiceConfig


@dataclass
class ClonedVoice:
    speaker_wav: Path
    config: VoiceConfig
    _tts: object = None  # lazily-constructed TTS.api.TTS instance

    def _ensure_loaded(self) -> None:
        if self._tts is not None:
            return
        from TTS.api import TTS  # heavy import; deferred until first use

        self._tts = TTS(self.config.model_name)

    def synth(self, text: str, out_path: Path) -> Path:
        """Synthesize `text` in the cloned voice, writing a wav to `out_path`."""
        self._ensure_loaded()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        self._tts.tts_to_file(
            text=text,
            speaker_wav=str(self.speaker_wav),
            language=self.config.language,
            file_path=str(out_path),
        )
        return out_path


def clone_voice(speaker_wav: Path, config: VoiceConfig) -> ClonedVoice:
    if not speaker_wav.exists():
        raise FileNotFoundError(f"voice sample not found: {speaker_wav}")
    return ClonedVoice(speaker_wav=speaker_wav, config=config)
