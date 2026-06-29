"""Navigation graph — characters request destinations, the world finds paths.

Waypoints at zones, character marks, and corridor points along the floor lane;
two are linked when no solid object sits fully between them. Pathfinding is
Dijkstra on the resulting graph (see :class:`NavGraph`).
"""
from __future__ import annotations

from ..core.geometry import Vec2
from .schema import NavGraph, NavNode


def build_nav(room, zones, objects) -> NavGraph:
    nav = NavGraph()
    marks: list[tuple[float, str]] = []

    for z in zones:
        if z.kind in ("entrance", "working", "seating", "conversation"):
            nid = f"nav.{z.id}"
            nav.add(NavNode(nid, Vec2(z.center.x, room.floor_y), z.kind))
            marks.append((z.center.x, nid))
    for o in objects:
        if o.role == "character":
            nid = f"nav.{o.id}"
            nav.add(NavNode(nid, Vec2(o.position.x, room.floor_y), "character"))
            marks.append((o.position.x, nid))
    for frac, name in [(-0.3, "wpL"), (0.0, "wpC"), (0.3, "wpR")]:
        nid = f"nav.{name}"
        nav.add(NavNode(nid, Vec2(room.width * frac, room.floor_y), "waypoint"))
        marks.append((room.width * frac, nid))

    solids = [o.interval() for o in objects if o.solid]
    marks.sort()
    for i in range(len(marks)):
        for j in range(i + 1, len(marks)):
            lo, hi = marks[i][0], marks[j][0]
            blocked = any(lo < a and b < hi for (a, b) in solids)
            if not blocked:
                nav.link(marks[i][1], marks[j][1])
    return nav
