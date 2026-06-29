"""Character blocking — positions that communicate, never random coordinates.

Uses the World Engine's interaction zones + proxemics + status: the highest-
status actor claims central/open space, lower-status (and fearful) actors edge
toward exits and shrink, relationship sets interpersonal distance, and silhouette
separation + furniture avoidance keep staging readable.
"""
from __future__ import annotations

from ..core.geometry import Vec2
from .bodylanguage import body_language
from .proxemics import preferred_distance, status_for, posture_for
from .schema import BlockingMark

_MIN_SEP = 130.0     # world units; keeps silhouettes readable


def _relation(roles: set[str]) -> str:
    if roles & {"interviewer", "boss", "teacher", "manager"}:
        return "professional"
    if "friend" in roles:
        return "friend"
    if roles & {"parent", "child"}:
        return "family"
    return "acquaintance"


def _zone_x(world, kind: str):
    for z in world.zones:
        if z.kind == kind:
            return z.center.x
    return None


def _find_spot(desired, solids, placed, limit):
    """Nearest x to ``desired`` that clears furniture and keeps separation."""
    step = _MIN_SEP / 2
    for k in range(60):
        for s in ((1, -1) if k else (1,)):
            x = desired + s * step * k
            if abs(x) > limit:
                continue
            in_solid = any(a - 30 < x < b + 30 for (a, b) in solids)
            too_close = any(abs(x - p) < _MIN_SEP for p in placed)
            if not in_solid and not too_close:
                return x
    return max(-limit, min(limit, desired))


def plan_blocking(world, spec, state=None, rng=None) -> dict:
    chars = list(spec.characters or [])
    if not chars:
        return {}
    floor_y = world.bounds.get("floor_y", 300.0)
    width = world.bounds.get("width", 1400.0)
    solids = [o.interval() for o in world.objects if o.solid]
    entrance_x = _zone_x(world, "entrance")
    center_x = (_zone_x(world, "conversation") or _zone_x(world, "working") or 0.0)

    infos = []
    for c in chars:
        emo = c.get("emotion", "neutral")
        role = c.get("role", "character")
        infos.append({"name": c["name"], "emotion": emo, "role": role,
                      "status": status_for(emo, role)})
    infos.sort(key=lambda d: -d["status"])

    # desired targets from proxemics/status
    targets: dict[str, float] = {}
    if len(infos) == 1:
        targets[infos[0]["name"]] = center_x
    elif len(infos) == 2:
        a, b = infos
        d = max(_MIN_SEP * 1.4, preferred_distance(_relation({a["role"], b["role"]})))
        targets[a["name"]] = center_x - d / 2     # higher status on one side
        targets[b["name"]] = center_x + d / 2
        if b["status"] < 0.32 and entrance_x is not None:   # fearful -> toward exit
            targets[b["name"]] = targets[b["name"]] * 0.5 + entrance_x * 0.5
    else:
        for info, x in zip(infos, _fan(len(infos), width)):
            targets[info["name"]] = center_x * 0.3 + x

    # sequential placement (status order): clear furniture + keep separation
    limit = 0.46 * width
    placed: list[float] = []
    xs: dict[str, float] = {}
    for info in infos:
        x = _find_spot(targets[info["name"]], solids, placed, limit)
        placed.append(x)
        xs[info["name"]] = x

    marks = {}
    for info in infos:
        name = info["name"]
        x = xs[name]
        others = [xs[o] for o in xs if o != name]
        if others:
            target = sum(others) / len(others)
            facing = 1 if target >= x else -1
        else:
            facing = 1
        zone = ("working" if abs(x - (center_x or 0)) < 40 and len(infos) == 1
                else "conversation" if len(infos) >= 2 else "working")
        marks[name] = BlockingMark(
            actor=name, zone=zone, position=Vec2(x, floor_y), facing=facing,
            posture=posture_for(info["emotion"]), status=info["status"],
            body_language=body_language(info["emotion"]))
    return marks


def _fan(n: int, width: float) -> list[float]:
    span = width * 0.7
    if n == 1:
        return [0.0]
    step = span / (n - 1)
    # centre-out ordering: index 0 (highest status) gets centre
    raw = [(-span / 2 + i * step) for i in range(n)]
    raw.sort(key=lambda v: abs(v))
    return raw
