"""Metadata validation — fail fast on bad assets, warn on unknown vocab.

Errors block ingestion (a marketplace pack with these is rejected); warnings are
advisory (unknown styles/environments are allowed so the vocabulary can grow).
"""
from __future__ import annotations

from dataclasses import dataclass

from .schema import AssetMeta
from .taxonomy import in_vocab, is_category


@dataclass(frozen=True)
class Issue:
    level: str        # "error" | "warning"
    field: str
    message: str

    def __str__(self) -> str:
        return f"[{self.level}] {self.field}: {self.message}"


def validate_meta(m: AssetMeta) -> list[Issue]:
    issues: list[Issue] = []

    def err(f, msg): issues.append(Issue("error", f, msg))
    def warn(f, msg): issues.append(Issue("warning", f, msg))

    if not m.id or ":" not in m.id and "." not in m.id:
        err("id", "must be a namespaced id like 'pack:category.name'")
    if not m.category:
        err("category", "required")
    elif not is_category(m.category):
        warn("category", f"unknown category {m.category!r} (register it)")

    if not (isinstance(m.bbox, (list, tuple)) and len(m.bbox) == 2):
        err("bbox", "must be [width, height]")
    if not (0.0 <= m.quality_score <= 10.0):
        err("quality_score", "must be in [0, 10]")
    if m.lod_levels < 1:
        err("lod_levels", "must be >= 1")

    surface = m.placement.get("surface", "floor")
    if not in_vocab("surfaces", surface):
        warn("placement.surface", f"unknown surface {surface!r}")
    for st in m.styles:
        if not in_vocab("styles", st):
            warn("styles", f"unknown style {st!r}")
    for env in m.environments:
        if not in_vocab("environments", env):
            warn("environments", f"unknown environment {env!r}")
    for act in m.supported_actions:
        if not in_vocab("actions", act):
            warn("supported_actions", f"unknown action {act!r}")

    for name, pt in {**m.anchors, **m.interaction_points}.items():
        if not (isinstance(pt, (list, tuple)) and len(pt) == 2):
            err("anchors", f"anchor {name!r} must be [x, y]")

    return issues


def errors(issues: list[Issue]) -> list[Issue]:
    return [i for i in issues if i.level == "error"]
