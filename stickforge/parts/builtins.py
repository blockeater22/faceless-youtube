"""The seed component library: illustrated art providers for each part style.

Each function draws one part style into an :class:`SvgCanvas` using a
:class:`PartFrame`. These are deliberately *vector* (filled, two-tone, with
appeal) — the opposite of thin stick-lines — and they read expression/style
params from the frame so a single style covers a continuous range of acting.

Quantity here is meant to grow (toward 50 heads / 120 eyes / …); the
architecture is what matters — every entry is an independent, recombinable
asset registered without touching the engine.
"""
from __future__ import annotations

import math

from . import (HEADS, HAIRS, EYES, BROWS, MOUTHS, HANDS, FEET, BODIES,
               CLOTHES, ACCESSORIES)
from .frame import PartFrame


def _clamp(v, lo=0.0, hi=1.0):
    return lo if v < lo else hi if v > hi else v


def _pt(v):
    return f"{v.x:.1f} {v.y:.1f}"


# --------------------------------------------------------------------------- #
# HEADS — the silhouette (filled skin + outline). Drawn first.
# --------------------------------------------------------------------------- #
@HEADS.register("round")
def head_round(cv, f: PartFrame):
    cv.ellipse(f.center, f.size, f.size * 1.06, f.color("skin", "#ffd9a8"),
               f.color("outline"), f.outline_w, rot=f.angle)


@HEADS.register("egg")
def head_egg(cv, f: PartFrame):
    c = f.at(0, 0.06)
    cv.ellipse(c, f.size * 0.92, f.size * 1.12, f.color("skin", "#ffd9a8"),
               f.color("outline"), f.outline_w, rot=f.angle)


@HEADS.register("wide")
def head_wide(cv, f: PartFrame):
    cv.ellipse(f.center, f.size * 1.12, f.size * 0.96, f.color("skin", "#ffd9a8"),
               f.color("outline"), f.outline_w, rot=f.angle)


@HEADS.register("square")
def head_square(cv, f: PartFrame):
    s = f.size
    tl, tr = f.at(-0.95, -0.95), f.at(0.95, -0.95)
    br, bl = f.at(0.95, 0.95), f.at(-0.95, 0.95)
    r = 0.42 * s
    d = (f"M {tl.x:.1f} {tl.y + r:.1f} Q {tl.x:.1f} {tl.y:.1f} {tl.x + r:.1f} {tl.y:.1f} "
         f"L {tr.x - r:.1f} {tr.y:.1f} Q {tr.x:.1f} {tr.y:.1f} {tr.x:.1f} {tr.y + r:.1f} "
         f"L {br.x:.1f} {br.y - r:.1f} Q {br.x:.1f} {br.y:.1f} {br.x - r:.1f} {br.y:.1f} "
         f"L {bl.x + r:.1f} {bl.y:.1f} Q {bl.x:.1f} {bl.y:.1f} {bl.x:.1f} {bl.y - r:.1f} Z")
    cv.filled_path(d, f.color("skin", "#ffd9a8"), f.color("outline"), f.outline_w)


# --------------------------------------------------------------------------- #
# HAIR — sits above the brow line so it never covers the eyes.
# --------------------------------------------------------------------------- #
@HAIRS.register("bald")
def hair_bald(cv, f: PartFrame):
    return


@HAIRS.register("tuft")
def hair_tuft(cv, f: PartFrame):
    col = f.color("hair", "#3a2a22")
    a = f.at(-0.78, -0.5)
    d = f"M {_pt(a)} "
    n = 4
    for i in range(n + 1):
        x = -0.78 + 1.56 * (i / n)
        d += f"L {_pt(f.at(x + 0.07, -1.16))} L {_pt(f.at(x + 0.2, -0.62))} "
    d += "Z"
    cv.filled_path(d, col, f.color("outline"), f.outline_w)


@HAIRS.register("spikes")
def hair_spikes(cv, f: PartFrame):
    col = f.color("hair", "#3a2a22")
    n = 6
    for i in range(n):
        x = -0.8 + 1.6 * (i / (n - 1))
        base_l, base_r = f.at(x - 0.14, -0.58), f.at(x + 0.14, -0.58)
        tip = f.at(x, -1.32)
        cv.filled_path(f"M {_pt(base_l)} L {_pt(tip)} L {_pt(base_r)} Z",
                       col, f.color("outline"), f.outline_w * 0.8)


@HAIRS.register("swoosh")
def hair_swoosh(cv, f: PartFrame):
    col = f.color("hair", "#3a2a22")
    a = f.at(-0.9, -0.45)
    c1 = f.at(-0.5, -1.4)
    c2 = f.at(0.8, -1.25)
    b = f.at(1.0, -0.35)
    base = f.at(0.2, -0.55)
    d = (f"M {_pt(a)} C {_pt(c1)} {_pt(c2)} {_pt(b)} "
         f"Q {_pt(f.at(0.5, -0.7))} {_pt(base)} Z")
    cv.filled_path(d, col, f.color("outline"), f.outline_w)


