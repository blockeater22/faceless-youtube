# Expressive Cartoon Character System — Research & Architecture

> Status: **RESEARCH + ARCHITECTURE ONLY. No character-system code written yet.**
> (The only code change shipped alongside this doc is the removal of the ray/burst
> line effects, per request — see §0.)
>
> Goal: replace the current geometric stick figure with a **hand-drawn doodle
> mascot** — clothing, hands, feet, eyebrows, real mouths, expressive faces and
> body language that sync to the script — entirely **procedurally in code** (no AI
> image generation).

---

## 0. Shipped now: rays removed

The floating-keyword/icon **ray & burst line effects** were removed because they
render as messy stringy lines in video. Props that previously requested
`effect: "rays"` or `"burst"` now fall back to a clean **soft glow halo**. The
opening **hook** sunburst was likewise replaced with a soft radial glow.

- `faceless/render.py` → `_draw_glow_effect()` now only draws the blurred glow
  halo; the target-seeking and radial line loops are gone.
- `faceless/render.py` → `_draw_hook()` burst changed from triangular ray wedges
  to a soft elliptical glow.

No other behaviour changed. All 32 pipeline tests pass.

---

# PART 1 — Current System Report (full pipeline trace)

### Pipeline at a glance

```
topic ─▶ scriptwriter (Gemini)         autopilot/scriptwriter.py
      ─▶ beats  ─▶ _beats_to_scenes     autopilot/produce.py
                    └─ TEMPLATES         scripts/generate_stories.py  (t_solo, t_two, …)
                    └─ _colorize         autopilot/produce.py
      ─▶ story JSON {style, voice, scenes:[{actors, props, …}]}
      ─▶ faceless.render.build()         faceless/render.py
            ├─ build_audio()  (TTS per scene → durations, word_timings)
            ├─ for each frame:
            │     render_frame()
            │        ├─ _background()           flat colour + vignette
            │        ├─ scenery.draw_backdrop() sky / sun / hills / bokeh
            │        ├─ _draw_prop()  (back)    labels, icons, shapes
            │        ├─ _draw_actor() ───────▶  figures.draw_figure()  ← THE CHARACTER
            │        ├─ _draw_prop()  (front)
            │        ├─ motion.camera()         Ken Burns
            │        ├─ captions.draw_kinetic_caption()
            │        ├─ _draw_watermark()
            │        └─ _draw_hook()
            └─ pipe RGB frames ─▶ ffmpeg ─▶ mp4 (+ audio, +music)
```

A "scene" is data, not code: `actors` (figures with keyframes), `props`, and a
`narration`/`caption`. Templates in `scripts/generate_stories.py` turn a script
beat into that actor/prop data.

---

### 1. How stick figures are currently rendered

`faceless/render.py::_draw_actor()` is the entry point per actor per frame:

1. Samples keyframes (`anim.sample_keys`) for `pos`, `scale`, `alpha`.
2. Resolves the **pose** by blending two named poses (`_sample_pose` →
   `anim.blend_pose`) and the **face** (`_face_at`).
