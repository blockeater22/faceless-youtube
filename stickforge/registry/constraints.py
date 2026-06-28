"""Composition constraints — reject impossible scenes before they render.

A scene is a list of :class:`Placement` s (an asset on a surface, in an
environment). Constraint rules (an extensible registry) check the composition
and return :class:`Issue` s. The World Engine will run these before committing a
layout, so "a ceiling lamp on the floor" or a mixed-style room never renders.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..core.registry import Registry
from .validate import Issue

CONSTRAINTS: "Registry" = Registry("constraint")

# style families that read as incompatible if mixed in one scene
_STYLE_FAMILY = {
    "modern": "clean", "minimal": "clean", "corporate": "clean", "flat": "clean",
    "fantasy": "stylized", "sci-fi": "stylized", "comic": "stylized",
    "cute": "soft", "hand-drawn": "soft", "whiteboard": "soft",
}


@dataclass
class Placement:
    asset_id: str
    surface: str = "floor"           # the surface it was actually placed on
    environment: str = ""            # the scene environment


def validate_composition(placements: list[Placement], registry,
                         environment: str = "") -> list[Issue]:
    issues: list[Issue] = []
    for rule in CONSTRAINTS:
        issues.extend(CONSTRAINTS.get(rule)(placements, registry, environment))
    return issues


@CONSTRAINTS.register("placement_surface")
def _surface(placements, registry, environment):
    out = []
    for p in placements:
        m = registry.get(p.asset_id) if p.asset_id in registry else None
        if not m:
            continue
        need = m.placement.get("surface", "floor")
        if need not in ("any", p.surface):
            out.append(Issue("error", "placement",
                             f"{m.id} must sit on {need!r}, not {p.surface!r}"))
    return out


@CONSTRAINTS.register("style_consistency")
def _styles(placements, registry, environment):
    fams = set()
    for p in placements:
        m = registry.get(p.asset_id) if p.asset_id in registry else None
        if m:
            for st in m.styles:
                fams.add(_STYLE_FAMILY.get(st, st))
    if len(fams) > 1:
        return [Issue("warning", "style",
                      f"mixed style families in one scene: {sorted(fams)}")]
    return []


@CONSTRAINTS.register("environment_fit")
def _environment(placements, registry, environment):
    if not environment:
        return []
    out = []
    for p in placements:
        m = registry.get(p.asset_id) if p.asset_id in registry else None
        if m and m.environments and environment not in m.environments:
            out.append(Issue("warning", "environment",
                             f"{m.id} is unusual in a {environment!r} scene"))
    return out
