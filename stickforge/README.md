# stickforge

A **modular, data-driven stickman animation engine**. Characters, poses,
expressions, and animations are *data* (loadable from JSON asset packs), never
hardcoded into the renderer. The core has **zero third-party dependencies**;
rasterization/video are optional backends that degrade gracefully.

This is the fresh engine core for the platform — built bottom-up as independent,
registry-extensible layers so the larger feature set (physics, lip-sync,
marketplace, editor, AI) can be layered on without rewrites. See
[`ARCHITECTURE.md`](../ARCHITECTURE.md) for the full module map and roadmap.

---

## Quickstart

```bash
# zero dependencies needed for these:
python -m stickforge demo                  # -> output/stickforge/demo.html
python -m stickforge showcase              # expression contact sheet
python -m stickforge assets --search wave  # browse the asset library
python -m stickforge poses                 # list poses
python -m stickforge build stickforge/examples/hello.json

# global options go BEFORE the subcommand:
python -m stickforge --format 16:9 --fps 30 demo
```

Every command writes a **self-contained `.html` player** (opens in any browser,
no server, no codecs). If `cairosvg` **and** `ffmpeg` are installed, an `.mp4`
is written too:

```bash
pip install cairosvg          # SVG rasterizer
apt-get install -y ffmpeg     # video muxer
```

---

## Concepts

```
AssetLibrary ── packs (JSON) ──> characters / clips / poses / expressions
     │
Character (spec + Skeleton)      Skeleton = bones solved by forward kinematics
     │
AnimationClip (keyframed poses + expressions)  ──sample(t)──>  Posing
     │                                           + procedural life (breath/blink)
Scene (actors + camera + background + props)
     │
Timeline (scenes back-to-back)
     │
SvgRenderer ──> SVG frames ──> HTML player / MP4
```

- **Angle convention:** degrees, clockwise from straight up (`0`=up, `90`=right).
- **Rig:** hierarchical — leaning the spine carries the arms and head (real
  forward kinematics, not independent absolute angles).
- **Expressions:** a single continuous parameter space (brows, eyes, gaze,
  mouth). "happy"/"angry"/… are just named presets; anything between is a blend.

---

## Authoring a project

A project is JSON: a `timeline` of scenes, each placing `actors` (a character +
an animation clip) under a `camera`. Characters and clips are referenced by
library id, or inlined. See [`examples/hello.json`](examples/hello.json).

```jsonc
{
  "format": "9:16", "fps": 24,
  "timeline": [{
    "id": "intro", "duration": 2.6,
    "background": {"type": "night"},
    "caption": "Built from a JSON spec.",
    "actors": [{ "character": "char.classic", "clip_id": "clip.wave_hello",
                 "pos": [0.5, 0.66], "unit_scale": 0.36 }]
  }]
}
```

---

## Extending (no core edits)

Everything pluggable is a `Registry`:

```python
from stickforge.pose import register_pose
from stickforge.expression import register_expression
from stickforge.render.svg import ATTACHMENTS         # hair/hats/accessories
from stickforge.core.easing import EASINGS
from stickforge.character.character import SKELETONS

register_pose("tpose", {"upper_arm_l": 270, "upper_arm_r": 90})
register_expression("zen", {"eye_open": 0.2, "mouth_curve": 0.3})

@ATTACHMENTS.register("halo")
def halo(cv, center, head_r, angle, color, spec):
    cv.circle(center + (0, -head_r*1.6), head_r*0.8, color, 4)
```

Asset packs distribute these as data — drop a `*.json` pack in a directory and
`AssetLibrary.load_dir()` picks it up.

---

## Tests

```bash
python -m unittest discover -s tests     # 36 tests, zero deps
```
