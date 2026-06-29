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
| **Stage (spatial)** | `stickforge/stage` | **world space, scene graph, affine transforms, anchors, depth layers + parallax, `Camera2D` (the only world→screen projection)** — the substrate every renderer/engine builds on |
| Assets | `stickforge/assets` | runtime content library (characters/clips), packs |
| **Asset Intelligence** | `stickforge/registry` | **the semantic asset knowledge base** — canonical metadata schema, taxonomy, inverted-index semantic query, relationships, anchors, variants, constraints; the single source of truth every future engine queries (no file paths) |
| **Cognitive (narrative)** | `stickforge/narrative` | **the story brain** — understanding (analysis + characters + segmentation) → Intent Graph → Scene Planner → validated Scene Graph; pluggable inference provider (heuristic now, LLM later). Downstream engines consume the Scene Graph, never English |
| **World** | `stickforge/world` | **Procedural World Simulation Engine** — Scene Graph → instantiated **World Graph**: constraint-placed props (registry-resolved), interaction zones, navigation graph, lighting, weather, environmental storytelling. Built on `stage` + `registry`; no image generation, no coordinate templates |
| **Stage Direction** | `stickforge/direction` | the **performance director** — World Graph → **Blocking Graph**: proxemics/status blocking, eye-contact choreography, motivated movement (over the nav graph), scene rhythm, interaction reservation, and cross-scene continuity. Reuses `acting` + `world`; the camera observes this, it doesn't create it |
| **Parts** | `stickforge/parts` | **Character Design System** — per-category style registries (art providers) |
| Rig + Character | `stickforge/character` | cartoon/line skeletons (FK), `ActorDesign` assembly |
| Pose | `stickforge/pose` | named, blendable joint poses |
| Expression | `stickforge/expression` | facial-parameter emotions + blending |
| Animation | `stickforge/animation` | keyframed clips + procedural life |
| **Acting** | `stickforge/acting` | **emotional state machine + beat-based performance** (think→react→act, anticipation, eye acting, emotion-driven idle) |
| **Story** | `stickforge/story` | **script → beats → performed, subtitled scene**; multi-character dialogue staging + eye contact |
| **Voice** | `stickforge/voice` | **procedural lip-sync (visemes)** + a pluggable TTS interface (timing model) |
| Scene | `stickforge/scene` | scene graph, camera, timeline |
| Render | `stickforge/render` | `illustrated` (house style) builds a **scene graph in world space** and projects via `Camera2D`; `svg` (legacy) backend; motion FX |
| Export | `stickforge/export` | frames → HTML player / MP4 |

**Visual identity:** the default `illustrated` renderer produces clean flat
cartoon actors per [`STYLE_GUIDE.md`](STYLE_GUIDE.md) — assembled from `parts`,
never hardcoded. The procedural `svg` line-stickman is retained only as a legacy
backend and is not the product look.

## The 20 modules

| # | Requested module | Status | Where / how to extend |
|---|---|---|---|
| 1 | Asset Management System | **Built (intelligence)** | `registry/` — Asset Intelligence Engine: canonical schema (validated, forward-compatible), taxonomy, inverted-index semantic query, relationships/anchors/variants/constraints, versioned packs; scales to 50k+ assets (~1s index, sub-second query). `assets/` remains the runtime content library |
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
| 12 | Story Engine | **Built (cognitive layer)** | `narrative/` — Narrative Understanding Engine (story analysis + character models + Scene→Beat→Action segmentation, all confidence-scored) → typed **Intent Graph** → **Scene Planning Engine** → versioned, **validated Scene Graph** of semantic requirements (no asset refs). Pluggable analyzer (heuristic now, LLM later); 300 synthetic stories analyze+plan+validate in <1s. (`story/` remains the low-level beat/dialogue performer.) |
| 13 | Voice Sync Engine | **Built (basic)** | `voice/engine.py` — pluggable TTS registry + timing model (silent backend); beat/subtitle timing derives from it (real audio backends plug in) |
| 14 | Lip Sync Engine | **Built (basic)** | `voice/lipsync.py` — syllable→viseme stream drives `mouth_open`/`mouth_curve`, synced to each spoken beat (no audio needed) |
| 15 | Background Generator | **Built (procedural)** | `world/` Procedural World Simulation Engine — rooms/environments composed procedurally (no image gen, no templates), with lighting + weather + storytelling |
| 16 | Props Engine | **Built (procedural)** | `world/placement.py` — constraint-based placement resolving registry assets onto surfaces/anchors with collision + relationships |
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

## Stage Direction Engine (performances before cameras)

`stickforge/direction/` directs actors on the built world — the layer between
the World Engine and the (future) camera.

```python
from stickforge.direction import direct_scene, direct_story
g = direct_scene(world, scene_spec)        # -> BlockingGraph (validated)
g.marks            # who stands where + why (proxemics/status/posture)
g.beats            # timed move/look/gesture/speak/react/pause/interact (+ motivation)
graphs, state = direct_story(worlds, specs)  # continuity across scenes
```

- **proxemics.py** Hall distances + status/power + posture; **blocking.py**
  sequential placement (status claims space, fearful edge to exits, clear of
  furniture, readable separation); **performance.py** the planners
  (movement/eye-contact/gesture/interaction/emotional) + **scene rhythm**
  (enter→settle→look→pause→speak/gesture→react with emotion-driven timing);
  **continuity.py** persistent `CharacterState`; **validate.py** rejects
  in-furniture / overlap / broken-look / unreachable. Reuses `acting.emotion`
  for body-language content (no duplicate acting system).

