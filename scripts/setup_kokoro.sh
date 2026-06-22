#!/usr/bin/env bash
# Install Kokoro-82M (onnx) and fetch the model + voices into ./voices.
# Kokoro is #1 on the TTS Arena for natural narration — our channel voice.
set -e

python -m pip install --upgrade kokoro-onnx >/dev/null

mkdir -p voices
cd voices

BASE="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
[ -f kokoro-v1.0.onnx ] || { echo "downloading kokoro-v1.0.onnx ..."; curl -fL -o kokoro-v1.0.onnx "$BASE/kokoro-v1.0.onnx"; }
[ -f voices-v1.0.bin ]  || { echo "downloading voices-v1.0.bin ...";  curl -fL -o voices-v1.0.bin  "$BASE/voices-v1.0.bin"; }

echo "Kokoro ready in ./voices (af_heart, bm_george, am_michael, af_bella, ...)."
echo "Set the voice in autopilot/config.json -> kokoro_voice, or a story's voice block."
