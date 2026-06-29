"""Room generation — procedural shells, not coordinate templates.

A :class:`Room` defines the *spatial frame* (width, wall band, floor line, door/
window positions, named slots) that the placement solver fills. Generators are
parametric and seed-jittered, so one environment yields thousands of unique
rooms. New environments register a params entry — no new code.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..core.registry import Registry
from ..stage import World

ROOM_GENERATORS: "Registry" = Registry("room-generator")

# per-environment parameters: base width, wall height, indoor, has door/window
_ENV = {
    "office":     dict(width=1500, wall=900, indoor=True, door=True, window=True),
    "home":       dict(width=1400, wall=880, indoor=True, door=True, window=True),
    "school":     dict(width=1600, wall=920, indoor=True, door=True, window=True),
    "restaurant": dict(width=1700, wall=900, indoor=True, door=True, window=True),
    "shop":       dict(width=1500, wall=900, indoor=True, door=True, window=True),
    "studio":     dict(width=1500, wall=950, indoor=True, door=True, window=False),
    "park":       dict(width=1900, wall=0,   indoor=False, door=False, window=False),
    "street":     dict(width=1900, wall=700, indoor=False, door=False, window=False),
    "outdoor":    dict(width=1900, wall=0,   indoor=False, door=False, window=False),
}


@dataclass
class Room:
    env: str
    room_type: str
    width: float
    wall_height: float
    floor_y: float
    indoor: bool
    door_x: float | None = None
    window_x: float | None = None
    styles: list = field(default_factory=list)
    slots: dict = field(default_factory=dict)

    @property
    def left(self) -> float:
        return -self.width / 2.0

    @property
    def right(self) -> float:
        return self.width / 2.0

    @property
    def wall_y(self) -> float:
        return self.floor_y - self.wall_height * 0.45


def generate_room(spec, story: dict, rng) -> Room:
    env = spec.environment.get("environment", "") or "generic"
    factory = ROOM_GENERATORS.get(env) if env in ROOM_GENERATORS \
        else ROOM_GENERATORS.get("generic")
    return factory(spec, story, rng)


def _make(env: str):
    def gen(spec, story, rng) -> Room:
        p = _ENV.get(env, dict(width=1400, wall=860, indoor=True, door=True, window=True))
        # seed jitter -> unique-but-plausible rooms; wealth -> larger spaces
        scale = {"high": 1.15, "mid": 1.0}.get(story.get("wealth"), 1.0)
        width = p["width"] * scale * rng.uniform(0.92, 1.12)
        floor_y = World.GROUND_Y
        room = Room(env=env, room_type=spec.environment.get("room_type", ""),
                    width=width, wall_height=p["wall"], floor_y=floor_y,
                    indoor=p["indoor"], styles=story.get("styles", []))
        if p["door"]:
            room.door_x = width * rng.uniform(0.30, 0.42) * rng.choice([-1, 1])
        if p["window"]:
            wx = width * rng.uniform(0.22, 0.36)
            room.window_x = -wx if (room.door_x or 0) > 0 else wx
        room.slots = {"center": 0.0, "left": -width * 0.30, "right": width * 0.30,
                      "far_left": -width * 0.42, "far_right": width * 0.42}
        return room
    return gen


for _env in list(_ENV) + ["generic"]:
    ROOM_GENERATORS.register(_env, _make(_env if _env in _ENV else "office"))