@HAIRS.register("mop")
def hair_mop(cv, f: PartFrame):
    col = f.color("hair", "#3a2a22")
    cv.ellipse(f.at(0, -0.78), f.size * 1.04, f.size * 0.62,
               col, f.color("outline"), f.outline_w, rot=f.angle)


@HAIRS.register("ponytail")
def hair_ponytail(cv, f: PartFrame):
    col = f.color("hair", "#3a2a22")
    # back tail
    cv.ellipse(f.at(-1.05, -0.2), f.size * 0.3, f.size * 0.6, col,
               f.color("outline"), f.outline_w, rot=f.angle - 18)
    hair_mop(cv, f)


# --------------------------------------------------------------------------- #
# EYES — big and expressive; modulated by eye_open / eye_wide / gaze.
# --------------------------------------------------------------------------- #
def _eye_pair(cv, f: PartFrame, w, h, style):
    eo = _clamp(f.p("eye_open", 1.0))
    wide = f.p("eye_wide", 0.0)
    gx, gy = f.p("pupil_x", 0.0), f.p("pupil_y", 0.0)
    ew = w * (1 + 0.35 * wide) * f.size
    eh = h * (1 + 0.35 * wide) * max(0.07, eo) * f.size
    ow = f.outline_w
    for sx in (-1, 1):
        cx_l = sx * 0.40
        if eo < 0.26:                                   # closed -> lash arc
            a, b = f.at(cx_l - 0.24, -0.02), f.at(cx_l + 0.24, -0.02)
            mid = f.at(cx_l, 0.06)
            cv.quad((a.x, a.y), (mid.x, mid.y), (b.x, b.y),
                    f.color("outline"), ow * 1.4)
            continue
        c = f.at(cx_l, -0.02)
        if style == "dot":
            cv.dot(c, eh * 0.9, f.color("outline", "#10131a"))
            continue
        cv.ellipse(c, ew, eh, f.color("eyewhite", "#ffffff"),
                   f.color("outline"), ow, rot=f.angle)
        pc = f.at(cx_l + gx * 0.14, -0.02 + gy * 0.14)
        cv.dot(pc, eh * 0.62, f.color("iris", "#3b4a66"))
        cv.dot(pc, eh * 0.34, "#10131a")
        hl = f.at(cx_l + 0.12 + gx * 0.14, -0.12 + gy * 0.14)
        cv.dot(hl, eh * 0.16, "#ffffff")


@EYES.register("cartoon")
def eyes_cartoon(cv, f):
    """Solid expressive eyes (the reference style): bold black ovals that change
    shape with eye_open/eye_wide, an upward arc when closed, gaze-aware."""
    eo = _clamp(f.p("eye_open", 1.0))
    wide = f.p("eye_wide", 0.0)
    gx, gy = f.p("pupil_x", 0.0), f.p("pupil_y", 0.0)
    rx = 0.165 * (1 + 0.45 * wide) * f.size
    ry = 0.225 * (1 + 0.55 * wide) * max(0.08, eo) * f.size
    col = f.color("outline", "#1b1b1b")
    ey = -0.05
    for sx in (-1, 1):
        cx_l = sx * 0.36
        if eo < 0.30:                                   # closed -> happy arc
            a, b = f.at(cx_l - 0.24, ey - 0.02), f.at(cx_l + 0.24, ey - 0.02)
            mid = f.at(cx_l, ey - 0.18)                  # concave-up (content)
            cv.quad((a.x, a.y), (mid.x, mid.y), (b.x, b.y), col, f.outline_w * 1.6)
            continue
        c = f.at(cx_l + gx * 0.12, ey + gy * 0.12)
        cv.ellipse(c, rx, ry, col, rot=f.angle)
        # tiny catch-light keeps solid eyes from going dead
        cv.dot(f.at(cx_l + 0.06 + gx * 0.12, ey - 0.08 + gy * 0.12), ry * 0.26, "#ffffff")


@EYES.register("round")
def eyes_round(cv, f):
    _eye_pair(cv, f, 0.26, 0.30, "round")


@EYES.register("oval")
def eyes_oval(cv, f):
    _eye_pair(cv, f, 0.22, 0.34, "round")


@EYES.register("anime")
def eyes_anime(cv, f):
    _eye_pair(cv, f, 0.30, 0.40, "round")


@EYES.register("dot")
def eyes_dot(cv, f):
    _eye_pair(cv, f, 0.12, 0.12, "dot")


