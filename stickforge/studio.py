"""High-level facade: load the core library and assemble ready-to-render demos.

This is the friendly entry point that ties the layers together; everything it
does is also available piecemeal through the individual modules.
"""
from __future__ import annotations

from pathlib import Path

from .assets.library import AssetLibrary
from .expression.expression import register_expression
from .pose.pose import register_pose
from .scene.scene import Scene, Timeline


def packs_dir() -> Path:
    return Path(__file__).parent / "data" / "packs"


def register_library_assets(library: AssetLibrary) -> None:
    """Make pose/expression assets referenceable by id from clips."""
    for a in library.of_type("pose"):
        register_pose(a.id, a.data, overwrite=True)
    for a in library.of_type("expression"):
        register_expression(a.id, a.data, overwrite=True)


def load_core_library() -> AssetLibrary:
    lib = AssetLibrary()
    lib.load_dir(packs_dir())
    register_library_assets(lib)
    return lib


# --------------------------------------------------------------------------- #
# Demo builders
# --------------------------------------------------------------------------- #
def build_demo_timeline(library: AssetLibrary | None = None) -> Timeline:
    """A short showcase of illustrated actors acting, with camera + packs."""
    lib = library or load_core_library()
    night = {"type": "night"}

    s1 = Scene.from_spec({
        "id": "hello", "duration": 2.6, "background": night,
        "caption": "Meet Max — an illustrated actor, assembled from parts.",
        "camera": {"zoom": 1.0},
        "actors": [{"id": "a", "character": "actor.max",
                    "clip_id": "clip.wave_hello", "pos": [0.5, 0.62],
                    "unit_scale": 0.34}],
    }, lib)

    s2 = Scene.from_spec({
        "id": "think", "duration": 3.0, "background": night,
        "caption": "Every part — hair, eyes, body — is a swappable asset.",
        "camera": {"zoom_keys": [{"t": 0, "value": 1.0},
                                 {"t": 3.0, "value": 1.18, "ease": "ease_in_out"}]},
        "actors": [{"id": "b", "character": "actor.sage",
                    "clip_id": "clip.thinking", "pos": [0.5, 0.62],
                    "unit_scale": 0.34}],
    }, lib)

    s3 = Scene.from_spec({
        "id": "party", "duration": 2.4, "background": night,
        "caption": "Recombine components into unlimited characters.",
        "camera": {"shake": 0.004},
        "actors": [
            {"id": "c", "character": "actor.nova", "clip_id": "clip.celebrate",
             "pos": [0.35, 0.64], "unit_scale": 0.30},
            {"id": "d", "character": "actor.pip", "clip_id": "clip.celebrate",
             "pos": [0.66, 0.64], "unit_scale": 0.30, "facing": -1},
        ],
    }, lib)

    return Timeline(scenes=[s1, s2, s3])


def build_character_lab(library: AssetLibrary | None = None) -> Scene:
    """A lineup of distinct actors — proof that the component library
    recombines into unlimited, on-brand characters."""
    from .parts import combination_count
    lib = library or load_core_library()
    ids = [a.id for a in lib.of_type("character") if a.id.startswith("actor.")]
    actors, props = [], []
    n = len(ids)
    for i, cid in enumerate(ids):
        fx = (i + 0.5) / n
        actors.append({"id": cid, "character": cid, "pos": [fx, 0.56],
                       "unit_scale": 0.155, "life": 0.0})
        props.append({"type": "label", "text": lib.get(cid).name,
                      "pos": [fx, 0.74], "font": 0.026, "color": "#1b1b1b"})
    combos = combination_count()
    scene = Scene.from_spec({
        "id": "lab", "duration": 1.0,
        "background": {"type": "plain", "color": "#fbfbf7"},
        "caption": f"One component library -> {combos:,} possible actors.",
        "actors": actors, "props": props,
    }, lib)
    return scene


_CAST_ORDER = ["kid", "clerk", "sage", "diva", "hero", "brute"]


