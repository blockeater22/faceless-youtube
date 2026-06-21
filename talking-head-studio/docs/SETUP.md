# Setup

## Requirements

- A CUDA GPU with **8GB+ VRAM** (SadTalker + XTTS are both usable on CPU
  only for short clips, but expect minutes-per-second of render time).
- `ffmpeg` on PATH.
- Python 3.10+.
- An `ANTHROPIC_API_KEY` environment variable (script generation).

## Install

```bash
cd talking-head-studio
python3 -m venv .venv && . .venv/bin/activate
bash setup/install.sh
```

This installs the Python deps, clones SadTalker + Wav2Lip into
`third_party/`, and downloads SadTalker's checkpoints. Wav2Lip's
`wav2lip_gan.pth` must be downloaded by hand per their README (the authors
don't publish a direct download link) into
`third_party/Wav2Lip/checkpoints/`.

## Inputs

- `--face`: a ~15s, well-lit, front-facing clip of you talking or just
  looking at the camera. Used to extract a reference still (SadTalker) or
  as the looped source clip (Wav2Lip).
- `--voice-sample`: 6-10 seconds of clean speech audio (wav), no background
  music or noise — this is what XTTS clones from.

## Run

```bash
export ANTHROPIC_API_KEY=sk-...
python -m studio generate \
  --face my_face.mp4 \
  --voice-sample my_voice.wav \
  --topic "5 habits that quietly drain your savings" \
  --seconds 60 \
  --music assets/music/bg.mp3 \
  --logo assets/branding/logo.png
```

Output lands in `output/<slugified-title>.mp4`. Intermediate files (synth
audio, per-segment clips, captions) are kept in `output/_work/` for
debugging and aren't deleted automatically.

## Running the tests

The pure logic (caption timing, script JSON parsing, ffmpeg command
building) has no GPU/model dependency and runs anywhere:

```bash
pip install pytest
pytest
```
