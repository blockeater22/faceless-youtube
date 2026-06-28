"""Inverted indices — the reason queries stay fast at 100k assets.

Like the Unreal Asset Registry, we index *metadata* (not the assets themselves)
so a query narrows to candidate ids by facet intersection/union before any
scoring, keeping lookups O(matches) rather than O(total assets).
"""
from __future__ import annotations

from .schema import AssetMeta

# facet name -> attribute that yields its value(s) on an AssetMeta
_LIST_FACETS = ["tags", "styles", "themes", "environments", "room_types",
                "materials", "supported_actions"]
_SCALAR_FACETS = ["category", "subcategory", "layer", "variant_key"]


class AssetIndex:
    def __init__(self) -> None:
        self.by_id: dict[str, AssetMeta] = {}
        self.facets: dict[str, dict[str, set[str]]] = {}

    def _bucket(self, facet: str, value: str) -> set[str]:
        return self.facets.setdefault(facet, {}).setdefault(str(value).lower(), set())

    def add(self, m: AssetMeta) -> None:
        self.by_id[m.id] = m
        for f in _LIST_FACETS:
            for v in getattr(m, f):
                self._bucket(f, v).add(m.id)
        for f in _SCALAR_FACETS:
            v = getattr(m, f)
            if v:
                self._bucket(f, v).add(m.id)
        self._bucket("surface", m.placement.get("surface", "floor")).add(m.id)

    def remove(self, asset_id: str) -> None:
        m = self.by_id.pop(asset_id, None)
        if not m:
            return
        for facet, values in self.facets.items():
            for ids in values.values():
                ids.discard(asset_id)

    def candidates(self, facet: str, value: str) -> set[str]:
        return set(self.facets.get(facet, {}).get(str(value).lower(), set()))

    def union(self, pairs: list[tuple[str, str]]) -> set[str]:
        out: set[str] = set()
        for facet, value in pairs:
            out |= self.candidates(facet, value)
        return out

    def values(self, facet: str) -> list[str]:
        return sorted(self.facets.get(facet, {}))

    def __len__(self) -> int:
        return len(self.by_id)
