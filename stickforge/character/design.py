"""ActorDesign: a character assembled by *choosing part styles*, not by drawing.

A design is a selection — one style id per part category — plus a flat palette
and a body build. Because each field is an independent library choice, the
design space multiplies (see ``parts.combination_count``). This is the
Vyond/Toonly model: ship recombinable components, generate characters by
selection.

The default ``CLASSIC_PALETTE`` / ``classic_design`` match the StickForge style
guide: big white head with a bold outline, flat yellow tee with rounded
shoulders, black shorts, white limbs, simple hands, black shoes.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Style-guide palette (flat, high-contrast, monochrome-safe).
CLASSIC_PALETTE: dict[str, str] = {
    "outline": "#1b1b1b",     # bold dark line art
    "skin": "#ffffff",        # white head + limbs
    "shirt": "#f4c20d",       # signature yellow tee
    "pants": "#1b1b1b",       # black shorts
    "shoe": "#1b1b1b",        # black shoes
    "hair": "#1b1b1b",        # dark hair
    "eyewhite": "#ffffff",
    "iris": "#1b1b1b",
    "mouth": "#7a2e2e",
    "accent": "#e8492b",      # small accent (red)
}

# Alternate palettes so the lab can show variety while staying on-brand.
PALETTES: dict[str, dict[str, str]] = {
    "classic": CLASSIC_PALETTE,
    "blue": {**CLASSIC_PALETTE, "shirt": "#2f6fed", "accent": "#f4c20d"},
    "green": {**CLASSIC_PALETTE, "shirt": "#27a35a", "accent": "#ffffff"},
    "red": {**CLASSIC_PALETTE, "shirt": "#e8492b", "accent": "#1b1b1b"},
    "purple": {**CLASSIC_PALETTE, "shirt": "#8a5cf6", "accent": "#f4c20d"},
    "grey": {**CLASSIC_PALETTE, "shirt": "#8d99a6", "hair": "#9aa3ad",
             "accent": "#5b6470"},
    "pink": {**CLASSIC_PALETTE, "shirt": "#ff6fae", "hair": "#3a2a33",
             "accent": "#ffd34d"},
}

# Default part-style selection (the "house" actor).
_DEFAULTS = {
    "head": "round", "hair": "tuft", "eyes": "cartoon", "brows": "thick",
    "mouth": "default", "hands": "four_finger", "feet": "shoe",
    "body": "regular", "clothing": "none", "accessory": "none",
}


@dataclass
class ActorDesign:
    id: str = "actor"
    name: str = ""
    skeleton: str = "cartoon"
    archetype: str = ""               # personality (drives proportions/stance)
    line_width: float = 1.0
    head_scale: float = 1.0
    base_pose: str = "stand"
    base_expression: str = "happy"
    palette: dict = field(default_factory=lambda: dict(CLASSIC_PALETTE))
    parts: dict = field(default_factory=lambda: dict(_DEFAULTS))
    build: dict | None = None         # body thickness; from archetype if set
    hands: dict = field(default_factory=dict)

    def part(self, category: str) -> str:
        return self.parts.get(category, _DEFAULTS.get(category, ""))

    @classmethod
    def from_dict(cls, d: dict) -> "ActorDesign":
        # seed from an archetype (personality) if requested, then overlay d
        if d.get("archetype"):
            from .archetype import get_archetype
            seed = get_archetype(d["archetype"]).to_design_dict()
            merged = dict(seed)
            for k, v in d.items():
                if k in ("parts", "hands") and isinstance(v, dict):
                    merged[k] = {**seed.get(k, {}), **v}
                else:
                    merged[k] = v
            d = merged

        palette = dict(CLASSIC_PALETTE)
        if isinstance(d.get("palette"), str):
            palette = dict(PALETTES.get(d["palette"], CLASSIC_PALETTE))
        elif isinstance(d.get("palette"), dict):
            palette.update(d["palette"])
        parts = dict(_DEFAULTS)
        parts.update(d.get("parts", {}))
        return cls(
            id=d.get("id", "actor"),
            name=d.get("name", ""),
            skeleton=d.get("skeleton", "cartoon"),
            archetype=d.get("archetype", ""),
            line_width=float(d.get("line_width", 1.0)),
            head_scale=float(d.get("head_scale", 1.0)),
            base_pose=d.get("base_pose", "stand"),
            base_expression=d.get("base_expression", "happy"),
            palette=palette,
            parts=parts,
            build=dict(d["build"]) if isinstance(d.get("build"), dict) else None,
            hands=dict(d.get("hands", {})),
        )


def classic_design(id: str = "classic", palette: str = "classic", **overrides) -> ActorDesign:
    d = {"id": id, "palette": palette}
    d.update(overrides)
    return ActorDesign.from_dict(d)
