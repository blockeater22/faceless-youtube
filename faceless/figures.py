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
    # --- 6 new poses (ref-image gesture vocabulary) ---
    # arms crossed across the chest - inner forearms cross over the torso
    "crossed":   {"lean": 0,  "head": 0,   "la": [62, 124],  "ra": [-62, -124], "ll": [10, 8],   "rl": [-10, -8]},
    # hands on hips - upper arms out, forearms angle back to the pelvis
    "hips":      {"lean": 0,  "head": 0,   "la": [58, 152],  "ra": [-58, -152], "ll": [10, 8],   "rl": [-10, -8]},
    # both arms reaching forward to hold a box (parallel, slightly down)
    "hold_box":  {"lean": 4,  "head": -2,  "la": [98, 96],   "ra": [-98, -96],  "ll": [12, 10],  "rl": [-12, -10]},
    # head turned, one hand shielding eyes - "looking around"
    "look_around": {"lean": -2,"head": -16,"la": [134, 156], "ra": [-22, -18],  "ll": [10, 8],   "rl": [-10, -8]},
    # face-palm - one hand up to the face
    "facepalm":  {"lean": -4, "head": -6,  "la": [168, 200], "ra": [-22, -18],  "ll": [10, 8],   "rl": [-10, -8]},
    # two-hand celebrate (higher than 'celebrate', straight up)
    "cheer":     {"lean": -2, "head": -8,  "la": [172, 180], "ra": [-172, -180],"ll": [12, 9],   "rl": [-12, -9]},
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
                blink: bool = False, reveal: float = 1.0,
                shirt=None, hands: bool = False) -> tuple[Point, float]:
    """Draw a stick figure. ``hip`` is the pixel anchor, ``unit`` the pixel U.

    ``blink`` momentarily closes the eyes (driven by wall-clock time in the
    renderer) so the character feels alive instead of frozen.

    ``reveal`` (0..1) draws the figure on progressively - the whiteboard/scribe
    look - in order: legs, torso, arms, head, then face. 1.0 = fully drawn.

    ``shirt`` (an RGB tuple) fills a simple coloured tee over the torso; ``hands``
    caps the arms with small fists. Both default off so existing stories are
    unchanged.

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
    # coloured shirt: a flat tee silhouette behind the ink torso, fading in with
    # the torso draw-on so it doesn't pop ahead of the line work.
    if shirt is not None and r_torso > 0.45:
        ux, uy = shoulder[0] - hip[0], shoulder[1] - hip[1]
        ln = math.hypot(ux, uy) or 1e-6
        px, py = -uy / ln, ux / ln                  # unit normal to the torso
        sw, hw = 0.16 * unit, 0.115 * unit          # shoulder/hip half-widths
        neck = _polar(shoulder, 0.05 * unit, torso_ang)
        poly = [(neck[0] + px * sw, neck[1] + py * sw),
                (neck[0] - px * sw, neck[1] - py * sw),
                (hip[0] - px * hw, hip[1] - py * hw),
                (hip[0] + px * hw, hip[1] + py * hw)]
        sk.draw.polygon(poly, fill=shirt)
    if r_torso > 0:
        sk.stroke([hip, shoulder], color=color, width=lw, reveal=r_torso)

    for ang, idx in ((la, 3), (ra, 4)):
        r = _part_reveal(reveal, idx, n)
        if r <= 0:
            continue
        elbow = _polar(shoulder, UPPER_ARM * unit, ang[0])
        hand = _polar(elbow, FOREARM * unit, ang[1])
        sk.stroke([shoulder, elbow, hand], color=color, width=lw, reveal=r)
        if hands and r >= 0.95:                      # a small fist at the wrist
            sk.dot(hand, 0.05 * unit, color=color)

    r_head = _part_reveal(reveal, 5, n)
    if r_head > 0:
        sk.circle(head_c, hr, color=color, width=lw, amp=sk.wobble * 0.5, reveal=r_head)
    # face only once the head outline is essentially complete
    if r_head >= 0.85:
        _draw_face(sk, head_c, hr, face, color, blink=blink)
    return head_c, hr


def draw_character(sk: Sketcher, hip: Point, unit: float, pose: dict,
                   color=(20, 22, 26), face: str = "dots", blink: bool = False,
                   shirt=(255, 200, 40), shorts=(24, 26, 32),
                   shadow: bool = True, hair: str = "tufts") -> tuple[Point, float]:
    """A *bold cartoon* character (thick clean outlines, T-shirt + sleeves,
    shorts, mitten hands, shoes, ground shadow) - the polished look, vs the thin
    ``draw_figure`` doodle. Reuses the same pose skeleton, so every existing pose
    / face / effect works unchanged. Returns ``(head_center, head_radius)``."""
    d = sk.draw
    ink = tuple(color)
    white = (255, 255, 255)
    lean = pose.get("lean", 0)
    head = pose.get("head", 0)
    la, ra = pose.get("la", [18, 16]), pose.get("ra", [-18, -16])
    ll, rl = pose.get("ll", [10, 8]), pose.get("rl", [-10, -8])

    torso_ang = 180 - lean
    shoulder = _polar(hip, TORSO * unit, torso_ang)
    head_c = _polar(shoulder, (HEAD_R * 1.25 + HEAD_GAP) * unit, 180 - lean - head)
    hr = HEAD_R * 1.4 * unit                       # bigger, rounder head
    lw = max(3, int(0.052 * unit))                 # thick limb weight
    ow = max(2, int(lw * 0.42))                    # outline weight on fills

    knees, feet = [], []
    for ang in (ll, rl):
        knee = _polar(hip, THIGH * unit, ang[0])
        knees.append(knee)
        feet.append(_polar(knee, SHIN * unit, ang[1]))
    elbows, hands = [], []
    for ang in (la, ra):
        elbow = _polar(shoulder, UPPER_ARM * unit, ang[0])
        elbows.append(elbow)
        hands.append(_polar(elbow, FOREARM * unit, ang[1]))

    def limb(p0, p1, w, fill):
        d.line([p0, p1], fill=fill, width=int(w), joint="curve")
        r = w / 2.0
        for p in (p0, p1):
            d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=fill)

    def disc(c, r, fill, outline=None):
        box = [c[0] - r, c[1] - r, c[0] + r, c[1] + r]
        d.ellipse(box, fill=fill, outline=outline, width=ow if outline else 1)

    def shoe(c, rx, ry, fill, outline):
        d.ellipse([c[0] - rx, c[1] - ry, c[0] + rx, c[1] + ry], fill=fill, outline=outline, width=ow)

    def midpoint(a, b, f=0.5):
        return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)

    # 1) ground shadow
    if shadow:
        fy = max(f[1] for f in feet)
        sw = unit * 0.46
        d.ellipse([hip[0] - sw, fy - unit * 0.03, hip[0] + sw, fy + unit * 0.07],
                  fill=(0, 0, 0, 38))
    # 2) legs + 3) shoes
    for knee, foot in zip(knees, feet):
        limb(hip, knee, lw, ink)
        limb(knee, foot, lw, ink)
    for foot in feet:
        shoe((foot[0], foot[1] + lw * 0.15), lw * 1.15, lw * 0.78, white, ink)  # oval shoe
    # 4) shorts: black over pelvis + upper thighs
    for knee in knees:
        limb(hip, midpoint(hip, knee, 0.5), lw * 1.6, shorts)
    disc(hip, lw * 1.15, shorts)
    # 5) arms (forearms stay bare)
    for elbow, hand in zip(elbows, hands):
        limb(shoulder, elbow, lw, ink)
        limb(elbow, hand, lw, ink)
    # 6) shirt body (filled + outlined trapezoid)
    ux, uy = shoulder[0] - hip[0], shoulder[1] - hip[1]
    ln = math.hypot(ux, uy) or 1e-6
    px, py = -uy / ln, ux / ln
    sw, hw = 0.24 * unit, 0.19 * unit
    neck = _polar(shoulder, 0.04 * unit, torso_ang)
    poly = [(neck[0] + px * sw, neck[1] + py * sw), (neck[0] - px * sw, neck[1] - py * sw),
            (hip[0] - px * hw, hip[1] - py * hw), (hip[0] + px * hw, hip[1] + py * hw)]
    d.polygon(poly, fill=shirt)
    d.line(poly + [poly[0]], fill=ink, width=ow, joint="curve")
    # 7) sleeves: shirt-coloured caps over the upper arms (outlined so they read)
    for elbow in elbows:
        limb(shoulder, midpoint(shoulder, elbow, 0.58), lw * 1.6, shirt)
    # 8) mitten hands (bigger, gloved)
    for hand in hands:
        disc(hand, lw * 1.02, white, ink)
    # 9) head + hair + face
    disc(head_c, hr, white, ink)
    _draw_hair(d, head_c, hr, hair, ink)
    _draw_face(sk, head_c, hr, face, ink, blink=blink, whites=True)
    return head_c, hr


def _draw_hair(d, head_c, hr: float, style: str, ink) -> None:
    """Small hair tufts on top of the head - the missing ref-image detail."""
    if not style or style == "none":
        return
    cx, cy = head_c
    if style == "tufts":
        # three little triangular tufts off the crown
        tips = [(-0.55, -1.06), (0.0, -1.18), (0.55, -1.06)]
        base_w = hr * 0.22
        for tx, ty in tips:
            px, py = cx + hr * tx, cy + hr * ty
            d.polygon([(px - base_w, py + base_w * 0.7),
                       (px + base_w, py + base_w * 0.7),
                       (px, py - base_w * 1.1)], fill=ink)
    elif style == "swoosh":
        # a side-sweep wedge above the brow line
        d.polygon([(cx - hr * 0.95, cy - hr * 0.55),
                   (cx + hr * 0.05, cy - hr * 1.05),
                   (cx + hr * 0.45, cy - hr * 0.45)], fill=ink)
    elif style == "wild":
        # 5 sharp spikes for an energetic look
        for fx in (-0.7, -0.35, 0.0, 0.35, 0.7):
            px = cx + hr * fx
            top = cy - hr * (1.15 + 0.08 * (1 - abs(fx)))
            d.polygon([(px - hr * 0.13, cy - hr * 0.85),
                       (px + hr * 0.13, cy - hr * 0.85),
                       (px, top)], fill=ink)


# Faces that carry an emotion get eyebrows; the calm/default ones stay clean.
_BROWED = {"happy", "sad", "worried", "angry", "surprised", "think", "skeptical",
           "laughing", "crying", "shocked", "grit", "smug", "tongue"}


def _brow(sk, x_in, x_out, y_in, y_out, color, lw):
    """One eyebrow as a short stroke from its inner end to its outer end."""
    sk.line((x_in, y_in), (x_out, y_out), color=color, width=lw)


def _draw_face(sk: Sketcher, c: Point, r: float, face: str, color, blink: bool = False,
               whites: bool = False) -> None:
    if face in (None, "none"):
        return
    cx, cy = c
    ex, ey = 0.36 * r, 0.12 * r
    eye_r = max(1.0, 0.10 * r)
    lw = sk.width * 0.7
    bg = (255, 255, 255)                        # eye-white fill (bold style)

    # ---- eyes ----
    if face == "shut" or blink:  # closed/peaceful eyes (or a momentary blink)
        sk.line((cx - ex * 1.4, cy - ey), (cx - ex * 0.3, cy - ey), color=color, width=lw)
        sk.line((cx + ex * 0.3, cy - ey), (cx + ex * 1.4, cy - ey), color=color, width=lw)
    elif whites:
        # Bold-style: white eye discs with smaller black pupils. Pupil offsets
        # carry the gaze direction so a 'look_up'/'look_around' actually reads.
        wr = eye_r * (2.0 if face == "surprised" else 1.7)
        pr = eye_r * (0.8 if face == "surprised" else 0.7)
        gx, gy = 0.0, 0.0
        if face == "surprised":
            gy = -0.2 * wr                  # eyes wide, pupils up
        elif face == "skeptical":
            gx = 0.35 * wr                  # side-eye
        elif face == "think":
            gx, gy = 0.25 * wr, -0.25 * wr
        for sx in (-1, 1):
            sk.circle((cx + sx * ex, cy - ey), wr, color=color, width=lw, fill=bg, segments=18)
            sk.dot((cx + sx * ex + gx, cy - ey + gy), pr, color=color)
    else:
        er = eye_r * 1.3 if face == "surprised" else eye_r
        sk.dot((cx - ex, cy - ey), er, color=color)
        sk.dot((cx + ex, cy - ey), er, color=color)

    # ---- eyebrows (emotion) ----
    if face in _BROWED:
        by = cy - ey - 0.26 * r          # nominal brow line, above the eyes
        din = 0.16 * r                    # half brow length
        tilt = 0.10 * r                   # how strongly the brow angles
        if face in ("sad", "worried", "crying"):    # inner ends raised -> concerned
            _brow(sk, cx - ex + din, cx - ex - din, by - tilt, by + tilt, color, lw)
            _brow(sk, cx + ex - din, cx + ex + din, by - tilt, by + tilt, color, lw)
        elif face in ("angry", "grit"):   # inner ends lowered -> scowl
            _brow(sk, cx - ex + din, cx - ex - din, by + tilt, by - tilt * 0.4, color, lw)
            _brow(sk, cx + ex - din, cx + ex + din, by + tilt, by - tilt * 0.4, color, lw)
        elif face in ("surprised", "shocked"):  # high, flat, lifted
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
    mw_thick = sk.width * 0.85
    if face == "happy":
        sk.arc((cx, cy + my * 0.35), mw * 1.05, 20, 160, color=color, width=mw_thick)
    elif face == "laughing":                # wide open smile, filled
        sk.circle((cx, cy + my * 0.55), mw * 0.65, color=color, width=lw, fill=color)
        # white teeth strip across the top of the mouth
        sk.line((cx - mw * 0.55, cy + my * 0.32), (cx + mw * 0.55, cy + my * 0.32),
                color=(255, 255, 255), width=int(lw * 1.4))
    elif face in ("sad", "worried"):
        sk.arc((cx, cy + my * 1.35), mw, 205, 335, color=color, width=mw_thick)
    elif face == "crying":                  # wobble line - downturned, jagged
        n = 6
        pts = [(cx + (i / n - 0.5) * mw * 1.4,
                cy + my * 0.85 + (0.06 * mw if i % 2 else -0.06 * mw))
               for i in range(n + 1)]
        sk.stroke(pts, color=color, width=mw_thick)
    elif face == "surprised":
        sk.circle((cx, cy + my), mw * 0.42, color=color, width=lw)
    elif face == "shocked":                 # taller open O
        sk.circle((cx, cy + my * 1.05), mw * 0.5, color=color, width=lw, fill=color)
    elif face == "angry":                   # tight downturned line
        sk.arc((cx, cy + my * 1.15), mw * 0.8, 210, 330, color=color, width=mw_thick)
    elif face == "grit":                    # bared teeth - a wide flat line with vertical ticks
        y0 = cy + my * 0.95
        sk.line((cx - mw * 0.55, y0), (cx + mw * 0.55, y0), color=color, width=lw)
        for f in (-0.35, -0.05, 0.25, 0.55):
            x = cx + mw * f
            sk.line((x, y0 - mw * 0.18), (x, y0 + mw * 0.05), color=color, width=int(lw * 0.7))
    elif face == "smug":                    # asymmetric upturned curl (one side)
        sk.arc((cx + mw * 0.18, cy + my * 0.45), mw * 0.7, 0, 150, color=color, width=mw_thick)
    elif face == "tongue":                  # smile with a tongue tip out
        sk.arc((cx, cy + my * 0.35), mw * 1.05, 20, 160, color=color, width=mw_thick)
        sk.dot((cx + mw * 0.05, cy + my * 0.85), mw * 0.16, color=(228, 95, 110))
    elif face in ("think", "skeptical"):    # small off-center flat mouth
        sk.line((cx - mw * 0.25, cy + my), (cx + mw * 0.45, cy + my), color=color, width=lw)
    elif face in ("neutral", "dots", "shut"):
        sk.line((cx - mw * 0.5, cy + my), (cx + mw * 0.5, cy + my), color=color, width=lw)