3. Computes pixel anchor `(px, py)` = hip position, and `unit` = `scale * mindim`
   (the figure's size in pixels).
4. Optionally draws a contact **shadow** ellipse.
5. Builds a `Sketcher` (the pen) with the figure colour + an auto-contrast
   **halo** (added in the last pass) and calls `figures.draw_figure()`.
6. Composites the figure layer onto the frame with `alpha`.

`figures.draw_figure()` draws the body as **open polylines** (limbs) + one
**circle** (head) + a few strokes/dots (face). That's the whole character.

### 2. Which drawing library is being used

**Pillow (PIL)** — `PIL.ImageDraw` only. No SVG, no vector engine, no skia/cairo.
- `faceless/draw.py::Sketcher` wraps `ImageDraw.Draw` and adds the hand-drawn
  wobble: every polyline is subdivided and its interior points are nudged
  perpendicular to the line (`_wobbly`), re-seeded every `boil_every` frames to
  get the "boiling line" doodle shimmer.
- Primitives available: `stroke` (polyline), `line`, `circle`, `arc`, `dot`,
  plus the new `halo` underlay. Compositing is `Image.alpha_composite`.
- `numpy` is used only for backgrounds/grain, not the character.

So the character is literally **lines drawn with a slightly shaky pen**. There is
no notion of a filled body, a silhouette, or outlined shapes.

### 3. How body parts are created

In `faceless/figures.py`, the body is a **2-segment-limb stick skeleton** anchored
at the hip. Segment lengths are fractions of the figure unit `U`:

```
HEAD_R 0.130   TORSO 0.340   UPPER_ARM 0.190   FOREARM 0.170
THIGH 0.210    SHIN 0.210     HEAD_GAP 0.030
```

`draw_figure()`:
- `hip` is the anchor. `shoulder = hip + TORSO` along the (tilted) torso angle.
- `head_c = shoulder + (HEAD_R+HEAD_GAP)`; head = one `circle`.
- Each **leg**: `hip → knee → foot` (a 3-point polyline).
- **Torso**: `hip → shoulder` (one line).
- Each **arm**: `shoulder → elbow → hand` (a 3-point polyline).
- **Face**: dots/lines/arcs inside the head.

That is the *entire* part list: **head circle, torso line, 2 arm polylines, 2 leg
polylines, face marks.** There are **no separate** eyes-as-objects, eyebrows,
hands, feet, hat, shirt, or shorts. Limbs are infinitely thin lines with rounded
caps — there is no body mass, no clothing layer, no hands or shoes.

### 4. How poses are generated

`figures.POSES` is a dict of ~15 named poses. Each pose is **joint angles in
degrees** measured from straight-down:

```python
"stand": {"lean":0, "head":0, "la":[18,16], "ra":[-18,-16], "ll":[10,8], "rl":[-10,-8]}
#         torso tilt  head tilt  [upperarm,forearm] L/R     [thigh,shin] L/R
```

Poses: `stand, idle, think, look_up, arms_up, celebrate, point_up, point_r,
point_l, reach, wave, shrug, sit, walk_a, walk_b`.

- A scene actor carries keyframes referencing pose **names**; `_sample_pose`
  blends the bracketing poses with `anim.blend_pose` (shortest-path angle lerp).
- `walk` is faked by alternating `walk_a`/`walk_b` keyframes (see `t_walk`).
- Limbs are strictly **2 segments** — no wrist, no ankle, no finger, no spine
  curve, so poses can't express weight, reach, or follow-through well.

### 5. How expressions are generated

Expressions = the `face` string, drawn by `figures._draw_face()`:
- Eyes: two `dot`s, or short lines when blinking/`shut`.
- Mouth: an `arc` (happy/sad), a small `circle` (surprised), or a flat `line`
  (neutral/dots).
- Faces available: `happy, sad, surprised, neutral, dots, shut`.

There are **no eyebrows**, no eye *shape* variation, no pupils, no brow angle, and
expression does **not** affect the body. `angry, excited, confused, thinking,
scared, determined, celebrating` do **not exist** as faces — they map to nothing.
Emotion and posture are decoupled: a "happy" face can sit on a slumped body.

### 6. How animation is generated

Three independent layers:

1. **Keyframes** (`anim.sample_keys`): per-actor `pos/scale/alpha` and pose
   transitions over scene-normalized time `t∈[0,1]`, with easings
   (`linear, ease_in_out, ease_out, ease_in, pop`).
2. **Procedural "life"** (`faceless/motion.py`): per-frame breathing bob, sway,
   and deterministic blinks added inside `draw_figure` so a held pose never fully
   freezes. Stable per-figure phase via `phase_for`.
3. **Draw-on reveal**: `Sketcher` truncates strokes by arc length
   (`draw.truncate`) so a figure "sketches itself in" over `draw_in_dur`.
4. **Camera**: `motion.camera` applies a slow Ken Burns zoom/drift to the world.

Timing is synced to narration: `build_audio` measures real TTS duration and
`captions.build_word_timings` aligns words to audio energy. Props can `sync_word`
to pop on a spoken word.

This animation core is **solid and reusable** — the problem is *what* it animates,
not *how* it interpolates.

### 7. Why characters look like basic stick figures (root causes)

| # | Root cause | Consequence |
|---|-----------|-------------|
| 1 | Body = **thin polylines**, no filled silhouette | Reads as wireframe, not a "person"/mascot |
| 2 | **No clothing layer** (hat/shirt/shorts) | No identity, no colour blocking, no "character" |
| 3 | **No hands/feet** — limbs end in round caps | No gesture, no grounding, looks unfinished |
| 4 | Limbs are **2 rigid segments** | Stiff; can't show weight, reach, follow-through |
| 5 | **Expression = face only**, 6 presets, **no eyebrows** | Flat affect; can't read emotion at a glance |
| 6 | **Emotion ⊥ posture** (decoupled) | Body language never matches the line being said |
| 7 | **No scene→emotion/pose inference** | Templates pick generic poses unrelated to meaning |
| 8 | Head is a **plain circle**, eyes are dots | Generic; lacks the rounded doodle-mascot charm |

The reference images (red-beanie mascot; rounded-head expressive stickmen) all
have: **filled outlined bodies, clothing, mitten hands, shoes, eyebrows, big
expressive eyes/mouths, motion lines, ground shadows, and posture that matches
emotion.** Our system has essentially none of those.

---

# PART 2 — Target style (from the reference images)

Common DNA across the 5 references we should reproduce procedurally:

- **Rounded-head doodle** with a clear, slightly thick **black outline**.
- **Clothing as filled colour blocks**: beanie/hat, short-sleeve shirt, shorts.
- **Mitten/glove hands** and **shoes** (small filled shapes at limb ends).
- **Eyebrows** + **big eyes** + **expressive mouth** — emotion legible instantly.
- **Tapered, slightly curved limbs** (not hairlines) — limbs have *width*.
- **Motion/action lines** (speed whooshes, impact ticks) and a **ground shadow**.
- **Posture sells emotion**: celebrate = open & airborne; push = low & leaning;
  angry = arms crossed, brow down; think = hand to chin, head tilt.
- **Consistent identity** across scenes (same proportions, colours, accessories).

Two flavours appear: a **coloured mascot** (img 1: beanie + yellow shirt) and a
**clean B/W expressive stickman** (imgs 3–5). The architecture below produces both
from one model by swapping the palette/clothing config.

---

# PART 3 — Proposed Architecture

Five cooperating systems, layered so the existing animation core (keyframes,
"life", camera, captions, ffmpeg) is **reused unchanged**. Only the *figure
drawing* and *scene authoring* are replaced.

```
SceneInterpreter ─(emotion,pose,action)──▶ AnimationEngine ──▶ CharacterModel ──▶ renderer (Pillow)
        ▲                                        ▲  uses              ▲ uses
        │ narration text                 PoseEngine  ExpressionEngine │
        │                              (skeleton angles) (face+body)  │
   script beats                                                 part geometry + style
```

### 3.1 `CharacterModel` — identity & proportions (the "rig")

A dataclass capturing everything that stays **constant across scenes** so the
character is consistent, plus the part list for independent control.

```python
@dataclass
class CharacterModel:
    # identity / proportions (fractions of figure unit U)
    head_r: float = 0.16
    torso_len: float = 0.34
    limb_width: float = 0.055      # limbs have MASS now (tapered capsules)
    proportions: dict = ...        # upper_arm, forearm, thigh, shin, neck, hand_r, foot_len

    # palette
    outline: str = "#1a1a1a"
    skin: str = "#ffffff"          # head/face fill
    line_width: float = 0.011

    # clothing / accessories (each independently toggdleable + recolourable)
    hat:   Part | None = Beanie(color="#e23b3b", pom=True)
    shirt: Part         = Shirt(color="#f2c014", sleeves="short")
    shorts:Part         = Shorts(color="#222222")
    hands: Part         = Mittens(color="#ffffff")
    feet:  Part         = Shoes(color="#444444")

    seed: int = 0                  # stable wobble identity
```

Key ideas:
- **Parts are objects** (`Part` protocol with `.draw(skldraw, joints, style)`),
  so head/eyes/eyebrows/mouth/torso/arms/hands/legs/feet/hat/shirt/shorts are all
  **independently controllable** and individually styleable, as required.
- **Proportions live here once** → consistency across all scenes for free.
- A channel gets **one** `CharacterModel` (e.g. Inklings = the beanie mascot);
  per-scene we only vary pose/expression, never identity.

### 3.2 Rendering approach — from "lines" to "doodle body"

This is the crucial change. Instead of stroking thin lines we draw **filled,
outlined shapes** (capsules + polygons) so the body has mass and a clean black
outline — the doodle look.

Add to `Sketcher` (Pillow-only, no new deps):
- `capsule(p0, p1, width, fill, outline)` — a rounded-rect limb between two
  joints (the body "tube"); drawn as a filled wobbly polygon + outline pass.
- `blob(points, fill, outline)` — closed wobbly filled polygon (torso, mittens,
  shoes, hat, shirt).
- Reuse existing wobble so it still looks hand-drawn; reuse `draw`-truncation for
  the sketch-on reveal (truncate the outline path).

Draw order per figure (back→front): far leg → far arm → torso/shirt → shorts →
near leg → head+face → near arm → hands → hat → motion lines.

Two-pass outline: fill all parts, then stroke a single **black outline** so
overlaps merge into one clean silhouette (matches the references).

### 3.3 `PoseEngine` — skeleton angles (extends current poses)

Keep the angle-based pose idea but **richer joints** and an explicit schema, as
the user specified (per-pose: L/R arm rot, L/R leg rot, body tilt, head angle —
plus we add elbow/knee/wrist/ankle for expressiveness).

```python
@dataclass
class Pose:
    body_tilt: float           # torso lean
    head_angle: float
    l_arm: tuple[float,float,float]   # shoulder, elbow, wrist
    r_arm: tuple[float,float,float]
    l_leg: tuple[float,float,float]   # hip, knee, ankle
    r_leg: tuple[float,float,float]
    weight: float = 0.0        # hip drop / crouch amount (sells push/sit/jump)
    hand_l: str = "open"       # open|fist|point|grab  (drives hand shape)
    hand_r: str = "open"

POSES = { "idle", "walk", "run", "jump", "point", "push", "pull",
          "kick", "carry", "wave", "celebrate", "sit", "think", "work" }
```

- `PoseEngine.get(name) -> Pose`; `PoseEngine.blend(a, b, t)` (shortest-path
  angle lerp, reuses `anim.blend_pose` logic).
- "run"/"walk" can ship as cyclic generators (phase → Pose) so locomotion is one
  call instead of hand-placed `walk_a/walk_b` keys.

### 3.4 `ExpressionEngine` — face **and** body coupling

An expression preset modifies **eye shape, eyebrow angle, mouth shape, head tilt,
and body posture bias** — fixing the current emotion⊥posture decoupling.

```python
@dataclass
class Expression:
    eyes: str       # round|wide|squint|happy_arc|closed|spiral
    brow: float     # angle: + = raised(surprise), - = furrowed(anger)
    brow_height: float
    mouth: str      # smile|frown|open_smile|grimace|small_o|flat|gasp
    head_tilt: float
    posture_bias: float   # blended into body_tilt/weight (e.g. sad = slump)

EXPRESSIONS = { happy, sad, angry, excited, surprised,
                confused, thinking, scared, determined, celebrating }
```

- `ExpressionEngine.get(name) -> Expression`, and a `mix()` for transitions.
- The face parts (eyes/eyebrows/mouth) read this; `posture_bias`/`head_tilt`
  are merged into the Pose before drawing, so **a sad character also slumps**.

### 3.5 `AnimationEngine` — keyframed poses + expressions + life

Thin layer over the **existing** `anim.py`. New concept: a clip is a list of
`(t, pose, expression, pos, scale)` keyframes; it interpolates both skeleton and
face, then adds the existing breathing/sway/blink "life" so nothing is static.

```python
@dataclass
class CharacterKeyframe:
    t: float; pose: str; expression: str
    pos: tuple[float,float]; scale: float; alpha: float = 1.0; ease: str = "ease_in_out"

class AnimationEngine:
    def sample(self, keys, t) -> CharacterState   # blends Pose+Expression+transform
```

- Reuses `anim.sample_keys` for pos/scale/alpha and `PoseEngine.blend` /
  `ExpressionEngine.mix` for the rig/face.
- Honors `startPose / midPose / endPose` (the requested 3-key shorthand expands
  to `t=0 / 0.5 / 1`).
- "Always subtle motion" = existing `motion.breath/sway/is_blink` stays on.

### 3.6 `SceneInterpreter` — narration → (emotion, pose, action)

Turns a beat's text into body language automatically (the user's examples).

