"""The :class:`Asset` value type and the registry of known asset types."""
from __future__ import annotations

from dataclasses import dataclass, field

from ..core.registry import Registry

# Known asset-type names. New layers/plugins register their type here, optionally
# with a validator(asset) -> None that raises on malformed data. Registration is
# advisory: the library will accept unknown types but warn-free, so third parties
# are never blocked, while first-party types get validated.
ASSET_TYPES: "Registry" = Registry("asset-type")


@dataclass
class Asset:
    """A single reusable, addressable unit in the library.

    Attributes
    ----------
    id    : globally unique, stable identifier (e.g. ``"pose.wave"``).
    type  : category (e.g. ``"pose"``, ``"expression"``, ``"character"``).
    name  : human label for browsing.
    tags  : free-form labels powering search/filtering.
    data  : the type-specific payload (a plain dict, JSON-serializable).
    pack  : id of the pack this asset came from (for provenance/versioning).
    """

    id: str
    type: str
    name: str = ""
    tags: list[str] = field(default_factory=list)
    data: dict = field(default_factory=dict)
    pack: str = ""

    def __post_init__(self) -> None:
        if not self.name:
            self.name = self.id
        # normalize tags to lowercase, de-duplicated, order-preserving
        seen: set[str] = set()
        norm: list[str] = []
        for tg in self.tags:
            tg = str(tg).strip().lower()
            if tg and tg not in seen:
                seen.add(tg)
                norm.append(tg)
        self.tags = norm

    def validate(self) -> None:
        """Run the registered validator for this asset's type, if any."""
        if self.type in ASSET_TYPES:
            validator = ASSET_TYPES.get(self.type)
            if callable(validator):
                validator(self)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "tags": list(self.tags),
            "data": self.data,
        }

    @classmethod
    def from_dict(cls, d: dict, pack: str = "") -> "Asset":
        return cls(
            id=d["id"],
            type=d["type"],
            name=d.get("name", ""),
            tags=list(d.get("tags", [])),
            data=dict(d.get("data", {})),
            pack=pack,
        )
