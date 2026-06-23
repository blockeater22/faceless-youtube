# Running locally on a MacBook Pro (M3, base)

The whole pipeline runs comfortably on an M3 — Kokoro is ~82M params (<2 GB) and renders
real-time-ish; the rest is Pillow + ffmpeg. Here's the one-time setup.

## 1. System tools (Homebrew)

```bash
# Homebrew (if you don't have it): https://brew.sh
brew install ffmpeg            # required: encodes the video + audio
brew install espeak-ng         # optional: last-resort offline voice fallback
```

> No `apt`/MBROLA needed on macOS — Kokoro is the voice, ffmpeg does the muxing.

## 2. Python environment

```bash
cd faceless-youtube
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## 3. Neural voice — Kokoro "Liam" (free, local, no key)

```bash
pip install kokoro-onnx
bash scripts/setup_kokoro.sh      # downloads kokoro-v1.0.onnx + voices-v1.0.bin into ./voices
```

The channel voice is set in `autopilot/config.json` (`"kokoro_voice": "am_liam"`,
`"kokoro_speed": 0.9`). Override per run with `--voice` / `--speed`.

> Apple-Silicon note: `kokoro-onnx` runs on CPU via onnxruntime and is plenty fast on M3.
> If you want the MLX-accelerated build later, see the `kokoro-mlx` project — not required.

## 4. Free Gemini key for scripts (recommended)

1. Get a key at https://aistudio.google.com/apikey
2. Export it (add to `~/.zshrc` to persist):

```bash
export GEMINI_API_KEY="your_key_here"
```

Without a key the scriptwriter falls back to the offline template (lower quality — fine to
test the pipeline, not for publishing). With a key it uses `gemini-2.5-flash` on the free tier.

## 5. Generate your first video

```bash
# stick-figure long-form (on-brand, fully offline once Kokoro is set up):
python -m autopilot.generate

# a 9:16 Short:
python -m autopilot.generate --shorts

# AI-image slideshow style (uses Pollinations — no key needed):
python -m autopilot.generate --style image --shorts

# your own idea + a deeper voice:
python -m autopilot.generate --topic "What if your phone showed why you really open it?" --voice am_michael
```

Output lands in `output/<slug>/`:
- `…_16x9.mp4` (or `_9x16.mp4`) — the video
- `<slug>.txt` — paste-ready **title / description / tags / hashtags**
- (stick style) a thumbnail in `branding/`

Review it, tweak the title, and upload manually in YouTube Studio. That human-review step is
deliberate — see `docs/RESEARCH.md` §1 on the 2026 AI-content rules.

## 6. (Optional) image providers with more headroom

Pollinations needs no key but is a shared free service. For volume/reliability:

```bash
# Cloudflare Workers AI (free tier ~10k neurons/day ≈ 100+ images):
export CF_ACCOUNT_ID="..."; export CF_API_TOKEN="..."
python -m autopilot.generate --style image --provider cloudflare

# Hugging Face serverless inference:
export HF_TOKEN="hf_..."
python -m autopilot.generate --style image --provider huggingface
```

## Troubleshooting
- **`ffmpeg not found`** → `brew install ffmpeg` (or `pip install imageio-ffmpeg` for a bundled one).
- **Kokoro model missing** → re-run `bash scripts/setup_kokoro.sh`; check `./voices/` has the two files.
- **Voice falls back to espeak** → Kokoro files/onnx not found; the render still completes, just robotic.
- **Pollinations slow / blank frames** → it's queuing; the code retries then uses a fallback card.
  Switch `--provider cloudflare` for reliability.
</content>
