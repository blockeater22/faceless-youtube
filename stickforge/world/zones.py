"""Interaction zones — characters target semantics, not raw coordinates.

From the room + placed objects we derive working/seating/conversation/entrance/
path/camera-safe zones. The Director/Acting engines later say "go to the
working area" rather than computing pixels.
"""
from __future__ import annotations

from ..core.geometry import Vec2
from .schema import InteractionZone


def generate_zones(room, objects, spec) -> list[InteractionZone]:
    zones: list[InteractionZone] = []
    fy = room.floor_y

    if room.door_x is not None:
        zones.append(InteractionZone("zone.entrance", "entrance",
                                     Vec2(room.door_x, fy), tags=["door"]))

    focus = next((o for o in objects if o.role == "focus"), None)
    if focus:
        zones.append(InteractionZone("zone.working", "working",
                                     Vec2(focus.position.x, fy),
                                     tags=["focus", focus.semantic_role]))

    for i, o in enumerate(objects):
        if o.role == "seat" or o.semantic_role in ("chair", "sofa"):
            zones.append(InteractionZone(f"zone.seat{i}", "seating",
                                         Vec2(o.position.x, fy),
                                         tags=[o.semantic_role]))

    chars = [o for o in objects if o.role == "character"]
    if len(chars) >= 2:
        cx = sum(o.position.x for o in chars) / len(chars)
        zones.append(InteractionZone("zone.conversation", "conversation",
                                     Vec2(cx, fy), capacity=len(chars)))

    zones.append(InteractionZone("zone.path", "path", Vec2(0, fy),
                                 size=Vec2(room.width * 0.9, 90), tags=["walkable"]))
    zones.append(InteractionZone("zone.camera_safe", "camera_safe",
                                 Vec2(0, fy - 180),
                                 size=Vec2(room.width * 0.7, 420)))
    return zones
