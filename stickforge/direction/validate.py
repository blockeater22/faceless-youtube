"""Blocking validation — reject unstageable performances.

Catches characters inside furniture, awkward overlaps (unreadable silhouettes),
broken look targets, unreachable interactions, and dead space. Writes status
into ``graph.validation``.
"""
from __future__ import annotations

_MIN_SEP = 110.0


def validate_blocking(graph, world) -> list[dict]:
    issues: list[dict] = []

    def err(f, m): issues.append({"level": "error", "field": f, "msg": m})
    def warn(f, m): issues.append({"level": "warning", "field": f, "msg": m})

    solids = [(o.id, o.interval()) for o in world.objects if o.solid]
    names = set(graph.marks)

    # characters inside furniture
    for name, mk in graph.marks.items():
        for oid, (a, b) in solids:
            if a + 20 < mk.position.x < b - 20:
                err("furniture", f"{name} stands inside {oid}")

    # silhouette overlap
    xs = sorted((m.position.x, n) for n, m in graph.marks.items())
    for i in range(1, len(xs)):
        if xs[i][0] - xs[i - 1][0] < _MIN_SEP:
            err("overlap", f"{xs[i-1][1]} and {xs[i][1]} overlap (unreadable)")

    # broken look targets + unreachable interactions
    obj_ids = {o.id for o in world.objects}
    for b in graph.beats:
        if b.kind == "look":
            tgt = b.data.get("target")
            if tgt not in (None, "focus") and tgt not in names:
                err("look", f"{b.actor} looks at missing target {tgt!r}")
        if b.kind == "interact" and b.data.get("object") not in obj_ids:
            warn("interact", f"{b.actor} interacts with missing object")

    # dead space: a lone actor parked far off-centre
    if len(graph.marks) == 1:
        only = next(iter(graph.marks.values()))
        if abs(only.position.x) > world.bounds.get("width", 1400) * 0.4:
            warn("staging", "single actor pushed to the edge (dead space)")

    status = "valid" if not any(i["level"] == "error" for i in issues) else "invalid"
    graph.validation = {"status": status, "issues": issues}
    return issues
