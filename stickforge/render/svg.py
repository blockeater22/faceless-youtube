"""The SVG render backend: a Scene at time t -> a complete SVG document.

Draws each actor from forward-kinematics, a parametric face from the
expression, modular attachments (hair/hats/accessories from data), optional
scenery, props, and a caption — all under the scene camera. Pure strings; no
third-party dependencies.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from ..core.geometry import Vec2
from ..core.registry import Registry
from .canvas import SvgCanvas, _rng
from .config import RenderConfig

# Attachment drawers: fn(canvas, center: Vec2, head_r, angle, color, spec) -> None
ATTACHMENTS: "Registry" = Registry("attachment")


def _face_point(center: Vec2, r: float, lx: float, ly: float, angle: float) -> Vec2:
    """Map head-local (lx, ly) in head-radius units to world, honoring tilt."""
    return Vec2(lx * r, ly * r).rotated(angle) + center


class SvgRenderer:
    def __init__(self, config: RenderConfig | None = None) -> None:
        self.cfg = config or RenderConfig()

    # -- public ----------------------------------------------------------- #
    def render_frame(self, scene, t: float, frame_index: int = 0) -> str:
        cfg = self.cfg
        cv = SvgCanvas(cfg.width, cfg.height)
        self._seed = (frame_index // max(1, cfg.boil_every)) * 9973
        self._n = 0

        cam = scene.camera.sample(t)
        bg_color = scene.background.get("color", cfg.background)

        cx, cy = cfg.width / 2, cfg.height / 2
        z = cam["zoom"]
        tx, ty = cam["pan_x"] * cfg.width, cam["pan_y"] * cfg.height
        transform = (f"translate({cx:.1f},{cy:.1f}) scale({z:.4f}) "
                     f"translate({-cx:.1f},{-cy:.1f}) translate({tx:.1f},{ty:.1f})")

        cv.group_open(transform=transform)
        self._scenery(cv, scene.background, t)
        for actor in scene.actors:
            self._actor(cv, actor, t)
        for prop in scene.props:
            self._prop(cv, prop)
        cv.group_close()

        if scene.caption:
            self._caption(cv, scene.caption)
        return cv.to_svg(bg_color)

    # alias
    render = render_frame

    # -- internals -------------------------------------------------------- #
    @property
    def _wobble(self) -> float:
        return self.cfg.wobble * (self.cfg.min_dim / 1080.0)

    def _next_seed(self) -> int:
        self._n += 1
        return self._seed + self._n * 17

    def _actor(self, cv: SvgCanvas, actor, t: float) -> None:
        cfg = self.cfg
        posing = actor.posing_at(t)
        unit = actor.unit_scale * cfg.min_dim * posing.scale
        root = Vec2(actor.pos[0] * cfg.width + posing.offset.x * unit,
                    actor.pos[1] * cfg.height + posing.offset.y * unit)

        flip = ""
        if actor.facing < 0:
            flip = f"matrix(-1 0 0 1 {2 * root.x:.1f} 0)"
        if flip:
            cv.group_open(transform=flip)

        skel = actor.character.skeleton
        solved = skel.solve(root, unit, posing.pose)
        ink = actor.character.spec.ink
        lw = cfg.stroke_px * actor.character.spec.line_width

        # contact shadow under the lowest foot
        feet = [solved[b].end.y for b in ("shin_l", "shin_r") if b in solved]
        if feet:
            gy = max(feet)
            cv.elements.append(
                f'<ellipse cx="{root.x:.1f}" cy="{gy + lw:.1f}" '
                f'rx="{unit * 0.34:.1f}" ry="{unit * 0.05:.1f}" '
                f'fill="#000000" opacity="0.18"/>')

        def chain(*names):
            pts = []
            for nm in names:
                if nm in solved:
                    sb = solved[nm]
                    if not pts:
                        pts.append(sb.start)
                    pts.append(sb.end)
            return pts

        # legs (behind), spine, arms, then head + face on top
        cv.stroke(chain("thigh_l", "shin_l"), ink, lw, self._wobble, self._next_seed())
        cv.stroke(chain("thigh_r", "shin_r"), ink, lw, self._wobble, self._next_seed())
        cv.stroke(chain("spine"), ink, lw * 1.05, self._wobble, self._next_seed())
        cv.stroke(chain("upper_arm_l", "forearm_l"), ink, lw, self._wobble, self._next_seed())
        cv.stroke(chain("upper_arm_r", "forearm_r"), ink, lw, self._wobble, self._next_seed())

        head = skel.head(solved)
        if head is not None:
            hr = actor.character.head_radius * unit
            center = head.end
            # short neck from shoulders to the underside of the head
            neck_bottom = _face_point(center, hr, 0, 1.0, head.world_angle)
            cv.stroke([head.start, neck_bottom], ink, lw, self._wobble, self._next_seed())
            cv.circle(center, hr, ink, lw, wobble=self._wobble, seed=self._next_seed())
            self._face(cv, center, hr, head.world_angle, posing.expr, ink, lw)
            for att in actor.character.attachments:
                drawer = ATTACHMENTS.get(att.get("type", "")) if att.get("type") in ATTACHMENTS else None
                if drawer:
                    color = att.get("color", actor.character.spec.accent)
                    drawer(cv, center, hr, head.world_angle, color, att)

        if flip:
            cv.group_close()

    def _face(self, cv, center: Vec2, r: float, angle: float, e: dict,
              ink: str, lw: float) -> None:
        fp = lambda lx, ly: _face_point(center, r, lx, ly, angle)
        eye_open = e.get("eye_open", 1.0)
        wide = e.get("eye_wide", 0.0)
        px, py = e.get("pupil_x", 0.0), e.get("pupil_y", 0.0)
        eye_y = -0.10
        for sign in (-1, 1):
            ex = sign * 0.40
            c = fp(ex + px * 0.12, eye_y + py * 0.12)
            if eye_open < 0.35:                          # blink / shut -> short line
                a = fp(ex - 0.18, eye_y)
                b = fp(ex + 0.18, eye_y)
                cv.stroke([a, b], ink, lw * 0.7)
            elif wide > 0.3:                             # wide open -> ring + pupil
                cv.circle(c, r * (0.16 + 0.10 * wide), ink, lw * 0.7)
                cv.dot(c, r * 0.07, ink)
            else:                                        # default dot eye
                cv.dot(c, r * (0.11 * (0.6 + 0.4 * eye_open)), ink)

        # eyebrows
        for sign, key_h, key_a in ((-1, "brow_l_h", "brow_l_a"),
                                   (1, "brow_r_h", "brow_r_a")):
            bh = e.get(key_h, 0.0)
            ba = e.get(key_a, 0.0)
            base_y = -0.46 - bh * 0.5
            inner = fp(sign * 0.18, base_y + math.radians(ba) * sign * -0.6)
            outer = fp(sign * 0.56, base_y)
            cv.stroke([inner, outer], ink, lw * 0.8)

        # mouth
        self._mouth(cv, fp, e, ink, lw, r)

        if e.get("tears", 0.0) > 0.3:
            for sign in (-1, 1):
                top = fp(sign * 0.40, 0.05)
                bot = fp(sign * 0.40, 0.45)
                cv.stroke([top, bot], "#bcd3ff", lw * 0.7)

    def _mouth(self, cv, fp, e: dict, ink: str, lw: float, r: float) -> None:
        curve = e.get("mouth_curve", 0.0)
        opn = e.get("mouth_open", 0.0)
        skew = e.get("mouth_skew", 0.0)
        my, mw = 0.44, 0.40
        left = fp(-mw, my)
        right = fp(mw, my)
        if opn > 0.15:                                   # open mouth -> closed outline
            top = fp(skew * mw, my - curve * 0.10)
            bot = fp(skew * mw, my + opn * 0.45)
            d = (f"M {left.x:.1f} {left.y:.1f} "
                 f"Q {top.x:.1f} {top.y:.1f} {right.x:.1f} {right.y:.1f} "
                 f"Q {bot.x:.1f} {bot.y:.1f} {left.x:.1f} {left.y:.1f} Z")
            cv.path(d, ink, lw * 0.8)
        else:
            ctrl = fp(skew * mw, my + curve * 0.5)
            cv.quad((left.x, left.y), (ctrl.x, ctrl.y), (right.x, right.y), ink, lw * 0.8)

    # -- scenery / props / caption --------------------------------------- #
    def _scenery(self, cv: SvgCanvas, bg: dict, t: float) -> None:
        kind = bg.get("type", "plain")
        cfg = self.cfg
        if kind == "night":
            # moon
            mx, my = cfg.width * 0.78, cfg.height * 0.16
            cv.circle(Vec2(mx, my), cfg.min_dim * 0.07, "#f2ede1", 0, fill="#e8eef7")
            # deterministic stars
            for i in range(40):
                sx = (_rng(i * 3 + 1) * 0.5 + 0.5) * cfg.width
                sy = (_rng(i * 3 + 2) * 0.5 + 0.5) * cfg.height * 0.55
                cv.dot(Vec2(sx, sy), cfg.min_dim * 0.0016 * (1 + abs(_rng(i))), "#cfd8ea")
            # ground line
            gy = cfg.height * 0.82
            cv.stroke([Vec2(cfg.width * 0.04, gy), Vec2(cfg.width * 0.96, gy)],
                      bg.get("ink", "#48536b"), cfg.stroke_px * 0.8,
                      self._wobble, 7)
        elif kind == "ground":
            gy = cfg.height * bg.get("horizon", 0.82)
            cv.stroke([Vec2(cfg.width * 0.05, gy), Vec2(cfg.width * 0.95, gy)],
                      bg.get("ink", cfg.ink), cfg.stroke_px * 0.8, self._wobble, 7)

    def _prop(self, cv: SvgCanvas, prop: dict) -> None:
        cfg = self.cfg
        ptype = prop.get("type", "")
        pos = prop.get("pos", [0.5, 0.5])
        x, y = pos[0] * cfg.width, pos[1] * cfg.height
        color = prop.get("color", cfg.ink)
        size = prop.get("size", 0.05) * cfg.min_dim
        lw = cfg.stroke_px * prop.get("width", 0.8)
        if ptype == "label":
            cv.text(x, y, prop.get("text", ""),
                    prop.get("font", 0.035) * cfg.min_dim, color)
        elif ptype == "circle":
            cv.circle(Vec2(x, y), size, color, lw, fill=prop.get("fill", "none"),
                      wobble=self._wobble, seed=self._next_seed())
        elif ptype == "rect":
            cv.rect(x - size, y - size, size * 2, size * 2, prop.get("fill", color),
                    prop.get("opacity", 1.0))
        elif ptype == "line":
            to = prop.get("to", [pos[0] + 0.1, pos[1]])
            cv.stroke([Vec2(x, y), Vec2(to[0] * cfg.width, to[1] * cfg.height)],
                      color, lw, self._wobble, self._next_seed())

    def _caption(self, cv: SvgCanvas, text: str) -> None:
        cfg = self.cfg
        size = cfg.caption_size * cfg.min_dim
        y = cfg.height * 0.90
        # backing bar for legibility
        cv.rect(0, y - size, cfg.width, size * 1.7, "#000000", 0.28)
        cv.text(cfg.width / 2, y + size * 0.2, text, size, cfg.caption_color)


# --------------------------------------------------------------------------- #
# Built-in modular attachments (data-driven hair / hats / accessories).
# --------------------------------------------------------------------------- #
@ATTACHMENTS.register("hat_cone")
def _hat_cone(cv, center: Vec2, r, angle, color, spec):
    apex = _face_point(center, r, 0, -2.1, angle)
    left = _face_point(center, r, -1.0, -0.7, angle)
    right = _face_point(center, r, 1.0, -0.7, angle)
    d = (f"M {left.x:.1f} {left.y:.1f} L {apex.x:.1f} {apex.y:.1f} "
         f"L {right.x:.1f} {right.y:.1f} Z")
    cv.path(d, color, cv_width(cv), fill=color)


@ATTACHMENTS.register("hair_spikes")
def _hair_spikes(cv, center: Vec2, r, angle, color, spec):
    n = spec.get("count", 5)
    for i in range(n):
        lx = -0.8 + 1.6 * (i / (n - 1) if n > 1 else 0.5)
        base = _face_point(center, r, lx, -0.85, angle)
        tip = _face_point(center, r, lx * 1.05, -1.5, angle)
        cv.stroke([base, tip], color, cv_width(cv))


@ATTACHMENTS.register("hair_bob")
def _hair_bob(cv, center: Vec2, r, angle, color, spec):
    top = _face_point(center, r, 0, -1.5, angle)
    cv.circle(top, r * 0.95, color, cv_width(cv) * 0.8, fill=color)
    # cover the lower face line so it reads as a fringe
    cv.elements.append("")  # no-op keeps ordering explicit


@ATTACHMENTS.register("bowtie")
def _bowtie(cv, center: Vec2, r, angle, color, spec):
    neck = _face_point(center, r, 0, 1.25, angle)
    left = _face_point(center, r, -0.4, 1.25, angle)
    right = _face_point(center, r, 0.4, 1.25, angle)
    d = (f"M {left.x:.1f} {left.y:.1f} L {neck.x:.1f} {neck.y:.1f} "
         f"L {right.x:.1f} {right.y:.1f} L {left.x:.1f} {left.y:.1f} Z "
         f"M {neck.x:.1f} {neck.y:.1f} L {right.x:.1f} "
         f"{(2 * neck.y - left.y):.1f}")
    cv.path(d, color, cv_width(cv), fill=color)


@ATTACHMENTS.register("antenna")
def _antenna(cv, center: Vec2, r, angle, color, spec):
    base = _face_point(center, r, 0, -1.0, angle)
    tip = _face_point(center, r, 0, -1.9, angle)
    cv.stroke([base, tip], color, cv_width(cv) * 0.8)
    cv.dot(tip, r * 0.12, color)


def cv_width(cv: SvgCanvas) -> float:
    """A sensible default stroke for attachments, derived from canvas size."""
    return max(2.0, min(cv.width, cv.height) * 0.006)