@EYES.register("sleepy")
def eyes_sleepy(cv, f):
    f2 = PartFrame(f.center, f.size, f.angle, f.palette,
                   {**f.params, "eye_open": min(f.p("eye_open", 1.0), 0.5)},
                   f.outline_w)
    _eye_pair(cv, f2, 0.26, 0.30, "round")


# --------------------------------------------------------------------------- #
# BROWS — driven by brow_h (raise) and brow_a (inner tilt).
# --------------------------------------------------------------------------- #
def _brows(cv, f: PartFrame, thickness):
    for sx, kh, ka in ((-1, "brow_l_h", "brow_l_a"), (1, "brow_r_h", "brow_r_a")):
        h, a = f.p(kh), f.p(ka)
        y = -0.46 - h * 0.55
        inner = f.at(sx * 0.18, y + math.radians(a) * sx * -0.55)
        outer = f.at(sx * 0.58, y)
        cv.stroke([inner, outer], f.color("outline"), f.outline_w * thickness)


@BROWS.register("thin")
def brows_thin(cv, f):
    _brows(cv, f, 1.4)


@BROWS.register("thick")
def brows_thick(cv, f):
    _brows(cv, f, 2.6)


@BROWS.register("flat")
def brows_flat(cv, f):
    for sx in (-1, 1):
        y = -0.46 - f.p("brow_l_h" if sx < 0 else "brow_r_h") * 0.55
        cv.stroke([f.at(sx * 0.18, y), f.at(sx * 0.58, y)],
                  f.color("outline"), f.outline_w * 2.2)


# --------------------------------------------------------------------------- #
# MOUTHS — expression-driven (curve / open / skew) with a couple of styles.
# --------------------------------------------------------------------------- #
def _mouth(cv, f: PartFrame, mw, my):
    curve = f.p("mouth_curve", 0.0)
    opn = f.p("mouth_open", 0.0)
    skew = f.p("mouth_skew", 0.0)
    left, right = f.at(-mw, my), f.at(mw, my)
    if opn > 0.18:
        top = f.at(skew * mw, my - 0.04 - curve * 0.06)
        bot = f.at(skew * mw, my + opn * 0.42)
        d = (f"M {_pt(left)} Q {_pt(top)} {_pt(right)} "
             f"Q {_pt(bot)} {_pt(left)} Z")
        cv.filled_path(d, f.color("mouth", "#7a3b3b"), f.color("outline"), f.outline_w)
        if curve > 0.25:
            cv.dot(f.at(skew * mw, my + opn * 0.30), opn * 0.16 * f.size, "#d97b7b")
    else:
        ctrl = f.at(skew * mw, my + curve * 0.42)
        cv.quad((left.x, left.y), (ctrl.x, ctrl.y), (right.x, right.y),
                f.color("outline"), f.outline_w * 1.6)


@MOUTHS.register("default")
def mouth_default(cv, f):
    _mouth(cv, f, 0.32, 0.46)


@MOUTHS.register("wide")
def mouth_wide(cv, f):
    _mouth(cv, f, 0.44, 0.46)


@MOUTHS.register("small")
def mouth_small(cv, f):
    _mouth(cv, f, 0.22, 0.48)


# --------------------------------------------------------------------------- #
# HANDS — drawn at each forearm tip (center = tip, size = hand radius).
# --------------------------------------------------------------------------- #
@HANDS.register("ball")
def hand_ball(cv, f):
    cv.circle(f.center, f.size, f.color("outline"), f.outline_w,
              fill=f.color("skin", "#ffd9a8"))


@HANDS.register("mitt")
def hand_mitt(cv, f):
    cv.ellipse(f.center, f.size * 1.1, f.size * 0.85, f.color("skin", "#ffd9a8"),
               f.color("outline"), f.outline_w, rot=f.angle)
    # thumb nub
    cv.circle(f.at(0.8, -0.6), f.size * 0.45, f.color("outline"),
              f.outline_w, fill=f.color("skin", "#ffd9a8"))


@HANDS.register("four_finger")
def hand_four_finger(cv, f):
    """Simple cartoon hand: a rounded palm with four short finger nubs."""
    skin = f.color("skin", "#ffffff")
    out = f.color("outline", "#1b1b1b")
    cv.circle(f.center, f.size, out, f.outline_w, fill=skin)
    for i in range(4):
        a = -0.6 + i * 0.4
        nub = f.at(a, -0.95)
        cv.circle(nub, f.size * 0.34, out, f.outline_w * 0.8, fill=skin)


@HANDS.register("glove")
def hand_glove(cv, f):
    cv.circle(f.center, f.size * 1.05, f.color("outline"), f.outline_w,
              fill=f.color("accent", "#ffffff"))
    cv.circle(f.at(0, 0.9), f.size * 0.55, f.color("outline"),
              f.outline_w, fill=f.color("accent", "#ffffff"))


