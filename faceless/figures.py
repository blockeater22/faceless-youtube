"""Stick-figure poses and rendering.

A figure is a 2-segment-limb skeleton anchored at the hip. Angles are degrees
measured from straight *down* (0 = down, +90 = image-right, 180 = up), so poses
read naturally and blend with :func:`anim.blend_pose`.
"""
from __future__ import annotations

import math

from .draw import Point, Sketcher

# segment lengths as a fraction of the figure unit U (U = scale * min(W, H))
HEAD_R = 0.130
HEAD_GAP = 0.030
TORSO = 0.340
UPPER_ARM = 0.190
FOREARM = 0.170
THIGH = 0.210
SHIN = 0.210

# Each pose: lean (torso tilt), head (extra tilt), and [upper, fore/shin] angles
# for the two arms (la/ra) and two legs (ll/rl).
POSES: dict[str, dict] = {
    "stand":     {"lean": 0,  "head": 0,   "la": [18, 16],   "ra": [-18, -16],  "ll": [10, 8],   "rl": [-10, -8]},
    "idle":      {"lean": 1,  "head": 2,   "la": [22, 26],   "ra": [-16, -12],  "ll": [9, 7],    "rl": [-11, -9]},
    "think":     {"lean": -4, "head": -3,  "la": [158, 206], "ra": [-26, -44],  "ll": [9, 7],    "rl": [-12, -10]},
    "look_up":   {"lean": -6, "head": -24, "la": [16, 14],   "ra": [-16, -14],  "ll": [10, 8],   "rl": [-10, -8]},
    "arms_up":   {"lean": -3, "head": -10, "la": [150, 158], "ra": [-150, -158],"ll": [12, 9],   "rl": [-12, -9]},
    "celebrate": {"lean": -4, "head": -12, "la": [156, 168], "ra": [-156, -168],"ll": [16, 22],  "rl": [-16, -22]},
    "point_up":  {"lean": -2, "head": -12, "la": [176, 179], "ra": [-18, -16],  "ll": [10, 8],   "rl": [-10, -8]},
    "point_r":   {"lean": 4,  "head": 6,   "la": [88, 90],   "ra": [-16, -14],  "ll": [12, 10],  "rl": [-8, -6]},
    "point_l":   {"lean": -4, "head": -6,  "la": [16, 14],   "ra": [-88, -90],  "ll": [8, 6],    "rl": [-12, -10]},
    "reach":     {"lean": 6,  "head": -4,  "la": [118, 138], "ra": [-20, -16],  "ll": [14, 11],  "rl": [-12, -9]},
    "wave":      {"lean": -2, "head": -2,  "la": [142, 168], "ra": [-18, -16],  "ll": [10, 8],   "rl": [-10, -8]},
    "shrug":     {"lean": 0,  "head": 0,   "la": [54, 96],   "ra": [-54, -96],  "ll": [10, 8],   "rl": [-10, -8]},
    "sit":       {"lean": -6, "head": 0,   "la": [40, 78],   "ra": [-40, -78],  "ll": [70, 6],   "rl": [-70, -6]},
    "walk_a":    {"lean": 7,  "head": 2,   "la": [-22, -28], "ra": [24, 32],    "ll": [28, 36],  "rl": [-26, -32]},
    "walk_b":    {"lean": 7,  "head": 2,   "la": [24, 32],   "ra": [-22, -28],  "ll": [-26, -32],"rl": [28, 36]},
}


def get_pose(name) -> dict:
    """Resolve a pose name (or pass through an inline pose dict)."""
    if isinstance(name, dict):
        return name
    return POSES.get(name, POSES["stand"])


def _polar(origin: Point, length: float, angle_deg: float) -> Point:
    a = math.radians(angle_deg)
    return (origin[0] + length * math.sin(a), origin[1] + length * math.cos(a))


