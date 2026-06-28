"""The Character Design System: a modular library of illustrated part styles.

A character is *assembled* from interchangeable parts — head, hair, eyes,
brows, mouth, hands, feet, body build, clothing, accessories. Each part
*category* is a :class:`~stickforge.core.registry.Registry` of **styles**, and a
style is an *art provider*: a callable ``draw(canvas, frame)`` that renders that
part. Today the providers draw vector art procedurally; the same interface
accepts imported SVG art later, so the renderer can be swapped without touching
the assembly model.

This is the architecture that scales the way Vyond/Toonly do: ship a rich,
recombinable component library, not finished illustrations. Adding the 50th head
or 120th eye style is just another ``register`` call — no engine change.
"""
from __future__ import annotations

from ..core.registry import Registry
from .frame import PartFrame

# One registry per part category. Plugins/packs add styles here.
HEADS: "Registry" = Registry("head-style")
HAIRS: "Registry" = Registry("hair-style")
EYES: "Registry" = Registry("eye-style")
BROWS: "Registry" = Registry("brow-style")
MOUTHS: "Registry" = Registry("mouth-style")
HANDS: "Registry" = Registry("hand-style")
FEET: "Registry" = Registry("foot-style")
BODIES: "Registry" = Registry("body-style")
CLOTHES: "Registry" = Registry("clothing-style")
ACCESSORIES: "Registry" = Registry("accessory-style")

CATEGORIES: dict[str, Registry] = {
    "head": HEADS, "hair": HAIRS, "eyes": EYES, "brows": BROWS,
    "mouth": MOUTHS, "hands": HANDS, "feet": FEET, "body": BODIES,
    "clothing": CLOTHES, "accessory": ACCESSORIES,
}


def catalog() -> dict[str, list[str]]:
    """All registered styles per category — the size of the design space."""
    return {name: reg.names() for name, reg in CATEGORIES.items()}


def combination_count() -> int:
    """How many distinct characters the current library can assemble."""
    total = 1
    for reg in CATEGORIES.values():
        total *= max(1, len(reg))
    return total


# Importing the builtins registers the seed library as a side effect.
from . import builtins as _builtins  # noqa: E402,F401

__all__ = [
    "PartFrame", "CATEGORIES", "catalog", "combination_count",
    "HEADS", "HAIRS", "EYES", "BROWS", "MOUTHS", "HANDS", "FEET",
    "BODIES", "CLOTHES", "ACCESSORIES",
]
