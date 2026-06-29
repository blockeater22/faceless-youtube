"""World validation — reject impossible layouts before anything renders.

Detects floating objects, overlapping solids, orphaned "on" objects, blocked/
inaccessible navigation, and out-of-range scale. Writes status back into
``world.validation``.
"""
from __future__ import annotations


def validate_world(world) -> list[dict]:
    issues: list[dict] = []

    def err(f, m): issues.append({"level": "error", "field": f, "msg": m})
    def warn(f, m): issues.append({"level": "warning", "field": f, "msg": m})

    floor_y = world.bounds.get("floor_y", 300.0)
    ids = {o.id for o in world.objects}

    # floating / mis-surfaced objects
    for o in world.objects:
        if o.parent:                              # "on" objects ride a host
            if o.parent not in ids:
                err("parent", f"{o.id} references missing host {o.parent}")
            continue
        if o.surface == "floor" and abs(o.position.y - floor_y) > 2.0:
            err("floating", f"{o.id} floats off the floor")
        if o.surface == "wall" and o.position.y >= floor_y:
            err("floating", f"{o.id} wall item not on the wall")

    # overlapping solids
    solids = [(o.id, o.interval()) for o in world.objects if o.solid]
    for i in range(len(solids)):
        for j in range(i + 1, len(solids)):
            a, b = solids[i][1], solids[j][1]
            overlap = min(a[1], b[1]) - max(a[0], b[0])
            if overlap > 12.0:
                err("overlap", f"{solids[i][0]} overlaps {solids[j][0]}")

    # navigation accessibility: every character reachable from the entrance
    entrance = next((n for n in world.nav.nodes if "entrance" in n), None)
    if entrance:
        for o in world.objects:
            if o.role == "character":
                node = f"nav.{o.id}"
                if node in world.nav.nodes and not world.nav.path(entrance, node):
                    err("navigation", f"{o.id} is unreachable from the entrance")

    # scale sanity
    for o in world.objects:
        if not (0.3 <= o.scale <= 3.0):
            warn("scale", f"{o.id} has unusual scale {o.scale}")

    status = "valid" if not any(i["level"] == "error" for i in issues) else "invalid"
    world.validation = {"status": status, "issues": issues}
    return issues
