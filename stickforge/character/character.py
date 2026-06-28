"""Character assembly: bind a skeleton to a data-driven look.

A :class:`Character` is produced from a :class:`CharacterSpec` (or a library
asset of type ``"character"``). The spec selects a skeleton, a palette, a head
size, and a list of *attachments* (hair, hats, accessories) that the renderer
draws relative to named bones. Nothing here is hardcoded into the renderer — a
new accessory is just another attachment dict.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .skeleton import Skeleton, default_humanoid

# Skeletons available by name. Plugins can register more.
from ..core.registry import Registry

SKELETONS: "Registry" = Registry("skeleton")
SKELETONS.register("humanoid", default_humanoid)


@dataclass
class CharacterSpec:
    id: str = "anon"
    name: str = ""
    skeleton: str = "humanoid"
    ink: str = "#f2ede1"
    accent: str = "#ffb454"
    line_width: float = 1.0          # multiplier on global ink width
    head_scale: float = 1.0          # multiply skeleton head radius
    base_pose: str = "stand"
    base_expression: str = "neutral"
    attachments: list[dict] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "CharacterSpec":
        return cls(
            id=d.get("id", "anon"),
            name=d.get("name", ""),
            skeleton=d.get("skeleton", "humanoid"),
            ink=d.get("ink", "#f2ede1"),
            accent=d.get("accent", "#ffb454"),
            line_width=float(d.get("line_width", 1.0)),
            head_scale=float(d.get("head_scale", 1.0)),
            base_pose=d.get("base_pose", "stand"),
            base_expression=d.get("base_expression", "neutral"),
            attachments=list(d.get("attachments", [])),
        )


@dataclass
class Character:
    spec: CharacterSpec
    skeleton: Skeleton

    @property
    def id(self) -> str:
        return self.spec.id

    @property
    def name(self) -> str:
        return self.spec.name or self.spec.id

    @property
    def head_radius(self) -> float:
        return self.skeleton.head_radius * self.spec.head_scale

    @property
    def attachments(self) -> list[dict]:
        return self.spec.attachments


def build_character(source, library=None) -> Character:
    """Build a Character from a CharacterSpec, a dict, or a library Asset.

    ``library`` is accepted for future asset cross-references (e.g. resolving a
    skeleton asset); the built-in skeletons come from the SKELETONS registry.
    """
    if isinstance(source, CharacterSpec):
        spec = source
    elif hasattr(source, "type") and getattr(source, "type", None) == "character":
        spec = CharacterSpec.from_dict({"id": source.id, "name": source.name,
                                        **source.data})
    elif isinstance(source, dict):
        spec = CharacterSpec.from_dict(source)
    else:
        raise TypeError(f"cannot build character from {type(source).__name__}")

    factory = SKELETONS.get(spec.skeleton)
    skeleton = factory()
    return Character(spec=spec, skeleton=skeleton)
