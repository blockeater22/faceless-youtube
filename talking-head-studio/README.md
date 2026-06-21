# talking-head-studio

Turn a **topic**, a **~15s clip of your face**, and **a short voice sample**
into a narrated marketing/blogging video: an LLM drafts the script, your
voice is cloned for narration, a talking-head model animates your face for
the hook and call-to-action, and the body runs as voiceover over b-roll —
all stitched together with ffmpeg into a captioned, scored final cut.

```
topic ──▶ script (LLM) ──▶ cloned voice (XTTS) ──▶ avatar (SadTalker/Wav2Lip)
                                                  └▶ b-roll + voiceover
                                                          │
                                                          ▼
                                          ffmpeg: concat + captions + music + logo
                                                          │
                                                          ▼
                                                  output/<title>.mp4
```

Open-source, self-hosted stack — no per-video API fees, but it needs a GPU
to run at a usable speed. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
for how the stages fit together and [docs/SETUP.md](docs/SETUP.md) to get
it running.

## Why your face only appears in the intro/outro

15 seconds of footage is plenty for a one-shot avatar model to render a
short, convincing talking-head clip — it is not enough source motion to
carry a full-length video without looping artifacts. The script generator
always opens and closes on an on-camera segment and uses voiceover-over-b-roll
for everything in between, which is also closer to how real marketing/vlog
content is cut.

## Quickstart

```bash
cd talking-head-studio
python3 -m venv .venv && . .venv/bin/activate
bash setup/install.sh
export ANTHROPIC_API_KEY=sk-...

python -m studio generate \
  --face my_face.mp4 \
  --voice-sample my_voice.wav \
  --topic "5 habits that quietly drain your savings" \
  --seconds 60
```

## Status

The orchestration, caption timing, script-JSON parsing, and all ffmpeg
command construction are unit tested (`pytest`, no GPU required). The
model-backed stages (voice cloning, avatar animation) are real wrappers
around Coqui XTTS / SadTalker / Wav2Lip but need a GPU + downloaded
checkpoints to exercise end-to-end — see [docs/SETUP.md](docs/SETUP.md).
