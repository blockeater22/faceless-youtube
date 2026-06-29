# stickforge

A **modular, data-driven engine for illustrated cartoon actors**. Characters are
not drawn by hand and not hardcoded — they are **assembled from a component
library** (head, hair, eyes, brows, mouth, hands, feet, body build, clothing,
accessories), posed on a rig, and rendered in a clean flat **house style**. The
core has **zero third-party dependencies**.

> The look is an *illustrated cartoon actor*, not a mathematical stickman:
> big white head + bold outline, expressive face, hair, yellow tee with rounded
> shoulders, black shorts, thick limbs, simple hands, shoes, ground shadow.
> See [`STYLE_GUIDE.md`](../STYLE_GUIDE.md).

---

## Quickstart

```bash
python -m stickforge demo       # showcase: actors acting  -> output/.../demo.html
python -m stickforge cast       # the personality-first archetype cast
python -m stickforge silhouettes# silhouette readability test (no detail)
python -m stickforge lab        # the character lab: recombination lineup
python -m stickforge acting     # an actor performing a beat sequence
python -m stickforge story      # a wordless silent story (read it muted)
python -m stickforge emotions   # emotion board (body acting reads w/o face)
python -m stickforge storyboard stickforge/examples/story.txt  # script -> film
python -m stickforge showcase   # expression contact sheet
python -m stickforge assets --search actor
python -m stickforge build stickforge/examples/hello.json

# global options go BEFORE the subcommand:
python -m stickforge --format 16:9 --fps 30 demo
python -m stickforge --backend svg demo     # legacy line-stickman renderer
```

Every command writes a **self-contained `.html` player** (any browser, no
server, no codecs). With `cairosvg` + `ffmpeg` installed it also writes `.mp4`.

---

## The Character Design System

A character is a *selection*, not a drawing. Each part category is a registry of
styles; a design picks one per category plus a palette and body build:

```python
from stickforge.character.design import ActorDesign
from stickforge.parts import catalog, combination_count

d = ActorDesign.from_dict({
    "palette": "blue",
    "parts": {"hair": "ponytail", "eyes": "cartoon", "body": "round",
              "accessory": "glasses", "feet": "boot"},
})
print(combination_count())   # distinct characters the current library can make
print(catalog())             # styles available per category
```

Because the choices multiply, a modest seed library already yields **~10^6**
characters — and it grows toward the 50-heads / 120-eyes targets simply by
registering more styles. No engine change.

```
ActorDesign (part-style selection + palette + build)
     │
Character (design + cartoon Rig)
     │
AnimationClip (keyframed poses + expressions) ─sample─> Posing + procedural life
     │
Scene (actors + camera + background + props/FX) ─> Timeline
     │
IllustratedRenderer ─> clean SVG frames ─> HTML player / MP4
```

---

## Procedural World Simulation Engine (story → living world)

Turns a Scene Graph into a fully-instantiated, validated World Graph — rooms,
constraint-placed props (resolved from the registry), interaction zones,
navigation, lighting, weather, and environmental storytelling. No image
generation, no coordinate templates.

```python
from stickforge.narrative import understand_story, plan
from stickforge.world import build_world
spec = plan(understand_story("John entered his interview on a rainy morning."))[0]
world = build_world(spec, seed=3)     # placed props, zones, nav, lights, valid
world.nav.path("nav.zone.entrance", "nav.zone.working")   # characters navigate
```

```bash
python -m stickforge world "A cozy family dinner in the kitchen on a snowy evening."
```

## Cognitive layer (understand a story, then plan it)

The story brain turns prose into a validated, structured Scene Graph — nothing
downstream parses English:

```python
from stickforge.narrative import understand_story, plan, summarize_story
u = understand_story("John nervously entered his first interview on a rainy morning.")
summarize_story(u)   # {genre: business, setting: corporate office, time: morning,
                     #  weather: rain, mood: nervous, emotion_curve: [...]}
plan(u)              # -> [SceneSpec] (environment, cameras, semantic props, validated)
```

```bash
python -m stickforge understand "On the spaceship, Nova saw an alien signal. Suddenly the lights went dark."
```

Understanding (analysis + persistent character models + Scene→Beat→Action
segmentation) → typed **Intent Graph** → **Scene Planner** → validated Scene
Graph. The inference provider is pluggable (heuristic today, LLM tomorrow) and
every value carries a confidence score.

## Asset Intelligence Engine (semantic asset registry)

The single source of truth for assets — engines query by meaning, never by path:

