"""The Asset Intelligence Engine — StickForge's semantic asset knowledge base.

Principles (distilled from UE Asset Registry, Unity AssetDatabase, USD, DAM, ECS):

  * Identity, never location. Assets are addressed by stable namespaced IDs
    (``pack:category.name``), never file paths. Engines ask questions; the
    registry answers. No engine knows a filename.
  * Metadata-driven & fast at scale. A rich, validated, *additive* schema with
    inverted indices, so semantic queries over tens of thousands of assets are
    O(matches), not O(n) — and unknown future fields are preserved, not dropped.
  * Composition & relationships. Assets declare anchors, placement surfaces,
    interactions, variants, dependencies, and typed relationships; a constraint
    system rejects impossible compositions before they ever render.
  * Built for a marketplace. Versioned, backward-compatible, extensible — core
    team and third-party packs add content without touching engine code.

Public entry point: :class:`AssetRegistry`.
"""
from .schema import AssetMeta, SCHEMA_VERSION
from .taxonomy import CATEGORIES, VOCAB, register_category, register_vocab
from .validate import validate_meta, Issue
from .query import Query, parse_query
from .registry import AssetRegistry
from .relationships import Relationship
from .constraints import validate_composition, CONSTRAINTS, Placement


def default_registry() -> AssetRegistry:
    """An AssetRegistry pre-loaded with the shipped world packs."""
    from pathlib import Path
    reg = AssetRegistry()
    reg.load_dir(Path(__file__).parent / "data")
    return reg


__all__ = [
    "default_registry",
    "AssetMeta", "SCHEMA_VERSION", "AssetRegistry", "Query", "parse_query",
    "CATEGORIES", "VOCAB", "register_category", "register_vocab",
    "validate_meta", "Issue", "Relationship", "validate_composition",
    "CONSTRAINTS", "Placement",
]
