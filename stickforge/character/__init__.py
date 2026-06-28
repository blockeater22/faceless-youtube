"""Rigging + modular character assembly.

A :class:`Skeleton` is a hierarchy of :class:`Bone` s solved with forward
kinematics. A :class:`Character` binds a skeleton to a *spec* (palette, head
style, attachments such as hair/hats) assembled from library assets — so no
character is ever hardcoded into the renderer.
"""

from .skeleton import Bone, Skeleton, SolvedBone, default_humanoid
from .character import Character, CharacterSpec, build_character

__all__ = [
    "Bone",
    "Skeleton",
    "SolvedBone",
    "default_humanoid",
    "Character",
    "CharacterSpec",
    "build_character",
]
