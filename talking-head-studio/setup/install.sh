#!/usr/bin/env bash
# One-time setup: clones the third-party avatar engines and fetches their
# checkpoints. Run from the talking-head-studio/ directory. Requires a CUDA
# GPU for usable speed — see ../docs/SETUP.md.
set -euo pipefail

THIRD_PARTY_DIR="third_party"
mkdir -p "$THIRD_PARTY_DIR"

echo "== Python deps =="
pip install -r requirements.txt

echo "== SadTalker =="
if [ ! -d "$THIRD_PARTY_DIR/SadTalker" ]; then
  git clone https://github.com/OpenTalker/SadTalker.git "$THIRD_PARTY_DIR/SadTalker"
fi
pip install -r "$THIRD_PARTY_DIR/SadTalker/requirements.txt"
bash "$THIRD_PARTY_DIR/SadTalker/scripts/download_models.sh"

echo "== Wav2Lip (optional second avatar engine) =="
if [ ! -d "$THIRD_PARTY_DIR/Wav2Lip" ]; then
  git clone https://github.com/Rudrabha/Wav2Lip.git "$THIRD_PARTY_DIR/Wav2Lip"
fi
pip install -r "$THIRD_PARTY_DIR/Wav2Lip/requirements.txt"
echo "Download wav2lip_gan.pth manually from the Wav2Lip README into"
echo "  $THIRD_PARTY_DIR/Wav2Lip/checkpoints/wav2lip_gan.pth"
echo "(no direct download link is published by the authors)."

echo "== done =="
