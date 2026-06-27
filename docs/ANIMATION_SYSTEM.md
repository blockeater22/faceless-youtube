# Animation system — architecture, decisions, roadmap

How the Shorts pipeline is built, why it's built that way, and what's worth
doing next. This is the engineering map for the stickman/whiteboard engine and
the SOP-driven generator that sit behind the published shorts.

## Pipeline at a glance

```
topic dict ─▶ scripting_sop (validate) ─▶ generate_sop_shorts (storyboard)
                                                    │
                                       direction (face/pose/prop inference)
                                                    ▼
                                          stories/<slug>.json
                                                    │
                          lint_script (SOP gate) ───┤
                                                    ▼
                         faceless.render  ──▶  output/<slug>_9x16.mp4
                         make_thumbnail   ──▶  output/<slug>_thumb.png
```

## Modules (single responsibility each)

| Module | Owns |
|---|---|
| `faceless/draw.py` | Low-level inked/wobble strokes; **stroke-reveal** (`reveal` arclength truncation) for the whiteboard draw-on |
| `faceless/figures.py` | Stick-figure skeleton + poses, faces (emotion brows/mouths), blink, sequential draw-on order |
| `faceless/effects.py` | Emotion/motion **glyphs** (sparkle, sweat, anger, shock, thought-?, speed lines), auto-derived from face/pose |
| `faceless/anim.py` | Keyframe sampling + easings + pose blending |
| `faceless/render.py` | Frame composition: background, props, actors (blink/breathe/draw-on/effects), virtual **camera** (Ken-Burns), captions, hook card, watermark; ffmpeg mux |
| `faceless/scenery.py`, `icons.py` | Colourful object/icon props |
| `faceless/model.py` | Story schema (`Style`, `Voice`, `Scene`, `Script`) + JSON loading |
| `scripts/scripting_sop.py`*| The Scripting SOP encoded as hard rules + the validator |
| `scripts/direction.py` | Sentence → `infer_face` / `infer_pose` / `infer_prop` (keyword-driven, deterministic) |
| `scripts/generate_sop_shorts.py` | Storyboards a topic into a per-sentence scene list (framing, duo staging, camera) |
| `scripts/lint_script.py` | CI-style gate: a story must pass the SOP before it renders |
| `scripts/make_thumbnail.py` | Composes the bold colour-bar + complete-character thumbnail |

\* `scripting_sop` lives in `faceless/` and is imported by the scripts.

## Key design decisions & tradeoffs

- **SOP as code, not a doc.** `validate_topic` mechanically fails non-compliant
  scripts (hook length, banned phrases, specificity spike, question-CTA, title
  formula). *Why:* the content-mill drift came from a doc nobody enforced under
  volume. *Tradeoff:* rules can reject a good line on a technicality — kept the
  ranges loose to limit false positives.
- **Direction is keyword-driven, not an LLM call.** Deterministic, instant,
  unit-testable. *Tradeoff:* misses nuance a model would catch; mitigated by a
  broad, ordered keyword table and consecutive-pose de-duplication.
- **Backward-compatible engine extensions.** `beat`/`camera`/`draw_on`/`hook_y`
  all default to off, so the ~95 pre-existing stories render unchanged
  (verified by the render smoke test on both schemas).
- **Whiteboard draw-on gated by `style.draw_on`.** Off by default; the SOP style
  opts in. *Why:* the scribe look is a per-brand choice, not a global change.
- **Per-sentence sub-scenes.** Each sentence is its own shot (fresh pose, prop,
  camera, framing, redraw) so the visual changes every ~3–4s. *Tradeoff:* more
  scenes = longer renders; acceptable for 30–40s shorts.

## Quality features implemented

Effect glyphs · hero-size centred composition · auto-blink + idle breathing ·
whiteboard stroke-reveal with marker cursor · scroll-stop hook (shake + pulse) ·
per-sentence pacing · narration-synced pose + metaphor prop · two-character
contrast staging · rule-of-thirds shot framing · bold colour-bar hook/thumbnail ·
proportional (approx word-sync) captions · coloured shirt + hands · richer prop
vocabulary (eye/mask/battery) with cross-scene de-dup · procedural sound design
(pop/whoosh/ding) + optional ducked music bed.

## Known limitations

- **Stick-figure art ceiling.** Single-weight line figures; no coloured
  clothing, hands, or turning. Extreme close-ups don't hold up.
- **No sound design.** No music bed or SFX (audio/voice is the owner's call).
- **Caption timing is chunk-based**, not word-level forced-alignment, so
  emphasis can land a beat off the spoken word.
- **Props skew to a small icon set**; abstract psychology lines sometimes repeat
  the brain icon.
- **No type-checking in CI yet** (mypy available, not wired).

## Roadmap (highest leverage first)

Done since first draft: sound design, proportional caption sync, prop
vocabulary, coloured shirt + hands. Remaining:

1. **True word-level caption sync** via a forced aligner (whisperx/aeneas) for
   exact per-word emphasis — current timing is proportional, not aligned.
2. **Shot-scale variety:** medium vs. closer framing on the emotional payoff,
   not just horizontal position.
3. **Music bed:** ship with a cleared default track (user-provided) so `sfx`
   stories get a bed automatically, not just SFX.
4. **Character art:** turning/profile poses, simple legs-as-shapes, so the
   figure can walk/face directions instead of always front-on.
5. **Wire mypy + a SessionStart hook** so `pytest`/`ruff` run on every web session.

## Running the gates

```
pytest                 # unit + render smoke tests
ruff check faceless scripts tests
python scripts/lint_script.py "stories/*.json"   # SOP gate
```
