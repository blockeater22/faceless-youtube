"""The in-memory Asset Library: add, index, search, and resolve assets."""
from __future__ import annotations

from pathlib import Path

from .base import Asset
from .pack import AssetPack, load_pack


class AssetLibrary:
    """Holds assets and indexes them by id, type, and tag for fast search."""

    def __init__(self) -> None:
        self._by_id: dict[str, Asset] = {}
        self._by_type: dict[str, list[str]] = {}
        self._by_tag: dict[str, set[str]] = {}
        self.packs: dict[str, str] = {}      # pack id -> version

    # -- mutation --------------------------------------------------------- #
    def add(self, asset: Asset, *, overwrite: bool = False) -> Asset:
        if asset.id in self._by_id and not overwrite:
            raise ValueError(
                f"asset id {asset.id!r} already in library "
                f"(from pack {self._by_id[asset.id].pack!r})")
        self._by_id[asset.id] = asset
        self._by_type.setdefault(asset.type, [])
        if asset.id not in self._by_type[asset.type]:
            self._by_type[asset.type].append(asset.id)
        for tag in asset.tags:
            self._by_tag.setdefault(tag, set()).add(asset.id)
        return asset

    def add_pack(self, pack: AssetPack, *, overwrite: bool = False) -> "AssetLibrary":
        for a in pack.assets:
            self.add(a, overwrite=overwrite)
        self.packs[pack.id] = pack.version
        return self

    def load_pack_file(self, path: str | Path, *, overwrite: bool = False) -> "AssetLibrary":
        return self.add_pack(load_pack(path), overwrite=overwrite)

    def load_dir(self, directory: str | Path, *, overwrite: bool = False) -> "AssetLibrary":
        """Load every ``*.json`` pack in a directory (sorted for determinism)."""
        for p in sorted(Path(directory).glob("*.json")):
            self.load_pack_file(p, overwrite=overwrite)
        return self

    # -- lookup ----------------------------------------------------------- #
    def get(self, asset_id: str) -> Asset:
        try:
            return self._by_id[asset_id]
        except KeyError:
            raise KeyError(
                f"no asset {asset_id!r}; did you load its pack?") from None

    def __contains__(self, asset_id: object) -> bool:
        return asset_id in self._by_id

    def __len__(self) -> int:
        return len(self._by_id)

    def of_type(self, type_name: str) -> list[Asset]:
        return [self._by_id[i] for i in self._by_type.get(type_name, [])]

    def types(self) -> list[str]:
        return sorted(self._by_type)

    def tags(self) -> list[str]:
        return sorted(self._by_tag)

    # -- search ----------------------------------------------------------- #
    def search(self, query: str = "", *, type: str | None = None,
               tags: list[str] | None = None, limit: int | None = None
               ) -> list[Asset]:
        """Find assets by free text, type filter, and required tags.

        Ranking favours: exact id/name match > name substring > tag match >
        id substring. ``tags`` are *all* required (AND). Results are stable.
        """
        required = {t.strip().lower() for t in (tags or []) if t.strip()}
        q = query.strip().lower()

        candidates: list[Asset]
        if required:
            ids: set[str] | None = None
            for tag in required:
                matches = self._by_tag.get(tag, set())
                ids = matches if ids is None else (ids & matches)
            candidates = [self._by_id[i] for i in (ids or set())]
        else:
            candidates = list(self._by_id.values())

        if type is not None:
            candidates = [a for a in candidates if a.type == type]

        scored: list[tuple[int, str, Asset]] = []
        for a in candidates:
            if not q:
                scored.append((0, a.id, a))
                continue
            name_l, id_l = a.name.lower(), a.id.lower()
            if q == id_l or q == name_l:
                score = 4
            elif q in name_l:
                score = 3
            elif any(q in tg for tg in a.tags):
                score = 2
            elif q in id_l:
                score = 1
            else:
                continue
            scored.append((score, a.id, a))

        scored.sort(key=lambda s: (-s[0], s[1]))
        result = [a for _, _, a in scored]
        return result[:limit] if limit else result