def build_cast(library: AssetLibrary | None = None) -> Scene:
    """The personality-first cast: each archetype in its signature stance and
    resting expression — distinct silhouettes, proportions, and body language."""
    from .character.archetype import ARCHETYPES
    lib = library or load_core_library()
    actors, props = [], []
    n = len(_CAST_ORDER)
    us, ground = 0.185, 0.80
    for i, aid in enumerate(_CAST_ORDER):
        arch = ARCHETYPES.get(aid)
        fx = (i + 0.5) / n
        py = ground - (arch.thigh + arch.shin) * us      # align feet to a baseline
        actors.append({
            "id": aid, "character": {"id": aid, "archetype": aid},
            "clip": {"duration": 1.0,
                     "poses": [{"t": 0, "pose": arch.base_pose}],
                     "expressions": [{"t": 0, "expr": arch.base_expression}],
                     "hands": [{"t": 0, **arch.hands}]},
            "pos": [fx, py], "unit_scale": us, "life": 0.0})
        props.append({"type": "label", "text": f"{arch.name} ({arch.shape})",
                      "pos": [fx, 0.88], "font": 0.020, "color": "#1b1b1b"})
    return Scene.from_spec({
        "id": "cast", "duration": 1.0,
        "background": {"type": "plain", "color": "#fbfbf7"},
        "caption": "Personality-first cast — distinct silhouettes & body language.",
        "actors": actors, "props": props}, lib)


def build_silhouette_test(library: AssetLibrary | None = None) -> Scene:
    """The same cast — rendered as solid silhouettes (readability check)."""
    scene = build_cast(library)
    scene.id = "silhouettes"
    scene.caption = "Silhouette test — each character reads without any detail."
    scene.background = {"type": "plain", "color": "#fbfbf7"}
    for p in scene.props:
        p["color"] = "#1b1b1b"
    return scene


_DEFAULT_SCRIPT = """\
(a quiet night under the stars)
happy: What a beautiful evening.
curious: Wait... what is that up there?
No way!
excited: It's a shooting star!
thinking: Hmm... what should I wish for?
hopeful: I wish this moment could last forever.
"""


def build_story(script: str | None = None, actor_id: str = "actor.max") -> Scene:
    """Compile a written script into a performed, subtitled scene."""
    from .story import storyboard
    return storyboard(script or _DEFAULT_SCRIPT, actor_id=actor_id)


def build_pose_gallery(n: int = 8, seed: int = 1,
                       library: AssetLibrary | None = None) -> Scene:
    """Top-scoring generated poses laid out in a row (render with silhouette=True
    for the silhouette test). Proof the pose pipeline yields readable poses."""
    from .pose import lab
    from .scene.scene import Actor
    from .character.character import build_character
    from .animation.clip import AnimationClip
    lib = library or load_core_library()
    best = lab.generate(max(40, n * 5), seed=seed)[:n]
    actors, props = [], []
    for i, r in enumerate(best):
        fx = (i + 0.5) / n
        clip = AnimationClip.from_spec({"duration": 1.0,
                                        "poses": [{"t": 0, "pose": r["pose"]}],
                                        "expressions": [{"t": 0, "expr": "determined"}]})
        actors.append(Actor(character=build_character({"id": "actor.max"}),
                            clip=clip, pos=(fx, 0.60), unit_scale=0.115,
                            life=0.0, id=f"p{i}"))
        props.append({"type": "label", "text": f"{r['score']:.1f}",
                      "pos": [fx, 0.74], "font": 0.024, "color": "#1b1b1b"})
    return Scene(id="pose_gallery", duration=1.0,
                 background={"type": "plain", "color": "#fbfbf7"},
                 actors=actors, props=props,
                 caption="Generated from line-of-action + weight — top scores shown.")


def build_emotion_board(library: AssetLibrary | None = None,
                        emotions: list[str] | None = None) -> Scene:
    """One actor in each emotion's *body* pose — readability proof (works in
    silhouette too: render with silhouette=True)."""
    from .acting.emotion import EMOTIONS
    from .acting.performance import emotion_clip
    from .scene.scene import Actor
    from .character.character import build_character
    lib = library or load_core_library()
    emotions = emotions or ["happy", "excited", "confident", "curious",
                            "confused", "suspicious", "shocked", "angry",
                            "sad", "nervous", "determined", "relieved"]
    cols = 6
    actors, props = [], []
    for i, emo in enumerate(emotions):
        if emo not in EMOTIONS:
            continue
        col, row = i % cols, i // cols
        fx = (col + 0.5) / cols
        fy = 0.34 + row * 0.40
        clip = emotion_clip(emo, dur=1.0, loop=False)
        actors.append(Actor(character=build_character({"id": "actor.max"}),
                            clip=clip, pos=(fx, fy), unit_scale=0.10, life=0.0,
                            id=f"e{i}"))
        props.append({"type": "label", "text": emo, "pos": [fx, fy + 0.12],
                      "font": 0.020, "color": "#1b1b1b"})
    return Scene(id="emotions", duration=1.0,
                 background={"type": "plain", "color": "#fbfbf7"},
                 actors=actors, props=props,
                 caption="Acting reads in the body — emotion is posture, not just face.")


