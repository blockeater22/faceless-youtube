"""Animation clips: timelines of pose and expression keyframes.

A clip is fully data-driven and JSON-loadable (so it can ship in asset packs).
Sampling a clip at time ``t`` blends the bracketing pose keyframes and the
bracketing expression keyframes independently, then returns a :class:`Posing`
— a complete, render-ready description of the figure at that instant.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..core import easing
from ..core.geometry import Vec2
from ..core.keyframe import lerp
from ..pose.pose import get_pose, blend_pose
from ..expression.expression import get_expression, blend_expression, NEUTRAL


@dataclass
class Posing:
    """A render-ready snapshot of a figure at one instant."""

    pose: dict = field(default_factory=dict)
    expr: dict = field(default_factory=lambda: dict(NEUTRAL))
    offset: Vec2 = field(default_factory=lambda: Vec2(0.0, 0.0))
    scale: float = 1.0


def _bracket(keys: list[dict], t: float):
    """Return (k0, k1, eased_fraction) for the pair bracketing time ``t``."""
    ks = sorted(keys, key=lambda k: k["t"])
    if t <= ks[0]["t"]:
        return ks[0], ks[0], 0.0
    if t >= ks[-1]["t"]:
        return ks[-1], ks[-1], 0.0
    for i in range(len(ks) - 1):
        k0, k1 = ks[i], ks[i + 1]
        if k0["t"] <= t <= k1["t"]:
            span = (k1["t"] - k0["t"]) or 1e-9
            raw = (t - k0["t"]) / span
            return k0, k1, easing.get(k1.get("ease"))(raw)
    return ks[-1], ks[-1], 0.0


@dataclass
class AnimationClip:
    duration: float = 1.0
    loop: bool = False
    pose_keys: list[dict] = field(default_factory=list)
    expr_keys: list[dict] = field(default_factory=list)
    offset_keys: list[dict] = field(default_factory=list)
    name: str = "clip"

    @classmethod
    def from_spec(cls, spec: dict, name: str = "clip") -> "AnimationClip":
        """Build from a JSON-style spec.

        Pose keys take ``pose`` (name or inline dict); expression keys take
        ``expr``; offset keys take ``value`` ([x, y] in figure units).
        """
        return cls(
            duration=float(spec.get("duration", 1.0)),
            loop=bool(spec.get("loop", False)),
            pose_keys=[dict(k) for k in spec.get("poses", [])],
            expr_keys=[dict(k) for k in spec.get("expressions", [])],
            offset_keys=[dict(k) for k in spec.get("offset", [])],
            name=name,
        )

    def _local_time(self, t: float) -> float:
        if self.loop and self.duration > 0:
            return t % self.duration
        return min(max(t, 0.0), self.duration)

    def sample(self, t: float) -> Posing:
        t = self._local_time(t)
        out = Posing()

        if self.pose_keys:
            k0, k1, e = _bracket(self.pose_keys, t)
            out.pose = blend_pose(get_pose(k0["pose"]), get_pose(k1["pose"]), e)

        if self.expr_keys:
            k0, k1, e = _bracket(self.expr_keys, t)
            out.expr = blend_expression(
                get_expression(k0["expr"]), get_expression(k1["expr"]), e)

        if self.offset_keys:
            k0, k1, e = _bracket(self.offset_keys, t)
            v0, v1 = k0["value"], k1["value"]
            out.offset = Vec2(lerp(v0[0], v1[0], e), lerp(v0[1], v1[1], e))

        return out
