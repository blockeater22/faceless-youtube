"""Pose scoring — the silhouette / appeal test, done analytically.

A storyboard artist judges a pose by its silhouette: is the action readable as a
solid shape? We approximate that judgement from the solved joint geometry (no
rasterizer needed, so 100 poses score instantly), across the levers professional
gesture drawing cares about:

    line_of_action  a dominant flowing curve (not stiff/vertical)
    balance         centre of gravity supported over the feet
    silhouette      limbs read clear of the torso and each other (negative space)
    asymmetry       not a mirror-image "twin" stance
    extension       limbs committed/extended (appeal), not collapsed

``score_pose`` returns (total 0..10, breakdown).
"""
from __future__ import annotations

import math

from ..character.skeleton import cartoon_humanoid
from ..core.geometry import Vec2


def _band(x: float, lo: float, peak_lo: float, peak_hi: float, hi: float) -> float:
    """Trapezoid: 0 below lo, ramps to 1 over [lo,peak_lo], 1 across the plateau,
    ramps back to 0 over [peak_hi,hi]."""
    if x <= lo or x >= hi:
        return 0.0
    if x < peak_lo:
        return (x - lo) / (peak_lo - lo)
    if x <= peak_hi:
        return 1.0
    return (hi - x) / (hi - peak_hi)


def _dist_point_seg(p: Vec2, a: Vec2, b: Vec2) -> float:
    ab = b - a
    t = 0.0
    denom = ab.x * ab.x + ab.y * ab.y
    if denom > 1e-9:
        t = max(0.0, min(1.0, ((p.x - a.x) * ab.x + (p.y - a.y) * ab.y) / denom))
    proj = Vec2(a.x + ab.x * t, a.y + ab.y * t)
    return (p - proj).length()


def score_pose(pose: dict, skeleton=None) -> tuple[float, dict]:
    sk = skeleton or cartoon_humanoid()
    s = sk.solve(Vec2(0, 0), 1.0, pose)
    hip, sh = s["spine"].start, s["spine"].end
    head = sk.head(s).end
    hand_l, hand_r = s["forearm_l"].end, s["forearm_r"].end
    elbow_l, elbow_r = s["forearm_l"].start, s["forearm_r"].start
    foot_l, foot_r = s["shin_l"].end, s["shin_r"].end
    scale = max(1e-6, (head - foot_l).length())
    mir = lambda p: Vec2(-p.x, p.y)

    # 1) line of action — lean of the spine + a counter-curve at the head
    spine_lean = abs(math.degrees(math.atan2((sh - hip).x, -(sh - hip).y)))
    head_bend = abs(math.degrees(math.atan2((head - sh).x, -(head - sh).y)))
    loa = _band(spine_lean + head_bend, 3, 12, 30, 55)

    # 2) balance — centre of gravity over the support base
    cog_x = 0.3 * head.x + 0.3 * sh.x + 0.4 * hip.x
    fmin, fmax = min(foot_l.x, foot_r.x), max(foot_l.x, foot_r.x)
    base_w = (fmax - fmin) / scale
    margin = 0.06 * scale
    in_base = 1.0 if (fmin - margin) <= cog_x <= (fmax + margin) else \
        max(0.0, 1.0 - (min(abs(cog_x - fmin), abs(cog_x - fmax)) / (0.12 * scale)))
    balance = 0.6 * in_base + 0.4 * _band(base_w, 0.05, 0.16, 0.42, 0.8)

    # 3) silhouette — hands/feet clear of the torso and each other (negative space)
    h_clear = min(_dist_point_seg(hand_l, hip, sh),
                  _dist_point_seg(hand_r, hip, sh)) / scale
    hands_apart = (hand_l - hand_r).length() / scale
    feet_apart = abs(foot_l.x - foot_r.x) / scale
    silh = (0.45 * _band(h_clear, 0.04, 0.12, 0.6, 1.2)
            + 0.30 * _band(hands_apart, 0.1, 0.28, 1.2, 2.0)
            + 0.25 * _band(feet_apart, 0.05, 0.16, 0.7, 1.4))

    # 4) asymmetry — reward not being a mirror twin (but not chaos)
    asym = (((hand_l - mir(hand_r)).length()
             + (foot_l - mir(foot_r)).length()
             + (elbow_l - mir(elbow_r)).length()) / 3.0) / scale
    asymmetry = _band(asym, 0.015, 0.08, 0.45, 0.9)

    # 5) extension / appeal — limbs committed, not collapsed onto the body
    arm_ext = 0.5 * ((hand_l - sh).length() + (hand_r - sh).length()) / scale
    extension = _band(arm_ext, 0.18, 0.34, 0.62, 0.9)

    breakdown = {"line_of_action": loa, "balance": balance, "silhouette": silh,
                 "asymmetry": asymmetry, "extension": extension}
    total = 10.0 * (0.27 * loa + 0.20 * balance + 0.26 * silh
                    + 0.15 * asymmetry + 0.12 * extension)
    return round(total, 2), {k: round(v, 3) for k, v in breakdown.items()}
