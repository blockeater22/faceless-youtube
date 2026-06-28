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
    """A short narrated-style showcase exercising poses, faces, camera, packs."""
    lib = library or load_core_library()
    night = {"type": "night"}

    s1 = Scene.from_spec({
        "id": "hello", "duration": 2.6, "background": night,
        "caption": "Meet a stickforge actor — assembled from data.",
        "camera": {"zoom": 1.0},
        "actors": [{"id": "a", "character": "char.classic",
                    "clip_id": "clip.wave_hello", "pos": [0.5, 0.66],
                    "unit_scale": 0.36}],
    }, lib)

    s2 = Scene.from_spec({
        "id": "think", "duration": 3.0, "background": night,
        "caption": "Every pose and expression is a blendable asset.",
        "camera": {"zoom_keys": [{"t": 0, "value": 1.0},
                                 {"t": 3.0, "value": 1.18, "ease": "ease_in_out"}]},
        "actors": [{"id": "b", "character": "char.amber",
                    "clip_id": "clip.thinking", "pos": [0.5, 0.66],
                    "unit_scale": 0.36}],
    }, lib)

    s3 = Scene.from_spec({
        "id": "party", "duration": 2.4, "background": night,
        "caption": "Nothing is hardcoded — characters, clips, packs.",
        "camera": {"shake": 0.004},
        "actors": [
            {"id": "c", "character": "char.indigo", "clip_id": "clip.celebrate",
             "pos": [0.36, 0.68], "unit_scale": 0.32},
            {"id": "d", "character": "char.classic", "clip_id": "clip.celebrate",
             "pos": [0.64, 0.68], "unit_scale": 0.32, "facing": -1},
        ],
    }, lib)

    return Timeline(scenes=[s1, s2, s3])


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
