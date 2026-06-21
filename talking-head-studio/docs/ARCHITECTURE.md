# Architecture

```
topic ─▶ script_gen (LLM) ─▶ Script { avatar/broll segments }
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                                            ▼
      voice_clone (XTTS)                            (per segment)
      synth each segment's                                │
      narration in your voice                             │
              │                                            │
              ▼                                            ▼
     avatar segments ──▶ face_animate          broll segments ──▶ broll.select_broll
     (SadTalker or Wav2Lip)                     + dub narration audio onto the clip
              │                                            │
              └─────────────────────┬─────────────────────┘
                                     ▼
                          compose (ffmpeg):
                          normalize → concat → burn captions
                          → mix music → overlay logo
                                     ▼
                              output/<title>.mp4
```

## Why only the intro/outro use your face

A single 15s clip is enough for a one-shot avatar model (SadTalker needs
only one still frame; Wav2Lip can loop the clip) to produce a believable
*short* talking-head segment, but not enough source motion to carry a full
60s+ video without visible looping artifacts. The script generator
(`studio/script_gen.py`) enforces this by always opening and closing on an
`avatar` segment and keeping the body as voiceover-over-b-roll.

## Swapping pieces

Every stage is a separate module with a narrow interface, so any one piece
can be swapped without touching the others:

- `script_gen.py` — swap the LLM (currently Anthropic) or hand-write scripts
  matching the `Script`/`Segment` schema directly.
- `voice_clone.py` — swap XTTS for ElevenLabs/OpenVoice by implementing the
  same `clone_voice(path, config) -> object with .synth(text, out_path)`.
- `face_animate.py` — swap SadTalker/Wav2Lip for a hosted avatar API.
- `broll.py` — currently matches local filenames; swap in a stock-footage
  API (Pexels, Pixabay) by replacing `find_local_clip`.
- `compose.py` — pure ffmpeg command builders; no model code, easy to test
  and easy to replace with a different compositor.
