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


def _part_reveal(g: float, idx: int, n: int) -> float:
    """Map a single 0..1 draw-on progress ``g`` to the reveal of part ``idx``
    of ``n``, so parts draw on one after another in order."""
    if g >= 1.0:
        return 1.0
    x = g * n - idx
    return 0.0 if x <= 0 else (1.0 if x >= 1 else x)


def draw_figure(sk: Sketcher, hip: Point, unit: float, pose: dict,
                color=None, face: str = "dots", lw: float | None = None,
                blink: bool = False, reveal: float = 1.0) -> tuple[Point, float]:
    """Draw a stick figure. ``hip`` is the pixel anchor, ``unit`` the pixel U.

    ``blink`` momentarily closes the eyes (driven by wall-clock time in the
    renderer) so the character feels alive instead of frozen.

    ``reveal`` (0..1) draws the figure on progressively - the whiteboard/scribe
    look - in order: legs, torso, arms, head, then face. 1.0 = fully drawn.

    Returns ``(head_center, head_radius)`` so callers can place effect glyphs
    around the head without recomputing the skeleton."""
    lean = pose.get("lean", 0)
    head = pose.get("head", 0)
    la, ra = pose.get("la", [18, 16]), pose.get("ra", [-18, -16])
    ll, rl = pose.get("ll", [10, 8]), pose.get("rl", [-10, -8])

    torso_ang = 180 - lean
    shoulder = _polar(hip, TORSO * unit, torso_ang)
    head_c = _polar(shoulder, (HEAD_R + HEAD_GAP) * unit, 180 - lean - head)
    hr = HEAD_R * unit

    # Draw-on order: legs (behind), torso, arms, head, face -> 6 stroke groups.
    n = 6
    legs = [(ll, 0), (rl, 1)]
    for ang, idx in legs:
        r = _part_reveal(reveal, idx, n)
        if r <= 0:
            continue
        knee = _polar(hip, THIGH * unit, ang[0])
        foot = _polar(knee, SHIN * unit, ang[1])
        sk.stroke([hip, knee, foot], color=color, width=lw, reveal=r)

    r_torso = _part_reveal(reveal, 2, n)
    if r_torso > 0:
        sk.stroke([hip, shoulder], color=color, width=lw, reveal=r_torso)

    for ang, idx in ((la, 3), (ra, 4)):
        r = _part_reveal(reveal, idx, n)
        if r <= 0:
            continue
        elbow = _polar(shoulder, UPPER_ARM * unit, ang[0])
        hand = _polar(elbow, FOREARM * unit, ang[1])
        sk.stroke([shoulder, elbow, hand], color=color, width=lw, reveal=r)

    r_head = _part_reveal(reveal, 5, n)
    if r_head > 0:
        sk.circle(head_c, hr, color=color, width=lw, amp=sk.wobble * 0.5, reveal=r_head)
    # face only once the head outline is essentially complete
    if r_head >= 0.85:
        _draw_face(sk, head_c, hr, face, color, blink=blink)
    return head_c, hr


# Faces that carry an emotion get eyebrows; the calm/default ones stay clean.
_BROWED = {"happy", "sad", "worried", "angry", "surprised", "think", "skeptical"}


def _brow(sk, x_in, x_out, y_in, y_out, color, lw):
    """One eyebrow as a short stroke from its inner end to its outer end."""
    sk.line((x_in, y_in), (x_out, y_out), color=color, width=lw)


def _draw_face(sk: Sketcher, c: Point, r: float, face: str, color, blink: bool = False) -> None:
    if face in (None, "none"):
        return
    cx, cy = c
    ex, ey = 0.36 * r, 0.12 * r
    eye_r = max(1.0, 0.10 * r)
    lw = sk.width * 0.7

    # ---- eyes ----
    if face == "shut" or blink:  # closed/peaceful eyes (or a momentary blink)
        sk.line((cx - ex * 1.4, cy - ey), (cx - ex * 0.3, cy - ey), color=color, width=lw)
        sk.line((cx + ex * 0.3, cy - ey), (cx + ex * 1.4, cy - ey), color=color, width=lw)
    else:
        er = eye_r * 1.3 if face == "surprised" else eye_r
        sk.dot((cx - ex, cy - ey), er, color=color)
        sk.dot((cx + ex, cy - ey), er, color=color)

    # ---- eyebrows (emotion) ----
    if face in _BROWED:
        by = cy - ey - 0.26 * r          # nominal brow line, above the eyes
        din = 0.16 * r                    # half brow length
        tilt = 0.10 * r                   # how strongly the brow angles
        if face in ("sad", "worried"):    # inner ends raised -> concerned
            _brow(sk, cx - ex + din, cx - ex - din, by - tilt, by + tilt, color, lw)
            _brow(sk, cx + ex - din, cx + ex + din, by - tilt, by + tilt, color, lw)
        elif face == "angry":             # inner ends lowered -> scowl
            _brow(sk, cx - ex + din, cx - ex - din, by + tilt, by - tilt * 0.4, color, lw)
            _brow(sk, cx + ex - din, cx + ex + din, by + tilt, by - tilt * 0.4, color, lw)
        elif face == "surprised":         # high, flat, lifted
            _brow(sk, cx - ex - din, cx - ex + din, by - 0.08 * r, by - 0.08 * r, color, lw)
            _brow(sk, cx + ex - din, cx + ex + din, by - 0.08 * r, by - 0.08 * r, color, lw)
        elif face in ("think", "skeptical"):  # one brow cocked up
            _brow(sk, cx - ex - din, cx - ex + din, by + 0.02 * r, by + 0.02 * r, color, lw)
            _brow(sk, cx + ex - din, cx + ex + din, by + tilt, by - tilt, color, lw)
        else:                              # happy: gentle raised brows
            _brow(sk, cx - ex - din, cx - ex + din, by + 0.03 * r, by - 0.03 * r, color, lw)
            _brow(sk, cx + ex - din, cx + ex + din, by - 0.03 * r, by + 0.03 * r, color, lw)

    # ---- mouth ----
    my, mw = 0.42 * r, 0.40 * r
    if face == "happy":
        sk.arc((cx, cy + my * 0.35), mw * 1.05, 20, 160, color=color, width=sk.width * 0.85)
    elif face in ("sad", "worried"):
        sk.arc((cx, cy + my * 1.35), mw, 205, 335, color=color, width=sk.width * 0.85)
    elif face == "surprised":
        sk.circle((cx, cy + my), mw * 0.42, color=color, width=lw)
    elif face == "angry":                  # tight downturned line
        sk.arc((cx, cy + my * 1.15), mw * 0.8, 210, 330, color=color, width=sk.width * 0.85)
    elif face in ("think", "skeptical"):   # small off-center flat mouth
        sk.line((cx - mw * 0.25, cy + my), (cx + mw * 0.45, cy + my), color=color, width=lw)
    elif face in ("neutral", "dots", "shut"):
        sk.line((cx - mw * 0.5, cy + my), (cx + mw * 0.5, cy + my), color=color, width=lw)