```python
from stickforge.registry import default_registry
reg = default_registry()
reg.find_assets("a rainy office window")     # -> ranked AssetMeta
reg.choose_variant("chair.office", "modern") # -> best variant for the intent
reg.supports("world:furniture.office_desk")  # -> {laptop, coffee_mug, ...}
```

```bash
python -m stickforge registry "cozy sofa for a living room"
python -m stickforge registry --stats
python -m stickforge registry --bench 50000   # scale test (~1s index)
```

Rich validated metadata (anchors, placement surfaces, interactions, variants,
relationships, styles, performance), inverted-index queries that scale to
100k+ assets, and a constraint system that rejects impossible scenes. Versioned
JSON packs let core + marketplace content plug in without engine changes.

## Generative posing (line-of-action first)

Poses are constructed from movement, not authored arms-first — line of action →
weight/contrapposto → spine → legs → arms. They're scored on the silhouette test
(line of action, balance, negative space, asymmetry, extension):

```python
from stickforge.pose import build_pose, score_pose, lab
p = build_pose(loa=14, weight=0.7, head=4, arm_l="reach", arm_r="hip")
print(score_pose(p))          # (8.x, {line_of_action, balance, silhouette, ...})
lab.evaluate(100)             # the generate→score→reject test loop
```

```bash
python -m stickforge posetest --n 100      # the test loop, scored
python -m stickforge posegallery           # top generated poses (try --? + silhouette)
```

## The Acting Engine (performance, not playback)

Don't keyframe motion — describe *intention* as beats; the engine compiles
acting (anticipation, think-before-act pauses, emotion-driven body/eyes/timing):

```python
from stickforge.acting import perform, Beat

clip = perform([
    Beat("curious", 1.4, "act"),                       # notices something
    Beat("confused", 1.6, "think", look=(0.4, -0.4)),  # pauses, eyes drift up
    Beat("shocked", 1.0, "react"),                      # recoils (anticipation)
    Beat("excited", 1.8, "act"),                        # delight
])
```

Each emotion (`stickforge/acting/emotion.py`) maps to a silhouette-readable body
pose, head/spine attitude, hand state, gaze bias, blink rate, and tempo — so
`python -m stickforge emotions` reads even with faces removed.

## The Story Engine (script → performed film)

Write a script; the director infers emotion per line, inserts "think before you
react" beats, performs it, and syncs subtitles:

```text
(a quiet night under the stars)
happy: What a beautiful evening.
curious: Wait... what is that up there?
No way!                     # inferred: shocked (gets a think-pause first)
excited: It's a shooting star!
```

```python
from stickforge.story import storyboard
scene = storyboard(open("story.txt").read())   # -> a performed, subtitled Scene
```

**Multi-character dialogue** stages the cast facing each other, with turn-taking,
eye contact, and lip-sync (the speaker's mouth flaps to the words):

```text
ALEX: Hey! Did you see that?
SAM: See what?
ALEX: That shooting star!
```

```python
from stickforge.story import stage_dialogue
scene = stage_dialogue(text, {"ALEX": "actor.nova", "SAM": "actor.rex"})
```

```bash
python -m stickforge dialogue     # the staged two-hander above
```

Lip-sync (`stickforge/voice/`) turns text into timed mouth visemes with no audio;
a pluggable TTS registry lets real voices (espeak/piper/…) plug in later.

## Extending (no core edits)

Every catalogue is a `Registry` — add a style/effect by registering it:

```python
from stickforge.parts import HAIRS, EYES, ACCESSORIES
from stickforge.render.fx import FX

@HAIRS.register("mohawk")
def mohawk(cv, f):
    ...                      # draw using f.at(lx, ly), f.color(...), f.outline_w

@FX.register("zzz")
def zzz(cv, center, size, color):
    cv.text(center.x, center.y, "Z", size, color)
```

Asset **packs** (JSON) distribute characters/clips/parts — drop a `*.json` in a
pack directory and `AssetLibrary.load_dir()` installs it (the marketplace
foundation). See `data/packs/actors.json`.

---

## Renderers

- **`illustrated`** (default) — the house style: flat colors, bold clean lines
  (no sketch/boil), rounded shoulders, thick limbs, hands, shoes, shadow.
- **`svg`** (legacy) — the original thin-line stickman, kept for comparison.

Select with `--backend` or `render_frames(..., backend=...)`.

---

## Tests

```bash
python -m unittest discover -s tests     # 47 tests, zero deps
```