# --------------------------------------------------------------------------- #
# FEET — drawn at each shin tip (center = ankle, size = foot length).
# --------------------------------------------------------------------------- #
@FEET.register("shoe")
def foot_shoe(cv, f):
    # upright (frame angle is 0); a rounded shoe seated at the ankle
    c = f.at(0.12, 0.32)
    cv.ellipse(c, f.size * 1.05, f.size * 0.5, f.color("shoe", "#1b1b1b"),
               f.color("outline"), f.outline_w)


@FEET.register("boot")
def foot_boot(cv, f):
    c = f.at(0.12, 0.30)
    cv.ellipse(c, f.size * 1.05, f.size * 0.55, f.color("shoe", "#1b1b1b"),
               f.color("outline"), f.outline_w)
    cv.rect(c.x - f.size * 0.55, c.y - f.size * 1.0, f.size * 1.1, f.size * 0.7,
            f.color("shoe", "#1b1b1b"))


@FEET.register("bare")
def foot_bare(cv, f):
    c = f.at(0.1, 0.30)
    cv.ellipse(c, f.size * 0.95, f.size * 0.45, f.color("skin", "#ffffff"),
               f.color("outline"), f.outline_w)


# --------------------------------------------------------------------------- #
# BODY builds — parameter dicts (thickness/shoulder), read by the renderer.
# --------------------------------------------------------------------------- #
BODIES.register("slim", {"limb": 0.050, "torso": 0.090, "shoulder": 0.10, "belly": 0.0})
BODIES.register("regular", {"limb": 0.072, "torso": 0.120, "shoulder": 0.17, "belly": 0.0})
BODIES.register("round", {"limb": 0.072, "torso": 0.150, "shoulder": 0.14, "belly": 0.18})
BODIES.register("broad", {"limb": 0.070, "torso": 0.135, "shoulder": 0.26, "belly": 0.05})


# --------------------------------------------------------------------------- #
# CLOTHING — drawn over the torso (center = torso mid, size = torso length).
# --------------------------------------------------------------------------- #
@CLOTHES.register("none")
def clothes_none(cv, f):
    return


@CLOTHES.register("tie")
def clothes_tie(cv, f):
    top = f.at(0, -0.42)
    d = (f"M {_pt(f.at(-0.12, -0.42))} L {_pt(f.at(0.12, -0.42))} "
         f"L {_pt(f.at(0.18, 0.35))} L {_pt(f.at(0, 0.5))} "
         f"L {_pt(f.at(-0.18, 0.35))} Z")
    cv.filled_path(d, f.color("accent", "#c0392b"), f.color("outline"), f.outline_w)


@CLOTHES.register("buttons")
def clothes_buttons(cv, f):
    for i in range(3):
        cv.dot(f.at(0, -0.25 + i * 0.3), f.size * 0.04, f.color("outline"))


@CLOTHES.register("collar")
def clothes_collar(cv, f):
    cv.filled_path(
        f"M {_pt(f.at(-0.22, -0.45))} L {_pt(f.at(0, -0.2))} "
        f"L {_pt(f.at(0.22, -0.45))} Z",
        f.color("accent", "#ecf0f1"), f.color("outline"), f.outline_w)


# --------------------------------------------------------------------------- #
# ACCESSORIES — drawn over the face (center = head, size = head radius).
# --------------------------------------------------------------------------- #
@ACCESSORIES.register("none")
def acc_none(cv, f):
    return


@ACCESSORIES.register("glasses")
def acc_glasses(cv, f):
    for sx in (-1, 1):
        cv.circle(f.at(sx * 0.40, -0.02), f.size * 0.30,
                  f.color("outline"), f.outline_w * 1.2, fill="none")
    cv.stroke([f.at(-0.12, -0.02), f.at(0.12, -0.02)], f.color("outline"),
              f.outline_w * 1.2)


@ACCESSORIES.register("hat_top")
def acc_hat_top(cv, f):
    brim_l, brim_r = f.at(-1.0, -0.6), f.at(1.0, -0.6)
    cv.stroke([brim_l, brim_r], f.color("accent", "#222"), f.outline_w * 3)
    d = (f"M {_pt(f.at(-0.6, -0.62))} L {_pt(f.at(-0.6, -1.5))} "
         f"L {_pt(f.at(0.6, -1.5))} L {_pt(f.at(0.6, -0.62))} Z")
    cv.filled_path(d, f.color("accent", "#222"), f.color("outline"), f.outline_w)


@ACCESSORIES.register("blush")
def acc_blush(cv, f):
    for sx in (-1, 1):
        cv.ellipse(f.at(sx * 0.55, 0.28), f.size * 0.16, f.size * 0.10,
                   "#ff9aa2", opacity=0.6, rot=f.angle)
