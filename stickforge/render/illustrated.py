"""The illustrated cartoon-actor renderer (the StickForge house style).

This is NOT a stickman of circles + lines. It assembles an *illustrated actor*
from part-style art providers (head/hair/eyes/brows/mouth/hands/feet/clothing)
over a cartoon-proportioned rig, with a flat high-contrast palette, rounded
shoulders, thick rubber-hose limbs, simple hands and shoes, and a ground
shadow. Lines are clean and consistent — no sketch/boil effect — per the style
guide.
"""
from __future__ import annotations

from ..core.geometry import Vec2
from ..parts import (HEADS, HAIRS, EYES, BROWS, MOUTHS, HANDS, FEET, BODIES,
                     CLOTHES, ACCESSORIES)
from ..parts.frame import PartFrame
from ..character.design import ActorDesign, CLASSIC_PALETTE
from .canvas import SvgCanvas, _rng
from .config import RenderConfig


def _perp(a: Vec2, b: Vec2) -> Vec2:
    """Unit vector perpendicular to a->b."""
    d = b - a
    n = d.length() or 1.0
    return Vec2(-d.y / n, d.x / n)


class IllustratedRenderer:
    def __init__(self, config: RenderConfig | None = None) -> None:
        self.cfg = config or RenderConfig()

    def render_frame(self, scene, t: float, frame_index: int = 0) -> str:
        cfg = self.cfg
        cv = SvgCanvas(cfg.width, cfg.height)
        self._fi = frame_index
        cam = scene.camera.sample(t)
        bg_color = scene.background.get("color", cfg.background)
        cx, cy = cfg.width / 2, cfg.height / 2
        z = cam["zoom"]
        tx, ty = cam["pan_x"] * cfg.width, cam["pan_y"] * cfg.height
        transform = (f"translate({cx:.1f},{cy:.1f}) scale({z:.4f}) "
                     f"translate({-cx:.1f},{-cy:.1f}) translate({tx:.1f},{ty:.1f})")
        cv.group_open(transform=transform)
        self._scenery(cv, scene.background)
        for actor in scene.actors:
            self._actor(cv, actor, t)
        for prop in scene.props:
            self._prop(cv, prop)
        cv.group_close()
        if scene.caption:
            self._caption(cv, scene.caption)
        return cv.to_svg(bg_color)

    render = render_frame

    # ------------------------------------------------------------------ #
    def _design(self, actor) -> ActorDesign:
        d = getattr(actor.character, "design", None)
        return d if isinstance(d, ActorDesign) else ActorDesign()

    def _actor(self, cv: SvgCanvas, actor, t: float) -> None:
        cfg = self.cfg
        design = self._design(actor)
        pal = {**CLASSIC_PALETTE, **design.palette}
        build = BODIES.get(design.part("body")) if design.part("body") in BODIES \
            else {"limb": 0.065, "torso": 0.12, "shoulder": 0.16, "belly": 0.0}

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
        out = pal["outline"]
        skin = pal["skin"]
        ow = cfg.stroke_px * 0.85 * design.line_width          # bold, consistent
        limb_fill = build["limb"] * unit
        limb_out = limb_fill + 2 * ow

        # --- secondary motion: solve a moment earlier for follow-through ---
        dt = 0.05
        gain, cap = 0.55, unit * 0.10
        prev = actor.posing_at(max(0.0, t - dt))
        root_p = Vec2(actor.pos[0] * cfg.width + prev.offset.x * unit,
                      actor.pos[1] * cfg.height + prev.offset.y * unit)
        solved_p = skel.solve(root_p, unit, prev.pose)

        def lag(name):
            if name not in solved or name not in solved_p:
                return Vec2(0.0, 0.0)
            d = (solved_p[name].end - solved[name].end) * gain
            m = d.length()
            return d * (cap / m) if m > cap else d

        def chain(*names):
            pts = []
            for nm in names:
                if nm in solved:
                    sb = solved[nm]
                    if not pts:
                        pts.append(sb.start)
                    pts.append(sb.end)
            return pts

        # --- ground shadow ------------------------------------------------
        feet_y = [solved[b].end.y for b in ("shin_l", "shin_r") if b in solved]
        if feet_y:
            cv.ellipse(Vec2(root.x, max(feet_y) + limb_out * 0.6),
                       unit * 0.36, unit * 0.05, "#000000", opacity=0.16)

        # shoulder geometry (also used to seat the arms at the shoulders)
        sp, sh = solved["spine"].start, solved["spine"].end
        perp = _perp(sp, sh)
        arm_off = perp * (build["shoulder"] * unit * 0.78)

        # --- legs (white) + feet -----------------------------------------
        for thigh, shin in (("thigh_l", "shin_l"), ("thigh_r", "shin_r")):
            cv.limb(chain(thigh, shin), out, skin, limb_out, limb_fill)
        for shin in ("shin_l", "shin_r"):
            if shin in solved:
                self._part(FEET, design.part("feet"), cv,
                           solved[shin].end, unit * 0.115, 0.0, pal, {}, ow)

        # --- shorts (black) over the upper thighs ------------------------
        for thigh in ("thigh_l", "thigh_r"):
            if thigh in solved:
                sb = solved[thigh]
                mid = sb.start.lerp(sb.end, 0.42)
                cv.limb([sb.start, mid], out, pal["pants"],
                        limb_out * 1.5, limb_fill * 1.5)
        cv.ellipse(solved["spine"].start, build["shoulder"] * unit * 0.66,
                   unit * 0.11, pal["pants"], out, ow)

        # --- arms (white) + hands, seated at the shoulders ---------------
        # left arm sits on -perp side, right arm on +perp side
        for ua, fa, side, hkey in (("upper_arm_l", "forearm_l", -1, "l"),
                                   ("upper_arm_r", "forearm_r", 1, "r")):
            off = arm_off * side
            pts = [p + off for p in chain(ua, fa)]
            cv.limb(pts, out, skin, limb_out, limb_fill)
            if fa in solved:
                gesture = posing.hands.get(hkey) or design.part("hands")
                # hand follows through; oriented along the forearm
                self._part(HANDS, gesture, cv, solved[fa].end + off + lag(fa),
                           limb_fill * 1.0, solved[fa].world_angle, pal, {}, ow)

        # --- torso (shirt) with rounded shoulders + short sleeves --------
        self._torso(cv, solved, unit, build, pal, ow)
        self._part(CLOTHES, design.part("clothing"), cv,
                   solved["spine"].start.lerp(solved["spine"].end, 0.5),
                   (solved["spine"].end - solved["spine"].start).length(),
                   solved["spine"].world_angle, pal, {}, ow)

        # --- neck + head --------------------------------------------------
        head = skel.head(solved)
        if head is not None:
            hr = actor.character.head_radius * unit * design.head_scale
            center = head.end
            neck_top = center + (head.start - center).normalized() * (hr * 0.9)
            cv.limb([head.start, neck_top], out, skin, limb_out * 0.8, limb_fill * 0.8)
            ang = head.world_angle
            self._part(HEADS, design.part("head"), cv, center, hr, ang, pal, {}, ow)
            # hair bounces / trails the head (secondary motion)
            self._part(HAIRS, design.part("hair"), cv, center + lag("head") * 1.4,
                       hr, ang, pal, {}, ow)
            face = posing.expr
            self._part(EYES, design.part("eyes"), cv, center, hr, ang, pal, face, ow)
            self._part(BROWS, design.part("brows"), cv, center, hr, ang, pal, face, ow)
            self._part(MOUTHS, design.part("mouth"), cv, center, hr, ang, pal, face, ow)
            self._part(ACCESSORIES, design.part("accessory"), cv, center, hr, ang,
                       pal, face, ow)

        if flip:
            cv.group_close()

    def _part(self, registry, name, cv, center, size, angle, palette, params, ow):
        if name not in registry:
            return
        drawer = registry.get(name)
        if callable(drawer):
            drawer(cv, PartFrame(center, size, angle, palette, params, ow))

    def _torso(self, cv, solved, unit, build, pal, ow):
        sp = solved["spine"].start            # hip center
        sh = solved["spine"].end              # shoulder center
        perp = _perp(sp, sh)
        up = (sh - sp).normalized()
        sw = build["shoulder"] * unit
        hw = sw * 0.62
        belly = build.get("belly", 0.0) * unit
        SL, SR = sh + perp * sw, sh - perp * sw
        HL, HR = sp + perp * hw, sp - perp * hw
        neck = sh + up * (unit * 0.02)
        # rounded-shoulder, slightly tapered, soft-bellied torso
        cl = SL + perp * (belly)              # side bulge controls
        cr = SR - perp * (belly)
        d = (f"M {HL.x:.1f} {HL.y:.1f} "
             f"Q {cl.x:.1f} {(HL.y+SL.y)/2:.1f} {SL.x:.1f} {SL.y:.1f} "
             f"Q {SL.x:.1f} {(SL.y+neck.y)/2-unit*0.04:.1f} {neck.x:.1f} {neck.y:.1f} "
             f"Q {SR.x:.1f} {(SR.y+neck.y)/2-unit*0.04:.1f} {SR.x:.1f} {SR.y:.1f} "
             f"Q {cr.x:.1f} {(HR.y+SR.y)/2:.1f} {HR.x:.1f} {HR.y:.1f} Z")
        cv.filled_path(d, pal["shirt"], pal["outline"], ow)
        # short-sleeve caps over the shoulders
        for shoulder in (SL, SR):
            cv.circle(shoulder.lerp(sh, 0.28), build["limb"] * unit * 1.15 + ow,
                      pal["outline"], ow, fill=pal["shirt"])

    # ------------------------------------------------------------------ #
    def _scenery(self, cv: SvgCanvas, bg: dict) -> None:
        cfg = self.cfg
        kind = bg.get("type", "plain")
        if kind == "night":
            cv.circle(Vec2(cfg.width * 0.80, cfg.height * 0.15),
                      cfg.min_dim * 0.075, "#e8eef7", 0, fill="#eef3fb")
            for i in range(46):
                sx = (_rng(i * 3 + 1) * 0.5 + 0.5) * cfg.width
                sy = (_rng(i * 3 + 2) * 0.5 + 0.5) * cfg.height * 0.55
                cv.dot(Vec2(sx, sy), cfg.min_dim * 0.0016, "#cfd8ea")
        elif kind == "ground":
            gy = cfg.height * bg.get("horizon", 0.82)
            cv.stroke([Vec2(cfg.width * 0.04, gy), Vec2(cfg.width * 0.96, gy)],
                      bg.get("ink", "#48536b"), cfg.stroke_px * 0.8)

    def _prop(self, cv: SvgCanvas, prop: dict) -> None:
        cfg = self.cfg
        ptype = prop.get("type", "")
        pos = prop.get("pos", [0.5, 0.5])
        x, y = pos[0] * cfg.width, pos[1] * cfg.height
        if ptype == "label":
            cv.text(x, y, prop.get("text", ""),
                    prop.get("font", 0.030) * cfg.min_dim, prop.get("color", cfg.ink))
        elif ptype == "fx":
            from .fx import draw_fx
            draw_fx(cv, prop.get("name", ""), Vec2(x, y),
                    prop.get("size", 0.06) * cfg.min_dim, prop.get("color", cfg.ink))

    def _caption(self, cv: SvgCanvas, text: str) -> None:
        cfg = self.cfg
        size = cfg.caption_size * cfg.min_dim
        y = cfg.height * 0.90
        cv.rect(0, y - size, cfg.width, size * 1.7, "#000000", 0.30)
        cv.text(cfg.width / 2, y + size * 0.2, text, size, cfg.caption_color)
