"""Category taxonomy + controlled vocabularies (open & extensible).

The taxonomy is a tree (category -> parent). Vocabularies (styles, surfaces,
environments, actions, …) are *open*: validation warns about unknown values but
never rejects them, so marketplace packs can introduce new styles/environments
without an engine release. New categories/vocab are registered, not hardcoded.
"""
from __future__ import annotations

# category -> parent (None = root). Extend via register_category().
CATEGORIES: dict[str, str | None] = {}


def register_category(name: str, parent: str | None = None) -> None:
    CATEGORIES[name] = parent


def category_ancestors(name: str) -> list[str]:
    out, cur = [], CATEGORIES.get(name)
    seen = set()
    while cur and cur not in seen:
        seen.add(cur)
        out.append(cur)
        cur = CATEGORIES.get(cur)
    return out


def is_category(name: str) -> bool:
    return name in CATEGORIES


# Controlled, extensible vocabularies.
VOCAB: dict[str, set[str]] = {
    "styles": set(), "surfaces": set(), "environments": set(),
    "room_types": set(), "actions": set(), "materials": set(),
    "lighting": set(), "weather": set(), "time": set(), "themes": set(),
}


def register_vocab(facet: str, *values: str) -> None:
    VOCAB.setdefault(facet, set()).update(v.strip().lower() for v in values)


def in_vocab(facet: str, value: str) -> bool:
    return value.strip().lower() in VOCAB.get(facet, set())


# --------------------------------------------------------------------------- #
# Seed taxonomy + vocab (the founding set; packs extend it).
# --------------------------------------------------------------------------- #
def _seed() -> None:
    roots = ["character", "prop", "environment", "effect", "audio", "ui",
             "animation", "camera", "lighting", "template"]
    for r in roots:
        register_category(r, None)
    children = {
        "prop": ["furniture", "electronics", "food", "clothing",
                 "vehicle", "decoration", "background_element"],
        "environment": ["building", "architecture", "nature", "weather",
                        "room"],
        "character": ["character_accessory"],
        "effect": ["particle", "transition"],
        "ui": ["icon"],
    }
    for parent, kids in children.items():
        for k in kids:
            register_category(k, parent)

    register_vocab("styles", "flat", "cartoon", "modern", "minimal",
                   "corporate", "fantasy", "sci-fi", "cute", "hand-drawn",
                   "comic", "educational", "whiteboard", "classic", "luxury")
    register_vocab("surfaces", "floor", "wall", "ceiling", "table", "any",
                   "character", "shelf")
    register_vocab("environments", "office", "home", "outdoor", "school",
                   "street", "park", "restaurant", "shop", "studio")
    register_vocab("room_types", "living_room", "bedroom", "kitchen",
                   "conference_room", "reception", "workspace", "bathroom",
                   "classroom", "cubicle")
    register_vocab("actions", "sit", "stand", "open", "close", "knock", "lock",
                   "place_object", "lean", "write", "walk", "run", "point",
                   "wave", "pick_up", "put_down", "hold", "hug", "gesture",
                   "rotate", "move")
    register_vocab("materials", "wood", "metal", "fabric", "glass", "plastic",
                   "leather", "stone", "paper")
    register_vocab("lighting", "day", "night", "warm", "cool", "neon", "dim")
    register_vocab("weather", "clear", "rain", "snow", "fog", "storm")
    register_vocab("time", "morning", "noon", "evening", "night")
    register_vocab("themes", "cozy", "corporate", "luxury", "rustic", "techy",
                   "playful", "gloomy", "cheerful")


_seed()