def build_silent_story(actor_id: str = "actor.max",
                       library: AssetLibrary | None = None) -> Scene:
    """A wordless beat performance: notice -> think -> react -> delight.
    Should be understandable with the sound (and captions) off."""
    from .acting.performance import perform, Beat
    from .scene.scene import Actor
    from .character.character import build_character
    lib = library or load_core_library()
    beats = [
        Beat("neutral", 1.0, "act"),
        Beat("curious", 1.6, "act", text="...something catches their eye"),
        Beat("confused", 1.6, "think", look=(0.5, -0.4), text="wait — what is that?"),
        Beat("shocked", 1.1, "react", text="!"),
        Beat("excited", 2.2, "act", text="amazing!"),
    ]
    clip = perform(beats, loop=False)
    actor = Actor(character=build_character({"id": actor_id}), clip=clip,
                  pos=(0.42, 0.64), unit_scale=0.34, life=1.0, id="star")
    # the thing being reacted to (staging): a glowing star, screen-right
    props = [{"type": "fx", "name": "stars", "pos": [0.80, 0.42],
              "size": 0.05, "color": "#ffd34d"}]
    return Scene(id="silent_story", duration=clip.duration,
                 background={"type": "night"}, actors=[actor], props=props,
                 caption="(sound off) — can you read the story?")


def build_acting_demo(actor_id: str = "actor.max",
                      library: AssetLibrary | None = None) -> Scene:
    """One actor performing a beat sequence through the Acting Engine —
    thinking before reacting, with anticipation and intentional eye acting."""
    from .acting.performance import perform, Beat
    from .scene.scene import Actor
    from .character.character import build_character
    lib = library or load_core_library()
    beats = [
        Beat("happy", 1.3, "act"),
        Beat("curious", 1.4, "act", text="hm?"),
        Beat("confused", 1.6, "think", look=(0.4, -0.4)),
        Beat("shocked", 1.0, "react"),
        Beat("excited", 1.8, "act"),
        Beat("confident", 1.6, "act"),
    ]
    from .scene.camera import Camera
    clip = perform(beats, loop=True)
    actor = Actor(character=build_character({"id": actor_id}), clip=clip,
                  pos=(0.5, 0.62), unit_scale=0.36, life=1.0, id="star")
    return Scene(id="acting", duration=clip.duration, background={"type": "night"},
                 caption="Acting first — think, react, then move.",
                 camera=Camera(zoom=1.08), actors=[actor])


def build_expression_showcase(emotions: list[str] | None = None) -> Scene:
    """A static grid-ish lineup of one character per emotion (a contact sheet)."""
    from .expression.expression import EXPRESSIONS
    from .animation.clip import AnimationClip

    emotions = emotions or ["happy", "sad", "angry", "surprised", "thinking",
                            "laughing", "scared", "sleepy", "smirk", "crying"]
    actors = []
    n = len(emotions)
    cols = 5
    for i, emo in enumerate(emotions):
        if emo not in EXPRESSIONS:
            continue
        col, row = i % cols, i // cols
        clip = AnimationClip.from_spec({
            "duration": 1.0,
            "poses": [{"t": 0, "pose": "idle"}],
            "expressions": [{"t": 0, "expr": emo}],
        }, f"show_{emo}")
        actors.append({
            "id": f"e{i}", "character": "char.classic", "clip": None,
            "pos": [(col + 0.5) / cols, 0.30 + row * 0.34], "unit_scale": 0.12,
            "_clip_obj": clip, "_label": emo,
        })
    # Build the Scene directly (we need real clip objects + labels as props).
    from .scene.scene import Actor
    from .character.character import build_character
    real_actors, props = [], []
    for a in actors:
        real_actors.append(Actor(
            character=build_character({"id": "char.classic", "ink": "#f2ede1"}),
            clip=a["_clip_obj"], pos=tuple(a["pos"]),
            unit_scale=a["unit_scale"], life=0.0, id=a["id"]))
        props.append({"type": "label", "text": a["_label"],
                      "pos": [a["pos"][0], a["pos"][1] + 0.12], "font": 0.022})
    return Scene(id="expressions", duration=1.0,
                 background={"type": "night"}, actors=real_actors, props=props,
                 caption="Expression engine — one parameter space, many emotions.")
