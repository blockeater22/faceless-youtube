"""The canonical asset metadata schema.

This is the contract every asset — first-party or marketplace — speaks. It is
deliberately *additive*: unknown fields are preserved in ``extra`` so newer
packs round-trip through older code (USD-style forward compatibility), and
``schema_version`` lets us migrate old packs forward without breaking them.

Spatial conventions: ``bbox`` is ``[width, height]`` in world units; ``anchors``
and ``interaction_points`` are normalized to the bbox and centered at the asset
origin (``[0,0]`` = center, ``[0,-0.5]`` = top, ``[0.5,0]`` = right edge). The
World Engine resolves them to world space via the asset's placement transform.
"""
from __future__ import annotations

from dataclasses import dataclass, field

SCHEMA_VERSION = 1

# fields the schema owns; anything else in a dict is round-tripped via `extra`.
_KNOWN = {
    "id", "name", "category", "subcategory", "tags", "styles", "themes",
    "environments", "room_types", "materials", "color_palette", "animations",
    "anchors", "bbox", "collision", "layer", "scale_limits", "rotation",
    "lighting_compat", "weather_compat", "time_compat", "interaction_points",
    "supported_actions", "variant_key", "variant_of", "variants",
    "dependencies", "supports", "belongs_to", "placement", "lod_levels",
    "version", "author", "license", "deprecated", "quality_score",
    "performance", "schema_version",
}


@dataclass
class AssetMeta:
    # -- identity ---------------------------------------------------------- #
    id: str
    name: str = ""
    category: str = "prop"
    subcategory: str = ""
    # -- discovery facets -------------------------------------------------- #
    tags: list[str] = field(default_factory=list)
    styles: list[str] = field(default_factory=list)
    themes: list[str] = field(default_factory=list)
    environments: list[str] = field(default_factory=list)
    room_types: list[str] = field(default_factory=list)
    materials: list[str] = field(default_factory=list)
    color_palette: list[str] = field(default_factory=list)
    animations: list[str] = field(default_factory=list)
    # -- spatial / rendering ---------------------------------------------- #
    anchors: dict = field(default_factory=dict)            # name -> [x, y]
    bbox: list = field(default_factory=lambda: [1.0, 1.0])  # [w, h] world units
    collision: str = "box"                                 # box | ellipse | none
    layer: str = "midground"
    scale_limits: list = field(default_factory=lambda: [0.5, 2.0])
    rotation: dict = field(default_factory=lambda: {"allowed": True, "snap": 0})
    # -- compatibility ----------------------------------------------------- #
    lighting_compat: list[str] = field(default_factory=list)
    weather_compat: list[str] = field(default_factory=list)
    time_compat: list[str] = field(default_factory=list)
    # -- interaction ------------------------------------------------------- #
    interaction_points: dict = field(default_factory=dict)  # name -> [x, y]
    supported_actions: list[str] = field(default_factory=list)
    # -- composition / relationships -------------------------------------- #
    variant_key: str = ""        # group key shared by all variants of a thing
    variant_of: str = ""         # base asset id ("" if this is a base)
    variants: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    supports: list[str] = field(default_factory=list)       # categories/ids it hosts
    belongs_to: list[str] = field(default_factory=list)     # environments/rooms
    placement: dict = field(default_factory=lambda: {"surface": "floor"})
    # -- production -------------------------------------------------------- #
    lod_levels: int = 1
    version: str = "1.0.0"
    author: str = ""
    license: str = "proprietary"
    deprecated: bool = False
    quality_score: float = 7.0                              # 0..10
    performance: dict = field(default_factory=lambda: {"memory": 1.0, "render": 1.0})
    # -- bookkeeping ------------------------------------------------------- #
    pack: str = ""
    schema_version: int = SCHEMA_VERSION
    extra: dict = field(default_factory=dict)              # forward-compat overflow

    def __post_init__(self) -> None:
        if not self.name:
            self.name = self.id.split(".")[-1].replace("_", " ").title()
        self.tags = _norm_list(self.tags)
        self.styles = _norm_list(self.styles)
        self.environments = _norm_list(self.environments)
        self.supported_actions = _norm_list(self.supported_actions)

    # -- (de)serialization ------------------------------------------------- #
    @classmethod
    def from_dict(cls, d: dict, pack: str = "") -> "AssetMeta":
        d = migrate(dict(d))
        known = {k: v for k, v in d.items() if k in _KNOWN}
        extra = {k: v for k, v in d.items() if k not in _KNOWN}
        known.setdefault("id", d.get("id"))
        m = cls(**{k: v for k, v in known.items() if k != "schema_version"})
        m.schema_version = d.get("schema_version", SCHEMA_VERSION)
        m.extra = {**extra, **d.get("extra", {})}
        m.pack = pack or d.get("pack", "")
        return m

    def to_dict(self) -> dict:
        out = {k: getattr(self, k) for k in _KNOWN if hasattr(self, k)}
        out.update(self.extra)
        return out


def _norm_list(xs) -> list[str]:
    seen, out = set(), []
    for x in xs or []:
        x = str(x).strip().lower()
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


def migrate(d: dict) -> dict:
    """Upgrade an asset dict from an older ``schema_version`` to the current one.

    Additive by design — add version blocks here as the schema evolves; older
    packs keep loading. (No migrations needed yet at v1.)
    """
    v = d.get("schema_version", 1)
    # if v < 2: ...  # future migrations go here
    return d
