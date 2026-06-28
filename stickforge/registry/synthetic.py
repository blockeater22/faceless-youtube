"""Synthetic asset generation — for stress-testing the registry at scale.

Produces tens of thousands of plausible, schema-valid assets so query speed,
indexing, validation, and variant/constraint logic can be benchmarked against a
marketplace-sized catalogue without shipping real content.
"""
from __future__ import annotations

import random

from .schema import AssetMeta

_CATS = {
    "furniture": ("floor", ["sit", "lean", "place_object"]),
    "electronics": ("table", ["place_object"]),
    "decoration": ("any", []),
    "nature": ("floor", []),
    "architecture": ("wall", ["open", "close"]),
    "vehicle": ("floor", ["move"]),
    "food": ("table", ["pick_up"]),
}
_STYLES = ["modern", "minimal", "corporate", "cute", "classic", "luxury", "flat"]
_ENVS = ["office", "home", "outdoor", "school", "shop", "restaurant"]
_ROOMS = ["living_room", "bedroom", "kitchen", "conference_room", "workspace"]
_WORDS = ["wooden", "metal", "cozy", "sleek", "vintage", "compact", "tall",
          "round", "soft", "bright", "dark", "small", "large", "fancy"]


def generate(n: int, seed: int = 0) -> list[AssetMeta]:
    rng = random.Random(seed)
    out: list[AssetMeta] = []
    for i in range(n):
        cat = rng.choice(list(_CATS))
        surface, base_actions = _CATS[cat]
        styles = rng.sample(_STYLES, k=rng.randint(1, 2))
        tags = rng.sample(_WORDS, k=rng.randint(2, 4))
        out.append(AssetMeta(
            id=f"synth:{cat}.a{i}",
            category=cat,
            styles=styles,
            environments=rng.sample(_ENVS, k=rng.randint(1, 2)),
            room_types=rng.sample(_ROOMS, k=rng.randint(0, 2)),
            tags=tags,
            materials=rng.sample(["wood", "metal", "fabric", "glass"], k=1),
            supported_actions=base_actions,
            placement={"surface": surface},
            anchors={"center": [0, 0], "top": [0, -0.5]},
            bbox=[round(rng.uniform(0.5, 3), 2), round(rng.uniform(0.5, 3), 2)],
            quality_score=round(rng.uniform(4.0, 10.0), 1),
            variant_key=f"{cat}.group{i % max(1, n // 8)}",
            version="1.0.0",
        ))
    return out
