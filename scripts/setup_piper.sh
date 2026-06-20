#!/usr/bin/env bash
# One-time setup for the bold neural narrator (Piper). Run on your own machine
# (needs HuggingFace access for the voice download).
#
#   bash scripts/setup_piper.sh                 # installs + grabs en_US-ryan-high
#   bash scripts/setup_piper.sh en_US-joe-medium # a different voice
#
# Then just render normally - the sample story already points at
# voices/en_US-ryan-high.onnx:
#   python -m faceless build stories/what_if_unmade_choices.json
set -e

VOICE="${1:-en_US-ryan-high}"
cd "$(dirname "$0")/.."

# use the project venv if present
[ -d .venv ] && . .venv/bin/activate

echo "==> installing piper-tts"
pip install -q piper-tts

echo "==> downloading voice: $VOICE  ->  ./voices/"
mkdir -p voices
python -m piper.download_voices "$VOICE" --data-dir voices

echo
echo "Done. Bold narrator voices worth trying (re-run with the name):"
echo "  en_US-ryan-high   warm, confident American male  (default)"
echo "  en_GB-alan-medium deep, calm British male"
echo "  en_US-joe-medium  deep American male"
echo
echo "Render with it:"
echo "  python -m faceless build stories/what_if_unmade_choices.json"
echo "  # or override per-render:"
echo "  python -m faceless build <story.json> --voice piper --piper-model voices/${VOICE}.onnx"
