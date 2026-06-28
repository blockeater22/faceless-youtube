# Stickforge — Architecture & Module Map

This document maps the **20 requested platform modules** to the current engine,
honestly: what is **implemented** and tested now, what is **partial**, and where
the **extension point** lives for the rest. The goal of this first build is the
*keystone* — a data-driven asset/character/animation core with clean,
registry-based seams — so every remaining module plugs in without a rewrite.

## Design principles (enforced in code)

1. **Nothing hardcoded.** Characters, poses, expressions, clips, palettes,
   attachments, and camera moves are all *data* that can live in JSON packs.
2. **Registries everywhere.** Asset types, renderers, exporters, easings,
   skeletons, poses, expressions, and attachments are each a `Registry`, so
   plugins extend the platform without editing core code.
3. **Zero-dependency core.** Pure-Python logic; rasterization/video are optional
   backends that degrade gracefully (HTML player always works).
4. **Pure & testable.** Geometry, easing, keyframes, FK, and blending are pure
   functions with a unit-test suite (`tests/`, 36 tests).

## Layer stack

| Layer | Package | Responsibility |
|---|---|---|
| Core | `stickforge/core` | geometry, easing, keyframes, registry |
| Assets | `stickforge/assets` | Asset, Library (search/tags), Packs |
| **Parts** | `stickforge/parts` | **Character Design System** — per-category style registries (art providers) |
| Rig + Character | `stickforge/character` | cartoon/line skeletons (FK), `ActorDesign` assembly |
| Pose | `stickforge/pose` | named, blendable joint poses |
| Expression | `stickforge/expression` | facial-parameter emotions + blending |
| Animation | `stickforge/animation` | keyframed clips + procedural life |
| **Acting** | `stickforge/acting` | **emotional state machine + beat-based performance** (think→react→act, anticipation, eye acting, emotion-driven idle) |
| **Story** | `stickforge/story` | **script → beats → performed, subtitled scene**; multi-character dialogue staging + eye contact |
| **Voice** | `stickforge/voice` | **procedural lip-sync (visemes)** + a pluggable TTS interface (timing model) |
| Scene | `stickforge/scene` | scene graph, camera, timeline |
| Render | `stickforge/render` | `illustrated` (house style) + `svg` (legacy) backends, motion FX |
| Export | `stickforge/export` | frames → HTML player / MP4 |

**Visual identity:** the default `illustrated` renderer produces clean flat
cartoon actors per [`STYLE_GUIDE.md`](STYLE_GUIDE.md) — assembled from `parts`,
never hardcoded. The procedural `svg` line-stickman is retained only as a legacy
backend and is not the product look.

## The 20 modules

| # | Requested module | Status | Where / how to extend |
|---|---|---|---|
| 1 | Asset Management System | **Built** | `assets/` — typed, taggable, searchable, JSON packs, versioning |
| 2 | Character Assembly Engine | **Built (personality-first)** | `character/archetype.py` (shape language + parametric proportions + signature stance) + `parts/` + `ActorDesign`; distinct, non-interchangeable silhouettes (silhouette test included) |
| 3 | Rigging Engine | **Built** | `character/skeleton.py` — hierarchical FK; `SKELETONS` registry |
| 4 | Pose Engine | **Built (generative)** | `pose/builder.py` constructs poses movement-first (line-of-action → weight/contrapposto → spine → legs → arms); `pose/score.py` silhouette/appeal scorer; `pose/lab.py` generate-score-reject loop |
| 5 | Expression Engine | **Built** | `expression/` — continuous params, `EXPRESSIONS` registry |
| 6 | Gesture Engine | **Built (basic)** | hand-gesture styles (point/thumbs-up/peace/fist/open/wave) + per-moment `hands` track on clips |
| 7 | Motion Engine | **Built** | `animation/clip.py` keyframes + `procedural.py` life; walk cycle; **`acting/` performance compiler** (emotion→body/eyes/timing, think-before-act, anticipation) |
| 8 | Physics Engine | **Built (basic)** | easings (anticipation/overshoot/bounce) + secondary-motion lag (hair bounce / hand follow-through) in the illustrated renderer |
| 9 | Camera Engine | **Built** | `scene/camera.py` — keyframable zoom/pan + shake; add orbit/parallax |
| 10 | Scene Builder | **Built** | `scene/scene.py` — actors/props/background/camera from spec |
| 11 | Timeline Editor | **Partial (data)** | `scene/scene.py:Timeline` sequences scenes; GUI editor is future |
| 12 | Story Engine | **Built (basic)** | `story/` — script → acting beats (auto "think before react") → subtitled `Scene`; `story/dialogue.py` multi-character staging, turn-taking, eye contact |
| 13 | Voice Sync Engine | **Built (basic)** | `voice/engine.py` — pluggable TTS registry + timing model (silent backend); beat/subtitle timing derives from it (real audio backends plug in) |
| 14 | Lip Sync Engine | **Built (basic)** | `voice/lipsync.py` — syllable→viseme stream drives `mouth_open`/`mouth_curve`, synced to each spoken beat (no audio needed) |
| 15 | Background Generator | **Partial** | `render/svg.py:_scenery` (night/ground); register more scenery kinds |
| 16 | Props Engine | **Built (basic)** | `scene` props + `render/svg.py:_prop` (label/circle/rect/line) |
| 17 | Particle & FX Engine | **Built (basic)** | `render/fx.py` — speed lines, impact, sweat, stars, lightbulb, hearts, anger via `FX` registry |
| 18 | Transition Engine | **Partial** | per-clip easing + camera; add cross-scene transitions in `Timeline` |
| 19 | Subtitle Engine | **Built** | timed subtitle cues (`Scene.subtitles` / `subtitle_at`), auto-synced by the Story Engine |
| 20 | Export Pipeline | **Built** | `export/` — HTML player (always), MP4 (ffmpeg+rasterizer) |

### Marketplace / packs
Asset **packs** (`assets/pack.py`) are versioned JSON bundles — the unit of
distribution. `AssetLibrary.load_dir()` installs every pack in a folder. This is
the foundation the marketplace (character/expression/pose/background/… packs)
builds on.

### Extensibility (plugin surfaces)
`ASSET_TYPES`, `RENDERERS`, `EASINGS`, `SKELETONS`, `POSES`, `EXPRESSIONS`,
`ATTACHMENTS` are all registries. A plugin imports the registry and registers —
no core change, no fork.

## Recommended next increments

1. **Physics/secondary motion** — a spring solver layered after FK (jiggle on
   hands/hair, weight-driven overshoot) — biggest perceived-quality jump.
2. **Story Engine** — script → beat parser → scene-spec generator (LLM-assisted),
   emitting the same JSON the renderer already consumes.
3. **Audio + lip-sync** — narration timing drives clip durations and
   `mouth_open`/`mouth_curve` per frame.
4. **Raster renderer backend** — register a Pillow/Skia `RENDERERS` entry for
   faster MP4 without an external rasterizer.
5. **Web editor** — timeline/inspector over the existing scene-spec data model.
