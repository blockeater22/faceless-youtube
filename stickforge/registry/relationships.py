"""Typed relationship graph (supports / belongs_to / variant_of / depends_on).

Built automatically from asset metadata, so engines traverse meaning instead of
guessing: "what can sit on a desk?", "what belongs in an office?", "what does
this asset depend on?". Reverse edges are maintained for fast inverse queries.
"""
from __future__ import annotations

from dataclasses import dataclass

from .schema import AssetMeta

SUPPORTS = "supports"
BELONGS_TO = "belongs_to"
VARIANT_OF = "variant_of"
DEPENDS_ON = "depends_on"


@dataclass(frozen=True)
class Relationship:
    src: str
    type: str
    dst: str


class RelationshipGraph:
    def __init__(self) -> None:
        self._out: dict[str, dict[str, set[str]]] = {}
        self._in: dict[str, dict[str, set[str]]] = {}

    def _edge(self, src: str, rtype: str, dst: str) -> None:
        self._out.setdefault(src, {}).setdefault(rtype, set()).add(dst)
        self._in.setdefault(dst, {}).setdefault(rtype, set()).add(src)

    def add_asset(self, m: AssetMeta) -> None:
        for dst in m.supports:
            self._edge(m.id, SUPPORTS, dst.lower())
        for dst in m.belongs_to:
            self._edge(m.id, BELONGS_TO, dst.lower())
        for dst in m.dependencies:
            self._edge(m.id, DEPENDS_ON, dst)
        if m.variant_of:
            self._edge(m.id, VARIANT_OF, m.variant_of)

    def out(self, src: str, rtype: str) -> set[str]:
        return set(self._out.get(src, {}).get(rtype, set()))

    def incoming(self, dst: str, rtype: str) -> set[str]:
        return set(self._in.get(dst.lower(), {}).get(rtype, set()))

    def edges(self, src: str) -> list[Relationship]:
        return [Relationship(src, rt, d)
                for rt, ds in self._out.get(src, {}).items() for d in ds]
