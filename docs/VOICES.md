# Voiceover without an API key — open-source TTS options

You **don't need ElevenLabs**. There are excellent free, open-source neural
text-to-speech models you can run locally with no key. Here's the landscape,
ranked for a faceless storytelling channel, plus exactly how to wire each into
this engine via the story's `voice` block.

## TL;DR recommendation

1. **Piper** — best free/offline default. CPU-fast, ~30–60 MB voices, genuinely
   good quality, permissive license. Use this on your own machine.
2. **Kokoro-82M** — newer, even more natural, tiny, **Apache-2.0** (safe for
   monetized videos). Great if you want a step up from Piper.
3. **Coqui XTTS-v2** — best quality + voice cloning, but heavier (GPU preferred)
   and **non-commercial license** ⚠️ — avoid for a monetized channel.
4. **Festival HTS** — the smoothest *zero-download* offline option; what this
   repo uses by default in-sandbox (espeak/MBROLA is the bare-minimum fallback).

> These are **TTS models**, not chat LLMs. (You *can* separately use an
> open-source LLM like Llama/Mistral to *write* scripts — but for turning text
> into a voice, you want a TTS model.)

---

## 1. Piper  ·  free · offline · no key · ★ recommended

[`rhasspy/piper`](https://github.com/OHF-Voice/piper1-gpl) — fast neural TTS that
runs on CPU.

```bash
pip install piper-tts
# download a voice (this pulls weights from HuggingFace):
python -m piper.download_voices en_US-lessac-medium
#   -> en_US-lessac-medium.onnx  +  en_US-lessac-medium.onnx.json
```

Then in your story:

```jsonc
"voice": {
  "backend": "piper",
  "piper_model": "voices/en_US-lessac-medium.onnx",
  "piper_length": 1.05,        // >1 = slower / more deliberate
  "polish": true
}
```

Good story-narrator voices: `en_US-lessac-medium`, `en_US-ryan-high`,
`en_GB-alan-medium`, `en_US-amy-medium`. Browse + listen:
<https://rhasspy.github.io/piper-samples/>.

The backend is already implemented in `faceless/tts.py` (`_piper`).

## 2. Kokoro-82M  ·  free · offline · Apache-2.0

[`hexgrad/Kokoro-82M`](https://github.com/hexgrad/kokoro) — 82M-param model,
remarkably natural, very permissive license.

```bash
pip install kokoro soundfile
```
```python
from kokoro import KPipeline
import soundfile as sf
pipe = KPipeline(lang_code="a")            # 'a' = American English
audio = next(pipe("Your narration line.", voice="af_heart"))[2]
sf.write("line.wav", audio, 24000)
```

To use it here, add a `_kokoro` backend in `faceless/tts.py` mirroring `_piper`
(synthesize the line to `out_wav`; `_finalize` handles the rest). ~15 lines.

## 3. Coqui TTS / XTTS-v2  ·  free · voice-clone · ⚠ non-commercial

[`coqui-ai/TTS`](https://github.com/coqui-ai/TTS) — top quality and clones a
voice from ~6 s of reference audio.

```bash
pip install TTS
```
```python
from TTS.api import TTS
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
tts.tts_to_file(text="...", speaker_wav="ref.wav", language="en", file_path="line.wav")
```
The **XTTS-v2 weights are CPML (non-commercial)** — fine for testing, **not** for
a monetized channel. Coqui also ships permissively-licensed VITS models
(`tts_models/en/ljspeech/vits`) that are commercial-safe.

## 4. Festival HTS  ·  this repo's offline default · no downloads from HF

The **HTS** Festival voices are *statistical-parametric* — they don't splice
recorded diphones, so they sound noticeably **smoother / more fluent** than
espeak or MBROLA (no choppy "buffering" seams). Pure apt, no key, no HF.

```bash
sudo apt-get install -y festival festvox-us-slt-hts
```
```jsonc
"voice": { "backend": "festival", "voice": "cmu_us_slt_arctic_hts", "rate": 150, "polish": true }
```
`rate` is reused as a pace control (lower = slower). `cmu_us_slt_arctic_hts` is a
clear US-English female voice.

## 5. espeak-ng + MBROLA  ·  the bare-minimum fallback

No model downloads either, but choppier than Festival. The `polish` chain helps.
```bash
sudo apt-get install -y espeak-ng mbrola mbrola-us1 mbrola-us2 mbrola-us3
```
```jsonc
"voice": { "backend": "espeak", "voice": "mb-us2", "rate": 142, "pitch": 40, "polish": true }
```
`mb-us1` female, `mb-us2`/`mb-us3` male. Plain espeak (no MBROLA) is `"en-us+m3"`.

---

## Why this repo's sample uses Festival (not Piper)

This project was built inside a sandbox whose network policy **blocks
HuggingFace** (`x-deny-reason: host_not_allowed`) — and HF is where Piper,
Kokoro, Coqui and friends host their weights. So the committed sample is voiced
with **Festival HTS**, the smoothest fully-offline option that needs no downloads.

**On your own machine, switch to Piper** (section 1) for another quality jump —
just change the `voice` block; nothing else needs to change.

## Tuning for "fluent, not choppy"
The biggest fixes if a voice sounds like it's buffering/stuttering:
- **No reverb/echo** in post — it comb-filters speech. (This repo's `polish`
  chain uses only EQ + gentle compression + loudness-normalise.)
- **No big inter-word gaps** (we dropped espeak's `-g`).
- Prefer a **statistical/neural** voice (Festival HTS, Piper, Kokoro) over
  diphone concatenation (MBROLA) when you can.

## Production tip
Whatever backend you pick, keep `polish:true`. It EQs, adds a touch of room, and
loudness-normalises to ~-16 LUFS (the YouTube/social sweet spot) so your
voiceover sounds "produced" rather than raw.
