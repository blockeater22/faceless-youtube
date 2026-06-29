"""Prop placement — constraint solving, never coordinate templates.

Each semantic requirement from the Scene Graph is resolved against the registry
(or a graceful placeholder), then placed by rules: wall items hang on the wall
band, floor items distribute along the floor lane with collision avoidance, and
"on" items snap to their host's surface anchor (desk → laptop). Seeded, so the
same scene yields many valid arrangements.
"""
from __future__ import annotations

from ..core.geometry import Vec2
from ..stage import Layer
from .schema import WorldObject

METER = 110.0      # world units per asset "meter" (reconciles registry bbox -> stage)

_DEFAULT_BBOX = {
    "desk": [2.4, 1.2], "chair": [1.0, 1.6], "sofa": [3.0, 1.4],
    "table": [2.6, 1.2], "laptop": [0.6, 0.4], "window": [1.6, 2.0],
    "door": [1.2, 2.4], "plant": [0.8, 1.2], "lamp": [0.8, 0.8],
    "painting": [1.2, 0.9], "mug": [0.3, 0.35], "monitor": [0.7, 0.5],
}


def _default_bbox(category: str, tags: list[str]) -> list[float]:
    for t in tags:
        if t in _DEFAULT_BBOX:
            return list(_DEFAULT_BBOX[t])
    return [1.2, 1.2]


def _resolve(registry, req: dict, story: dict):
    if registry is None:
        return None
    from ..registry import Query
    q = Query(category=req.get("category", ""), tags=req.get("tags", []),
              styles=story.get("styles", []), surface=req.get("surface", ""))
    res = registry.find_assets(q, limit=1)
    return res[0] if res else None


def _overlaps(a, b, pad=8.0):
    return not (a[1] + pad <= b[0] or a[0] >= b[1] + pad)


def _free_x(target, width, intervals, room, sign, tries=48):
    half = width / 2.0
    x = max(room.left + half, min(room.right - half, target))
    for _ in range(tries):
        iv = (x - half, x + half)
        if not any(_overlaps(iv, o) for o in intervals):
            return x
        x += sign * (width * 0.5 + 10)
        if x - half < room.left or x + half > room.right:
            sign = -sign
            x = max(room.left + half, min(room.right - half, target - sign * half))
    return x


class PropPlacementEngine:
    def place(self, spec, room, story, registry, rng):
        objects: list[WorldObject] = []
        floor_iv: list[tuple] = []
        hosts: dict[str, WorldObject] = {}
        deferred: list[tuple] = []
        wall_used: list[float] = []

        for i, req in enumerate(spec.prop_requirements):
            tags = req.get("tags", [])
            cat = req.get("category", "")
            role = req.get("role", "set")
            asset = _resolve(registry, req, story)
            raw_bbox = asset.bbox if asset else _default_bbox(cat, tags)
            bbox = [raw_bbox[0] * METER, raw_bbox[1] * METER]
            surface = req.get("surface") or (
                asset.placement.get("surface") if asset else "floor")
            sem = tags[0] if tags else (cat or "prop")
            obj = WorldObject(
                id=f"{spec.id}.prop{i}", semantic_role=sem, role=role, bbox=bbox,
                surface=surface, asset_query=req,
                asset_id=asset.id if asset else None,
                anchors=dict(asset.anchors) if asset else {},
                solid=(surface == "floor" and cat == "furniture"))

            if req.get("on"):
                deferred.append((obj, req["on"]))
                continue                              # placed after its host
            if surface == "wall":
                obj.position = Vec2(_wall_x(room, tags, wall_used, rng), room.wall_y)
                obj.layer = Layer.BACKGROUND
                obj.solid = False
            elif surface == "ceiling":
                obj.position = Vec2(rng.uniform(room.left * 0.4, room.right * 0.4),
                                    room.floor_y - room.wall_height)
                obj.layer = Layer.BACKGROUND
                obj.solid = False
            else:                                       # floor / any
                base = {"focus": 0.0, "seat": room.width * 0.15,
                        "set": room.width * 0.30, "decor": room.width * 0.40}.get(
                            role, room.width * 0.22)
                sign = rng.choice([-1, 1])
                x = _free_x(base * sign + rng.uniform(-40, 40), bbox[0],
                            floor_iv, room, sign)
                obj.position = Vec2(x, room.floor_y)
                obj.layer = Layer.MIDGROUND
                if obj.solid:
                    floor_iv.append(obj.interval())

            objects.append(obj)
            for t in tags:
                hosts[t] = obj

        # resolve "on" relationships (e.g., laptop on the desk's top anchor)
        for obj, host_tag in deferred:
            host = hosts.get(host_tag)
            if host:
                top = (host.anchor_world("top") if "top" in host.anchors
                       else Vec2(host.position.x, host.position.y - host.bbox[1] * 0.5))
                obj.position = Vec2(top.x, top.y)
                obj.parent = host.id
            else:
                obj.position = Vec2(_free_x(0, obj.bbox[0], floor_iv, room, 1),
                                    room.floor_y)
            obj.layer = Layer.MIDGROUND
            obj.solid = False
            objects.append(obj)
        return objects, floor_iv


def _wall_x(room, tags, used, rng):
    if "door" in tags and room.door_x is not None:
        return room.door_x
    if "window" in tags and room.window_x is not None:
        return room.window_x
    for _ in range(20):
        x = rng.uniform(room.left * 0.6, room.right * 0.6)
        if all(abs(x - u) > room.width * 0.12 for u in used):
            used.append(x)
            return x
    return rng.uniform(room.left * 0.6, room.right * 0.6)


class DecorationEngine:
    """Adds extra decoration to taste, driven by storytelling density."""

    def add(self, spec, room, story, objects, floor_iv, registry, rng):
        extra = []
        n = int(story.get("decoration_density", 0.4) * 3)
        has_wall = room.indoor and room.wall_height > 0
        kinds = ["plant", "painting"] if has_wall else ["plant"]
        for k in range(n):
            kind = rng.choice(kinds)
            surface = "wall" if kind == "painting" else "any"
            bbox = [v * METER for v in _DEFAULT_BBOX[kind]]
            o = WorldObject(id=f"{spec.id}.decor{k}", semantic_role=kind,
                            role="decor", bbox=bbox, surface=surface, solid=False,
                            layer=Layer.BACKGROUND if surface == "wall" else Layer.FOREGROUND)
            if surface == "wall":
                o.position = Vec2(_wall_x(room, [kind], [], rng), room.wall_y)
            else:
                o.position = Vec2(_free_x(room.width * 0.40 * rng.choice([-1, 1]),
                                          bbox[0], floor_iv, room, 1), room.floor_y)
            extra.append(o)
        return extra
