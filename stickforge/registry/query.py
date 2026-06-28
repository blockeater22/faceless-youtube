"""Semantic query — engines ask in words, the registry ranks the best matches.

A :class:`Query` is a set of facet preferences. ``parse_query`` turns a natural
phrase ("a cozy wooden sofa for a middle-class living room") into one by mapping
tokens against the controlled vocabularies + taxonomy; leftover content words
become tag hints. Scoring rewards facet matches, tag overlap, and quality, and
penalizes deprecation — so the *best* asset surfaces, not just *a* match.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .schema import AssetMeta
from .taxonomy import VOCAB, CATEGORIES

_STOP = {"a", "an", "the", "for", "of", "with", "in", "on", "to", "and",
         "find", "get", "some", "me", "that", "is", "suitable", "middle",
         "class", "nice"}

# normalize common adjective/spelling variants to canonical vocabulary terms
_SYNONYMS = {
    "wooden": "wood", "metallic": "metal", "glassy": "glass",
    "comfy": "cozy", "cosy": "cozy", "rainy": "rain", "snowy": "snow",
    "foggy": "fog", "stormy": "storm", "scifi": "sci-fi",
}

# a few friendly synonyms -> category
_CATEGORY_HINTS = {
    "sofa": "furniture", "couch": "furniture", "chair": "furniture",
    "desk": "furniture", "table": "furniture", "bed": "furniture",
    "lamp": "furniture", "shelf": "furniture", "laptop": "electronics",
    "computer": "electronics", "phone": "electronics", "tv": "electronics",
    "window": "architecture", "door": "architecture", "wall": "architecture",
    "plant": "decoration", "painting": "decoration", "rug": "decoration",
    "tree": "nature", "car": "vehicle",
}


@dataclass
class Query:
    text: str = ""
    category: str = ""
    styles: list[str] = field(default_factory=list)
    environments: list[str] = field(default_factory=list)
    room_types: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    themes: list[str] = field(default_factory=list)
    materials: list[str] = field(default_factory=list)
    surface: str = ""
    tags: list[str] = field(default_factory=list)


def parse_query(text: str) -> Query:
    q = Query(text=text)
    tokens = [(_SYNONYMS.get(w, w))
              for w in re.findall(r"[a-zA-Z][a-zA-Z'-]*", text.lower())]
    # bi-grams help catch "living room", "sci fi"
    grams = tokens + [f"{a} {b}" for a, b in zip(tokens, tokens[1:])] + \
        [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
    used: set[str] = set()
    for g in grams:
        if g in VOCAB["styles"]:
            q.styles.append(g); used.update(g.split())
        elif g in VOCAB["environments"]:
            q.environments.append(g); used.update(g.split())
        elif g in VOCAB["room_types"]:
            q.room_types.append(g); used.update(g.split("_") + g.split())
        elif g in VOCAB["actions"]:
            q.actions.append(g); used.update(g.split())
        elif g in VOCAB["themes"]:
            q.themes.append(g); used.update(g.split())
        elif g in VOCAB["materials"]:
            q.materials.append(g); used.update(g.split())
        elif g in VOCAB["surfaces"] and not q.surface:
            q.surface = g; used.add(g)
        elif g in CATEGORIES and not q.category:
            q.category = g; used.add(g)
        elif g in _CATEGORY_HINTS:
            if not q.category:
                q.category = _CATEGORY_HINTS[g]
            q.tags.append(g); used.add(g)
    for t in tokens:
        if t not in used and t not in _STOP and len(t) > 2:
            q.tags.append(t)
    return q


def score(m: AssetMeta, q: Query) -> float:
    if m.deprecated:
        return -1.0
    s = 0.0
    if q.category and (m.category == q.category or m.subcategory == q.category):
        s += 4.0
    s += 3.0 * len(set(q.styles) & set(m.styles))
    s += 3.0 * len(set(q.environments) & set(m.environments))
    s += 2.0 * len(set(q.room_types) & set(m.room_types))
    s += 2.0 * len(set(q.actions) & set(m.supported_actions))
    s += 1.5 * len(set(q.themes) & set(m.themes))
    s += 1.0 * len(set(q.materials) & set(m.materials))
    if q.surface and m.placement.get("surface") == q.surface:
        s += 2.0
    s += 1.0 * len(set(q.tags) & set(m.tags))
    # a tag that matches the name is a strong signal
    s += 1.5 * sum(1 for t in q.tags if t in m.name.lower())
    s += 0.2 * m.quality_score
    return s
