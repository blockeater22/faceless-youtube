"""Pluggable text-to-speech.

Each backend turns one line of narration into a wav file. The default
(``espeak``) is fully offline; ``elevenlabs`` is wired for final-channel quality
once you set ``ELEVENLABS_API_KEY``. Swap backends in the story's ``voice`` block.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import wave
from pathlib import Path

from .media import ffmpeg_exe, run
from .model import Voice


def synth(text: str, out_wav: str | Path, voice: Voice) -> None:
    """Synthesize ``text`` to a 44.1k stereo wav at ``out_wav``."""
    out_wav = Path(out_wav)
    raw = out_wav.with_name(out_wav.stem + "_raw.wav")
    text = text.strip()
    if not text or voice.backend == "none":
        _silence(out_wav, 0.6)
        return

    backend = voice.backend.lower()
    try:
        if backend == "espeak":
            _espeak(text, raw, voice)
        elif backend == "piper":
            _piper(text, raw, voice)
        elif backend == "gtts":
            _gtts(text, raw, voice)
        elif backend == "elevenlabs":
            _elevenlabs(text, raw, voice)
        else:
            raise ValueError(f"unknown tts backend: {voice.backend}")
    except Exception as exc:
        # never let a missing online voice kill a render - fall back to espeak
        if backend != "espeak" and shutil.which("espeak-ng"):
            print(f"  [tts] {backend} failed ({exc}); falling back to espeak-ng")
            _espeak(text, raw, voice)
        else:
            raise

    _finalize(raw, out_wav, voice)
    raw.unlink(missing_ok=True)


# --------------------------------------------------------------------------- #
# Backends
# --------------------------------------------------------------------------- #
def _espeak(text: str, out: Path, voice: Voice) -> None:
    exe = shutil.which("espeak-ng") or shutil.which("espeak")
    if not exe:
        raise RuntimeError("espeak-ng not installed (apt-get install espeak-ng)")
    subprocess.run(
        [exe, "-v", voice.voice, "-s", str(voice.rate), "-p", str(voice.pitch),
         "-g", "6", "-w", str(out), text],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def _piper(text: str, out: Path, voice: Voice) -> None:
    """Piper neural TTS - free, offline, no API key. Best free quality.

    On your own machine:  pip install piper-tts
    then fetch a voice (downloads from HuggingFace), e.g.:
        python -m piper.download_voices en_US-lessac-medium
    and point the story's voice.piper_model at the resulting .onnx file.
    """
    try:
        from piper import PiperVoice  # type: ignore
    except ImportError as exc:
        raise RuntimeError("piper not installed: `pip install piper-tts`") from exc
    model = voice.piper_model
    if not model or not Path(model).exists():
        raise RuntimeError(
            f"piper model not found: {model!r}. Download a voice (.onnx + .onnx.json) "
            "with `python -m piper.download_voices en_US-lessac-medium`."
        )
    pv = PiperVoice.load(model)
    with wave.open(str(out), "wb") as wf:
        try:
            pv.synthesize_wav(text, wf, length_scale=voice.piper_length)
        except (TypeError, AttributeError):
            pv.synthesize(text, wf)  # older piper-tts API


def _gtts(text: str, out: Path, voice: Voice) -> None:
    from gtts import gTTS  # type: ignore
    mp3 = out.with_suffix(".mp3")
    gTTS(text, lang=voice.lang).save(str(mp3))
    run([ffmpeg_exe(), "-y", "-i", str(mp3), str(out)])
    mp3.unlink(missing_ok=True)


def _elevenlabs(text: str, out: Path, voice: Voice) -> None:
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        raise RuntimeError("ELEVENLABS_API_KEY not set")
    from elevenlabs.client import ElevenLabs  # type: ignore
    client = ElevenLabs(api_key=key)
    audio = client.text_to_speech.convert(
        voice_id=voice.eleven_voice, model_id="eleven_multilingual_v2",
        text=text, output_format="mp3_44100_128",
    )
    mp3 = out.with_suffix(".mp3")
    with open(mp3, "wb") as fh:
        for chunk in audio:
            fh.write(chunk)
    run([ffmpeg_exe(), "-y", "-i", str(mp3), str(out)])
    mp3.unlink(missing_ok=True)


# --------------------------------------------------------------------------- #
# Post-processing
# --------------------------------------------------------------------------- #
def _finalize(raw: Path, out: Path, voice: Voice) -> None:
    """Add a trailing gap and (optionally) a 'warmth' chain so the offline
    voice sounds less brittle. Output is 44.1k stereo pcm."""
    if voice.polish:
        chain = ("highpass=f=85,lowpass=f=7900,"
                 "acompressor=threshold=-18dB:ratio=3:attack=8:release=180,"
                 "aecho=0.85:0.88:26:0.12,"
                 "loudnorm=I=-16:TP=-1.5:LRA=11,"
                 f"apad=pad_dur={voice.gap}")
    else:
        chain = f"apad=pad_dur={voice.gap}"
    run([ffmpeg_exe(), "-y", "-i", str(raw), "-af", chain,
         "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", str(out)])


def _silence(out: Path, seconds: float) -> None:
    with wave.open(str(out), "w") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(b"\x00\x00\x00\x00" * int(44100 * seconds))
