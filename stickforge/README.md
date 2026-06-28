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
