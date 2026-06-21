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
        elif backend == "festival":
            _festival(text, raw, voice)
        elif backend == "piper":
            _piper(text, raw, voice)
        elif backend == "gtts":
            _gtts(text, raw, voice)
        elif backend == "elevenlabs":
            _elevenlabs(text, raw, voice)
        else:
            raise ValueError(f"unknown tts backend: {voice.backend}")
    except Exception as exc:
        # never let a missing neural model kill a render: degrade gracefully
        # (piper/elevenlabs -> festival -> espeak) keeping the requested polish.
        fb = _fallback_voice(voice, exclude={backend})
        if fb is None:
            raise
        print(f"  [tts] '{backend}' unavailable ({exc}); falling back to '{fb.backend}'")
        (_festival if fb.backend == "festival" else _espeak)(text, raw, fb)

    _finalize(raw, out_wav, voice)
    raw.unlink(missing_ok=True)


def _fallback_voice(voice: Voice, exclude: set[str]) -> Voice | None:
    """Pick the best still-available offline backend, skipping ones already tried."""
    if "festival" not in exclude and shutil.which("text2wave"):
        return Voice(backend="festival", voice="cmu_us_slt_arctic_hts",
                     rate=voice.rate, polish=voice.polish, gap=voice.gap)
    if "espeak" not in exclude and (shutil.which("espeak-ng") or shutil.which("espeak")):
        return Voice(backend="espeak", voice="mb-us2", rate=voice.rate,
                     pitch=voice.pitch, polish=voice.polish, gap=voice.gap)
    return None


# --------------------------------------------------------------------------- #
# Backends
# --------------------------------------------------------------------------- #
def _espeak(text: str, out: Path, voice: Voice) -> None:
    exe = shutil.which("espeak-ng") or shutil.which("espeak")
    if not exe:
        raise RuntimeError("espeak-ng not installed (apt-get install espeak-ng)")
    subprocess.run(
        [exe, "-v", voice.voice, "-s", str(voice.rate), "-p", str(voice.pitch),
         "-w", str(out), text],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def _festival(text: str, out: Path, voice: Voice) -> None:
    """Festival TTS - the HTS voices are statistical-parametric (no diphone
    seams), so they sound smoother/more fluent than espeak or MBROLA. Offline,
    no key. Install: apt-get install festival festvox-us-slt-hts
    voice.voice = festival voice name, e.g. 'cmu_us_slt_arctic_hts'."""
    if not shutil.which("text2wave"):
        raise RuntimeError("festival not installed (apt-get install festival festvox-us-slt-hts)")
    vname = voice.voice or "cmu_us_slt_arctic_hts"
    # reuse `rate` as a pace control: lower wpm -> longer Duration_Stretch (slower)
    stretch = max(0.7, min(1.6, 165.0 / max(60, voice.rate)))
    eval_expr = f"(begin (voice_{vname}) (Parameter.set 'Duration_Stretch {stretch:.3f}))"
    proc = subprocess.run(["text2wave", "-o", str(out), "-eval", eval_expr],
                          input=text.encode("utf-8"),
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if proc.returncode != 0 or not out.exists() or out.stat().st_size < 256:
        raise RuntimeError(f"festival synthesis failed for voice {vname!r}")


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
        # NB: no reverb/echo - it smears speech and reads as "buffering".
        # loudnorm is deliberately NOT applied per-clip: on short (~3s) TTS
        # lines its gain-ramp pumps audibly, which also reads as "buffering" -
        # it's applied once on the full concatenated track in build_audio().
        chain = ("highpass=f=75,lowpass=f=7600,"
                 "acompressor=threshold=-16dB:ratio=2.5:attack=20:release=260,"
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