Design choice (challenged): this engine owns *blocking, gaze, rhythm, and
continuity* and emits a structured **Blocking Graph** — it does not re-implement
per-actor acting (delegated to `acting`) and emits no cameras or curves. The
Director AI will choose *how to film* this performance; the Cinematic Engine
realizes the shots; neither changes how the actors behave.

## Procedural World Simulation Engine (story → living world)

`stickforge/world/` is the bridge between understanding and direction. It turns
a semantic Scene Graph into a fully-instantiated **World Graph**:

```python
from stickforge.narrative import understand_story, plan
from stickforge.world import build_world
spec = plan(understand_story("John nervously entered his interview on a rainy morning."))[0]
world = build_world(spec, seed=3)          # -> WorldGraph (validated)
world.to_scene_graph()                      # -> stage.SceneGraph for rendering
```

Pipeline: **storytelling** (wealth/cleanliness/style from the scene) → **room**
(parametric shell + slots, seed-varied — never a template) → **placement**
(each semantic requirement resolved against the registry and constraint-placed:
surface rules, collision, "on" relationships like laptop→desk) → **decoration**
→ **characters** → **interaction zones** (working/seating/entrance/path/
camera-safe) → **navigation graph** (Dijkstra pathfinding) → **lighting**
(motivated key/fill/ambient) → **weather** → **optimize** (instancing/LOD/cache)
→ **validate** (floating/overlap/blocked/inaccessible/scale).

Design choices (challenged): worlds are **composed from constraints over
registry assets**, not coordinate templates, and degrade to semantic
placeholders when no concrete asset exists — the contract is semantic, so it
works today with 12 assets and tomorrow with 100k. The World Graph is built on
the `stage` scene graph, so renderer/Cinematic consume it natively. Validated at
scale (120 stories → worlds, nearly all valid, <1s).

## Cognitive layer (the story brain — understanding before rendering)

`stickforge/narrative/` understands a story and emits a structured contract;
nothing downstream parses English.

```python
from stickforge.narrative import understand_story, plan, summarize_story
u = understand_story("John nervously entered his first interview on a rainy morning.")
summarize_story(u)        # genre/tone/setting/time/weather/mood/emotion-curve
plan(u)                   # -> [SceneSpec] validated Scene Graphs
```

Pipeline: **segment** (Scene→Beat→Action) → **analyze** (`StoryAnalysis`,
confidence-scored) + **characters** (`CharacterModel`, persistent) → **Intent
Graph** (typed goal/fear/conflict/emotion/audience/visual/comedy/retention
nodes) → **Scene Planner** (`SceneSpec`: environment, layout, camera targets,
semantic prop *queries*, lighting, mood, animation notes — never asset names) →
**validate** (no invalid graph reaches the renderer).

Key design choice (challenged & justified): the *contracts + pipeline* are
deterministic and versioned; the *inference* is a pluggable `Analyzer`. The
shipped `HeuristicAnalyzer` can be replaced by an `LLMAnalyzer` emitting the
same structures — improving IQ without touching any consumer. Every inference
carries a confidence score, which is exactly that seam.

The planner's prop requirements are **registry-shaped queries**, so the future
World Engine resolves them via the Asset Intelligence Engine and places results
into the spatial scene graph — the three layers compose cleanly.

## Asset Intelligence Engine (the knowledge base every engine queries)

`stickforge/registry/` is the single source of truth for assets. Engines never
touch files or names — they ask semantic questions:

```python
from stickforge.registry import default_registry, Placement
reg = default_registry()
reg.find_assets("a cozy sofa for a living room")     # ranked metadata
reg.supports("world:furniture.office_desk")          # {laptop, coffee_mug, ...}
reg.find_variants("chair.office")                    # variant set
reg.choose_variant("chair.office", "modern")         # best variant for intent
reg.anchor("world:furniture.office_desk", "top")     # named anchor (local)
reg.validate_scene([Placement("...painting", "floor")])  # constraint check
```

- **schema.py** canonical metadata (validated, *additive* — unknown fields
  preserved for forward compat), **taxonomy.py** extensible categories + open
  vocabularies, **index.py** inverted indices (fast at scale), **query.py**
  natural-phrase → ranked matches, **relationships.py** typed graph
  (supports/belongs_to/variant_of/depends_on), **constraints.py** composition
  validation (no ceiling lamps on the floor; no style mixing), **registry.py**
  the public service. Versioned packs (`registry/data/*.json`) — core + future
  marketplace content add assets with zero engine changes.

When the World Engine is built it constructs scenes *entirely* by querying this
registry and resolving anchors into the spatial foundation below.

## Spatial foundation (the substrate for World/Cinematic/Director/Universe)

`stickforge/stage/` makes rendering resolution- and screen-independent:

- **World space** (`world.py`) — resolution-independent units (`REFERENCE`
  across the short edge at zoom 1), a ground plane, and a `Viewport`.
- **Scene graph** (`node.py`, `scenegraph.py`) — a tree of `SceneNode`s with
  composable `Transform2D`s, named **anchors** (e.g. an actor's `hand`/`head`/
  `feet`, exposed per frame), and depth **layers** with **parallax**.
- **Camera2D** (`camera.py`) — the *only* world→screen projection
  (`project`/`unproject`), with `look_at`/`framed_on` helpers the Cinematic
  Engine will drive. The renderer no longer computes screen coordinates itself.

The legacy screen-fraction Scene API is bridged via `World.frac_to_world`, so
existing scenes render identically while new engines author in world space.
Next engines plug in here: the **World Engine** adds environment/prop nodes on
the background/ground layers; the **Cinematic Engine** drives the camera and
reads anchors for framing.

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
