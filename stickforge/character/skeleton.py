"""Hierarchical skeleton + forward kinematics (the Rigging Engine).

Bones form a tree. Each bone has a *local* angle relative to its parent; world
angles accumulate down the chain, so leaning the spine carries the arms and
head with it (proper rigging, not independent absolute angles). A pose supplies
per-bone local-angle overrides; anything unspecified falls back to the bone's
rest angle.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..core.geometry import Vec2, polar

# Default segment lengths as fractions of the figure unit U.
HEAD_R = 0.130


@dataclass
class Bone:
    """One segment of the rig.

    parent : name of the parent bone, or None for a root.
    length : segment length as a fraction of the figure unit U.
    rest   : local angle (deg) relative to the parent, used when a pose omits it.
    attach : connect this bone to the parent's ``"tip"`` or ``"base"`` joint.
    kind   : ``"limb"`` (drawn as a stroke) or ``"head"`` (drawn as a circle).
    width  : stroke-weight multiplier relative to the global ink width.
    """

    name: str
    parent: str | None = None
    length: float = 0.2
    rest: float = 0.0
    attach: str = "tip"
    kind: str = "limb"
    width: float = 1.0


@dataclass
class SolvedBone:
    name: str
    start: Vec2
    end: Vec2
    world_angle: float
    bone: Bone


@dataclass
class Skeleton:
    bones: dict[str, Bone] = field(default_factory=dict)
    head_radius: float = HEAD_R       # fraction of U
    name: str = "skeleton"

    def add(self, bone: Bone) -> "Skeleton":
        self.bones[bone.name] = bone
        return self

    def _order(self) -> list[str]:
        """Topological order (parents before children)."""
        out: list[str] = []
        seen: set[str] = set()

        def visit(n: str) -> None:
            if n in seen:
                return
            b = self.bones[n]
            if b.parent and b.parent in self.bones:
                visit(b.parent)
            seen.add(n)
            out.append(n)

        for n in self.bones:
            visit(n)
        return out

    def solve(self, root: Vec2, unit: float,
              pose: dict[str, float] | None = None) -> dict[str, SolvedBone]:
        """Run forward kinematics. Returns name -> :class:`SolvedBone`.

        ``root`` is the anchor (the hip) in pixels; ``unit`` is U in pixels;
        ``pose`` maps bone name -> local angle override (degrees).
        """
        pose = pose or {}
        solved: dict[str, SolvedBone] = {}
        for name in self._order():
            b = self.bones[name]
            local = pose.get(name, b.rest)
            if b.parent and b.parent in solved:
                p = solved[b.parent]
                world = p.world_angle + local
                start = p.end if b.attach == "tip" else p.start
            else:
                world = local
                start = root
            end = polar(start, b.length * unit, world)
            solved[name] = SolvedBone(name, start, end, world, b)
        return solved

    def head(self, solved: dict[str, SolvedBone]) -> SolvedBone | None:
        for sb in solved.values():
            if sb.bone.kind == "head":
                return sb
        return None


def default_humanoid() -> Skeleton:
    """The built-in two-segment-limb stickman rig.

    Angles are tuned so the rest pose reads as a relaxed stand. Arms attach at
    the spine tip (shoulders); legs attach at the spine base (hip).
    """
    s = Skeleton(name="humanoid")
    s.add(Bone("spine", parent=None, length=0.34, rest=0.0, kind="limb", width=1.15))
    s.add(Bone("head", parent="spine", length=0.16, rest=0.0, attach="tip", kind="head"))
    # arms (figure-left points to image-left ~ angle >180)
    s.add(Bone("upper_arm_l", parent="spine", length=0.19, rest=196.0, attach="tip"))
    s.add(Bone("forearm_l",   parent="upper_arm_l", length=0.17, rest=6.0, attach="tip"))
    s.add(Bone("upper_arm_r", parent="spine", length=0.19, rest=164.0, attach="tip"))
    s.add(Bone("forearm_r",   parent="upper_arm_r", length=0.17, rest=-6.0, attach="tip"))
    # legs
    s.add(Bone("thigh_l", parent="spine", length=0.21, rest=187.0, attach="base"))
    s.add(Bone("shin_l",  parent="thigh_l", length=0.21, rest=-4.0, attach="tip"))
    s.add(Bone("thigh_r", parent="spine", length=0.21, rest=173.0, attach="base"))
    s.add(Bone("shin_r",  parent="thigh_r", length=0.21, rest=4.0, attach="tip"))
    return s
