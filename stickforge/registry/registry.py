"""AssetRegistry — the public service. The single source of truth for assets.

Engines never touch files or names; they call these methods with semantic
queries and structured questions. Backed by inverted indices (fast), a
relationship graph (meaningful), and validation/constraints (safe).
"""
from __future__ import annotations

import json
from pathlib import Path

from .index import AssetIndex
from .query import Query, parse_query, score
from .relationships import RelationshipGraph, SUPPORTS, BELONGS_TO
from .schema import AssetMeta
from .validate import validate_meta, errors


class AssetRegistry:
    def __init__(self) -> None:
        self.index = AssetIndex()
        self.rel = RelationshipGraph()
        self.packs: dict[str, str] = {}

    # -- ingestion -------------------------------------------------------- #
    def add(self, meta: AssetMeta, *, overwrite: bool = False,
            strict: bool = True) -> AssetMeta:
        if strict:
            errs = errors(validate_meta(meta))
            if errs:
                raise ValueError(f"invalid asset {meta.id}: {errs[0]}")
        if meta.id in self.index.by_id and not overwrite:
            raise ValueError(f"duplicate asset id {meta.id!r}")
        if overwrite and meta.id in self.index.by_id:
            self.index.remove(meta.id)
        self.index.add(meta)
        self.rel.add_asset(meta)
        return meta

    def add_pack(self, pack: dict, *, strict: bool = True,
                 overwrite: bool = False) -> "AssetRegistry":
        pid = pack.get("id", "")
        for a in pack.get("assets", []):
            self.add(AssetMeta.from_dict(a, pack=pid), strict=strict,
                     overwrite=overwrite)
        self.packs[pid] = pack.get("version", "0.0.0")
        return self

    def load_pack_file(self, path, **kw) -> "AssetRegistry":
        return self.add_pack(json.loads(Path(path).read_text(encoding="utf-8")), **kw)

    def load_dir(self, directory, **kw) -> "AssetRegistry":
        for p in sorted(Path(directory).glob("*.json")):
            self.load_pack_file(p, **kw)
        return self

    # -- access ----------------------------------------------------------- #
    def get(self, asset_id: str) -> AssetMeta:
        return self.index.by_id[asset_id]

    def __contains__(self, asset_id: object) -> bool:
        return asset_id in self.index.by_id

    def __len__(self) -> int:
        return len(self.index)

    def all(self) -> list[AssetMeta]:
        return list(self.index.by_id.values())

    # -- semantic discovery ---------------------------------------------- #
    def find_assets(self, query: "str | Query", limit: int = 20) -> list[AssetMeta]:
        q = parse_query(query) if isinstance(query, str) else query
        pairs: list[tuple[str, str]] = []
        if q.category:
            pairs += [("category", q.category), ("subcategory", q.category)]
        for f, vals in (("styles", q.styles), ("environments", q.environments),
                        ("room_types", q.room_types),
                        ("supported_actions", q.actions),
                        ("themes", q.themes), ("materials", q.materials),
                        ("tags", q.tags)):
            pairs += [(f, v) for v in vals]
        if q.surface:
            pairs.append(("surface", q.surface))

        ids = self.index.union(pairs) if pairs else set(self.index.by_id)
        scored = [(score(self.index.by_id[i], q), self.index.by_id[i]) for i in ids]
        scored = [(s, m) for s, m in scored if s > 0 or not pairs]
        scored.sort(key=lambda sm: (-sm[0], sm[1].id))
        return [m for _, m in scored[:limit]]

    def _by_facet(self, facet: str, value: str) -> list[AssetMeta]:
        metas = [self.index.by_id[i] for i in self.index.candidates(facet, value)]
        return sorted(metas, key=lambda m: -m.quality_score)

    def find_by_tag(self, tag: str) -> list[AssetMeta]:
        return self._by_facet("tags", tag)

    def find_by_style(self, style: str) -> list[AssetMeta]:
        return self._by_facet("styles", style)

    def find_by_environment(self, env: str) -> list[AssetMeta]:
        return self._by_facet("environments", env)

    def find_by_action(self, action: str) -> list[AssetMeta]:
        return self._by_facet("supported_actions", action)

    def find_by_category(self, category: str) -> list[AssetMeta]:
        return self._by_facet("category", category)

    # -- variants --------------------------------------------------------- #
    def find_variants(self, asset_id_or_key: str) -> list[AssetMeta]:
        key = asset_id_or_key
        if asset_id_or_key in self:
            key = self.get(asset_id_or_key).variant_key or asset_id_or_key
        return sorted([self.index.by_id[i] for i in self.index.candidates("variant_key", key)],
                      key=lambda m: -m.quality_score)

    def choose_variant(self, key: str, query: "str | Query") -> AssetMeta | None:
        q = parse_query(query) if isinstance(query, str) else query
        variants = self.find_variants(key)
        if not variants:
            return None
        return max(variants, key=lambda m: score(m, q))

    # -- relationships ---------------------------------------------------- #
    def supports(self, asset_id: str) -> set[str]:
        """Targets (categories/ids) this asset can host (e.g. desk -> laptop)."""
        return self.rel.out(asset_id, SUPPORTS)

    def hosts_for(self, target: str) -> set[str]:
        """Assets that can host ``target`` (inverse of supports)."""
        return self.rel.incoming(target, SUPPORTS)

    def belongs_to(self, asset_id: str) -> set[str]:
        return self.rel.out(asset_id, BELONGS_TO)

    def dependencies(self, asset_id: str) -> set[str]:
        from .relationships import DEPENDS_ON
        return self.rel.out(asset_id, DEPENDS_ON)

    # -- anchors ---------------------------------------------------------- #
    def anchor(self, asset_id: str, name: str) -> list | None:
        m = self.get(asset_id) if asset_id in self else None
        return m.anchors.get(name) if m else None

    def interaction(self, asset_id: str, name: str) -> list | None:
        m = self.get(asset_id) if asset_id in self else None
        return m.interaction_points.get(name) if m else None

    # -- recommendations -------------------------------------------------- #
    def recommend(self, environment: str = "", room_type: str = "",
                  limit: int = 12) -> list[AssetMeta]:
        q = Query(environments=[environment] if environment else [],
                  room_types=[room_type] if room_type else [])
        return self.find_assets(q, limit=limit)

    def suggest_replacements(self, asset_id: str, limit: int = 6) -> list[AssetMeta]:
        if asset_id not in self:
            return []
        base = self.get(asset_id)
        cands = [m for m in self._by_facet("category", base.category)
                 if m.id != asset_id and not m.deprecated]
        cands.sort(key=lambda m: (-len(set(m.styles) & set(base.styles)),
                                  -m.quality_score))
        return cands[:limit]

    # -- safety ----------------------------------------------------------- #
    def validate(self, meta: AssetMeta):
        return validate_meta(meta)

    def validate_scene(self, placements, environment: str = ""):
        from .constraints import validate_composition
        return validate_composition(placements, self, environment)
