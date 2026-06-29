"""Lighting — a key/fill/ambient rig derived from time, mood, and the window.

No pixels: produces :class:`LightSource` descriptors (position/color/intensity)
that the Cinematic/Render layers consume. Light motivation comes from the world
(the window is the key when present) and the story (dim & cool when somber).
"""
from __future__ import annotations

from ..core.geometry import Vec2
from .schema import LightSource


def build_lighting(room, spec, story, objects) -> list[LightSource]:
    pal = story.get("palette", {})
    intensity = {"night": 0.5, "evening": 0.8}.get(spec.time, 1.0)
    if spec.mood in ("sad", "scared", "angry"):
        intensity *= 0.7
    key_x = room.window_x if room.window_x is not None else room.right * 0.5
    top = room.floor_y - room.wall_height

    lights = [
        LightSource("light.key", Vec2(key_x, top),
                    pal.get("key", "#fff3da"), intensity, "key"),
        LightSource("light.fill", Vec2(-key_x, room.floor_y - room.wall_height * 0.8),
                    pal.get("ambient", "#cfe0f5"), intensity * 0.5, "fill"),
        LightSource("light.ambient", Vec2(0, top),
                    pal.get("ambient", "#cfe0f5"), intensity * 0.4, "ambient"),
    ]
    for o in objects:
        if o.semantic_role == "lamp":
            lights.append(LightSource(f"light.{o.id}", Vec2(o.position.x, o.position.y),
                                      "#ffd9a0", intensity * 0.6, "practical"))
    return lights