def draw_figure(sk: Sketcher, hip: Point, unit: float, pose: dict,
                color=None, face: str = "dots", lw: float | None = None,
                t: float = 0.0, phase: float = 0.0, life: float = 0.0,
                draw: float = 1.0) -> None:
    """Draw a stick figure. ``hip`` is the pixel anchor, ``unit`` the pixel U.

    ``life`` (>0) adds continuous breathing / sway / blink so the figure is
    never frozen. ``draw`` (<1) sketches strokes on by arc length for a
    hand-drawn 'being drawn' reveal; the face lands once the body is mostly in.
    """
    lean = pose.get("lean", 0)
    head = pose.get("head", 0)
    la, ra = list(pose.get("la", [18, 16])), list(pose.get("ra", [-18, -16]))
    ll, rl = pose.get("ll", [10, 8]), pose.get("rl", [-10, -8])

    blink = False
    if life > 0:
        from .motion import breath, is_blink, sway
        b, s = breath(t, phase), sway(t, phase)
        hip = (hip[0] + s * 0.010 * unit * life, hip[1] + b * 0.006 * unit * life)
        lean += s * 1.6 * life
        head += b * 1.3 * life
        la[0] += b * 1.8 * life
        ra[0] -= b * 1.8 * life
        blink = is_blink(t, phase)

    torso_ang = 180 - lean
    shoulder = _polar(hip, TORSO * unit, torso_ang)
    head_c = _polar(shoulder, (HEAD_R + HEAD_GAP) * unit, 180 - lean - head)
    hr = HEAD_R * unit

    # legs first (behind), then torso, arms, head on top
    for ang in (ll, rl):
        knee = _polar(hip, THIGH * unit, ang[0])
        foot = _polar(knee, SHIN * unit, ang[1])
        sk.stroke([hip, knee, foot], color=color, width=lw, draw=draw)

    sk.stroke([hip, shoulder], color=color, width=lw, draw=draw)

    for ang in (la, ra):
        elbow = _polar(shoulder, UPPER_ARM * unit, ang[0])
        hand = _polar(elbow, FOREARM * unit, ang[1])
        sk.stroke([shoulder, elbow, hand], color=color, width=lw, draw=draw)

    sk.circle(head_c, hr, color=color, width=lw, amp=sk.wobble * 0.5, draw=draw)
    if draw >= 0.82:
        _draw_face(sk, head_c, hr, face, color, blink=blink)


def _draw_face(sk: Sketcher, c: Point, r: float, face: str, color, blink: bool = False) -> None:
    if face in (None, "none"):
        return
    ex, ey = 0.36 * r, 0.12 * r
    eye_r = max(1.0, 0.10 * r)
    if not (blink or face == "shut"):
        sk.dot((c[0] - ex, c[1] - ey), eye_r, color=color)
        sk.dot((c[0] + ex, c[1] - ey), eye_r, color=color)
    else:  # closed/peaceful eyes (or mid-blink)
        sk.line((c[0] - ex * 1.4, c[1] - ey), (c[0] - ex * 0.3, c[1] - ey), color=color, width=sk.width * 0.7)
        sk.line((c[0] + ex * 0.3, c[1] - ey), (c[0] + ex * 1.4, c[1] - ey), color=color, width=sk.width * 0.7)

    my = 0.42 * r
    mw = 0.40 * r
    if face == "happy":
        sk.arc((c[0], c[1] + my * 0.4), mw, 25, 155, color=color, width=sk.width * 0.8)
    elif face == "sad":
        sk.arc((c[0], c[1] + my * 1.3), mw, 205, 335, color=color, width=sk.width * 0.8)
    elif face == "surprised":
        sk.circle((c[0], c[1] + my), mw * 0.45, color=color, width=sk.width * 0.7)
    elif face in ("neutral", "dots", "shut"):
        sk.line((c[0] - mw * 0.5, c[1] + my), (c[0] + mw * 0.5, c[1] + my), color=color, width=sk.width * 0.7)