```python
class SceneInterpreter:
    def infer(self, narration: str, hint: dict | None) -> BeatDirection
    # BeatDirection = {emotion, pose, action, props[], camera}
```

Two-tier, deterministic-first:
1. **Keyword/intent rules** (fast, free, offline): a lexicon maps verbs/affect to
   (emotion, pose). e.g. `treasure|won|finally|amazing → (excited, celebrate)`;
   `struggle|heavy|push|barely → (determined, push)`; `lost|alone|miss →
   (sad, idle+slump)`; `idea|realize → (excited, think→point)`.
2. **LLM enrichment (optional)**: the existing Gemini scriptwriter is extended to
   emit per-beat `{emotion, pose, action}` directly in its JSON, so we usually
   skip inference. Rules are the **fallback** when Gemini is down (consistent with
   the project's offline-first philosophy).

Output feeds the templates: instead of `t_solo` choosing a generic pose, the beat
already carries `emotion`+`pose`+`action`, which become CharacterKeyframes.

---

# PART 4 — Integration & migration plan (when we implement)

**New files (proposed):**
```
faceless/character/__init__.py
faceless/character/model.py          # CharacterModel, Part protocol + parts (Beanie, Shirt, Shoes, Mittens…)
faceless/character/pose.py           # Pose, PoseEngine, POSES
faceless/character/expression.py     # Expression, ExpressionEngine, EXPRESSIONS
faceless/character/animation.py      # CharacterKeyframe, AnimationEngine, CharacterState
faceless/character/skeleton.py       # joint solver: Pose → world joint coords (FK)
faceless/character/render.py         # draw_character(sketcher, state, model, style)
autopilot/scene_interpreter.py       # SceneInterpreter (rules + LLM glue)
```

**Touch points (minimal):**
- `faceless/draw.py` — add `capsule()` / `blob()` filled-shape primitives.
- `faceless/render.py::_draw_actor` — branch: if `style.character` present, call
  `character.render.draw_character(...)`; else fall back to legacy
  `figures.draw_figure` (keeps old stories renderable).
- `autopilot/produce.py` / `scripts/generate_stories.py` — templates emit the new
  `emotion/pose/action` beat fields; `CharacterModel` comes from the channel
  config (so identity is per-channel & consistent).
- `autopilot/channels.json` — add a `character` block (palette, clothing) per
  channel.

**Backward compatibility:** keep `figures.py` and the legacy path. Gate the new
renderer behind a `style.character` / channel flag so existing `stories/*.json`
still render. The animation core (`anim`, `motion`, `captions`, ffmpeg) is
untouched.

**Suggested phasing:**
1. `CharacterModel` + filled-shape primitives + static **idle** render that
   already looks like the mascot (biggest visual win, lowest risk).
2. `PoseEngine` + `ExpressionEngine` (the 14 poses / 10 expressions) with
   emotion↔posture coupling.
3. `AnimationEngine` keyframe clips (start/mid/end) + locomotion cycles.
4. `SceneInterpreter` (rules) + extend Gemini JSON to emit emotion/pose/action.
5. Hands/feet detailing, motion lines, prop interactions (carry box, push rock).

**Risks / watch-items:**
- **Per-frame cost**: filled polygons + outline pass are heavier than thin lines.
  Mitigate by caching static sub-parts and keeping shapes low-vertex.
- **Wobble on fills**: too much boil on filled outlines looks noisy — tune amp
  down for closed shapes vs. open strokes.
- **Self-overlap z-order**: need correct near/far limb ordering per pose (handled
  in `skeleton.py` by tagging limbs front/back from `body_tilt`/facing).
- **Consistency**: all identity lives in `CharacterModel`; scenes may only set
  pose/expression/transform — enforce this in the template layer.

---

## Appendix — current vs. target (capability matrix)

| Capability | Current | Target |
|---|---|---|
| Body | thin polylines | filled, outlined doodle silhouette |
| Clothing | none | hat, shirt, shorts (configurable) |
| Hands / feet | round caps | mittens + shoes (shape per gesture) |
| Limbs | 2 rigid segments | 3-joint, tapered, weighted |
| Eyes | 2 dots | shaped (round/wide/squint/arc/spiral) |
| Eyebrows | none | angled, emotion-driven |
| Mouth | arc/line/circle | smile/frown/open/grimace/o/gasp |
| Emotions | 6 faces | 10 presets, face **+** posture |
| Poses | ~15 angle sets | 14 named, richer joints + cycles |
| Body language from script | none | `SceneInterpreter` (rules + LLM) |
| Identity consistency | implicit | `CharacterModel` (explicit, locked) |
| Animation | keyframes + life ✅ | reused, extended to pose+expression clips |
