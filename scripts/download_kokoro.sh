#!/usr/bin/env bash
# Fetch the Kokoro-82M ONNX weights + voice pack used by the "kokoro" TTS
# backend (faceless/tts.py). Not committed to git - run this once per machine.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/.models/kokoro"
mkdir -p "$DIR"
BASE="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
curl -L --fail -o "$DIR/kokoro-v1.0.onnx" "$BASE/kokoro-v1.0.onnx"
curl -L --fail -o "$DIR/voices-v1.0.bin" "$BASE/voices-v1.0.bin"
echo "kokoro model files installed in $DIR"
