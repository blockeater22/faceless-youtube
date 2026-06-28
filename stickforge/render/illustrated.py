"""The illustrated cartoon-actor renderer.

Draws an *illustrated actor* (head/hair/eyes/brows/mouth/hands/feet/clothing art
providers over a cartoon rig) — but it no longer draws to screen coordinates.
It builds a :class:`~stickforge.stage.SceneGraph` in **world space**, then a
:class:`~stickforge.stage.Camera2D` projects every node to pixels (with layer
parallax). The Cinematic/World engines drive that graph + camera without this
renderer changing.
"""
from __future__ import annotations

from ..core.geometry import Vec2
from ..parts import (HEADS, HAIRS, EYES, BROWS, MOUTHS, HANDS, FEET, BODIES,
                     CLOTHES, ACCESSORIES)
from ..parts.frame import PartFrame
from ..character.design import ActorDesign, CLASSIC_PALETTE
from ..stage import Camera2D, Layer, SceneGraph, Viewport, World, REFERENCE
from .canvas import SvgCanvas, _rng
from .config import RenderConfig


def _perp(a: Vec2, b: Vec2) -> Vec2:
    d = b - a
    n = d.length() or 1.0
    return Vec2(-d.y / n, d.x / n)


class IllustratedRenderer:
    def __init__(self, config: RenderConfig | None = None) -> None:
        self.cfg = config or RenderConfig()

    # ------------------------------------------------------------------ #
    def render_frame(self, scene, t: float, frame_index: int = 0,
                     silhouette: bool = False) -> str:
        cfg = self.cfg
        self._fi = frame_index
        self._silhouette = silhouette
        cv = SvgCanvas(cfg.width, cfg.height)
        vp = Viewport(cfg.width, cfg.height)

        cam_s = scene.camera.sample(t)
        cam = Camera2D.from_pan_zoom(cam_s["zoom"], cam_s["pan_x"], cam_s["pan_y"], vp)

        graph = self.build_graph(scene, vp)
        for node in graph.renderables():
            kind = node.content.get("kind")
            if kind == "scenery":
                self._scenery(cv, node, cam, vp)
            elif kind == "actor":
                self._actor(cv, node, cam, vp, t)
            elif kind == "prop":
                self._prop(cv, node, cam, vp)

        text = scene.subtitle_at(t) if hasattr(scene, "subtitle_at") else scene.caption
        if text:
            self._caption(cv, text)                       # OVERLAY: screen space
        return cv.to_svg(scene.background.get("color", cfg.background))

    render = render_frame

    def build_graph(self, scene, vp: Viewport) -> SceneGraph:
        """Convert a Scene into a world-space SceneGraph (compat bridge)."""
        g = SceneGraph()
        g.spawn("scenery", Vec2(0, 0), Layer.BACKGROUND,
                content={"kind": "scenery", "bg": scene.background})
        for actor in scene.actors:
            wp = World.frac_to_world(actor.pos[0], actor.pos[1], vp)
            g.spawn(actor.id, wp, Layer.ACTORS,
                    content={"kind": "actor", "actor": actor})
        for i, prop in enumerate(scene.props):
            pos = prop.get("pos", [0.5, 0.5])
            wp = World.frac_to_world(pos[0], pos[1], vp)
            layer = (Layer.OVERLAY if prop.get("type") == "label"
                     else Layer.FX if prop.get("type") == "fx" else Layer.FOREGROUND)
            g.spawn(f"prop{i}", wp, layer, content={"kind": "prop", "prop": prop})
        return g

    # ------------------------------------------------------------------ #
    def _design(self, actor) -> ActorDesign:
        d = getattr(actor.character, "design", None)
        return d if isinstance(d, ActorDesign) else ActorDesign()

    def _actor(self, cv, node, cam: Camera2D, vp: Viewport, t: float) -> None:
        actor = node.content["actor"]
        cfg = self.cfg
        design = self._design(actor)
        pal = {**CLASSIC_PALETTE, **design.palette}
        if self._silhouette:
            pal = {k: CLASSIC_PALETTE["outline"] for k in pal}
        build = getattr(design, "build", None) or (
            BODIES.get(design.part("body")) if design.part("body") in BODIES
            else {"limb": 0.065, "torso": 0.12, "shoulder": 0.16, "belly": 0.0})

        posing = actor.posing_at(t)
        par = node.effective_parallax
        s = cam.screen_scale(vp)
        unit = actor.unit_scale * REFERENCE * posing.scale * s   # screen px per figure
        # project the actor's world root (+ in-figure offset) to the screen
        wpos = node.world_pos()
        unit_world = actor.unit_scale * REFERENCE * posing.scale
        wroot = Vec2(wpos.x + posing.offset.x * unit_world,
                     wpos.y + posing.offset.y * unit_world)
        root = cam.project(wroot, vp, par)

        flip = f"matrix(-1 0 0 1 {2 * root.x:.1f} 0)" if actor.facing < 0 else ""
        if flip:
            cv.group_open(transform=flip)

        skel = actor.character.skeleton
        solved = skel.solve(root, unit, posing.pose)
        out, skin = pal["outline"], pal["skin"]
        ow = cfg.stroke_px * 0.85 * design.line_width
        limb_fill = build["limb"] * unit
        limb_out = limb_fill + 2 * ow

        # secondary motion: solve a moment earlier (follow-through)
        gain, cap = 0.55, unit * 0.10
        prev = actor.posing_at(max(0.0, t - 0.05))
        root_p = cam.project(Vec2(wpos.x + prev.offset.x * unit_world,
                                  wpos.y + prev.offset.y * unit_world), vp, par)
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

        feet_y = [solved[b].end.y for b in ("shin_l", "shin_r") if b in solved]
        if feet_y:
            cv.ellipse(Vec2(root.x, max(feet_y) + limb_out * 0.6),
                       unit * 0.36, unit * 0.05, "#000000", opacity=0.16)

        sp, sh = solved["spine"].start, solved["spine"].end
        perp = _perp(sp, sh)
        arm_off = perp * (build["shoulder"] * unit * 0.78)

        for thigh, shin in (("thigh_l", "shin_l"), ("thigh_r", "shin_r")):
            cv.limb(chain(thigh, shin), out, skin, limb_out, limb_fill)
        for shin in ("shin_l", "shin_r"):
            if shin in solved:
                self._part(FEET, design.part("feet"), cv,
                           solved[shin].end, unit * 0.115, 0.0, pal, {}, ow)

        for thigh in ("thigh_l", "thigh_r"):
            if thigh in solved:
                sb = solved[thigh]
                cv.limb([sb.start, sb.start.lerp(sb.end, 0.42)], out, pal["pants"],
                        limb_out * 1.5, limb_fill * 1.5)
        cv.ellipse(solved["spine"].start, build["shoulder"] * unit * 0.66,
                   unit * 0.11, pal["pants"], out, ow)

        for ua, fa, side, hkey in (("upper_arm_l", "forearm_l", -1, "l"),
                                   ("upper_arm_r", "forearm_r", 1, "r")):
            off = arm_off * side
            cv.limb([p + off for p in chain(ua, fa)], out, skin, limb_out, limb_fill)
            if fa in solved:
                gesture = posing.hands.get(hkey) or design.part("hands")
                self._part(HANDS, gesture, cv, solved[fa].end + off + lag(fa),
                           limb_fill, solved[fa].world_angle, pal, {}, ow)

        self._torso(cv, solved, unit, build, pal, ow)
        self._part(CLOTHES, design.part("clothing"), cv,
                   solved["spine"].start.lerp(solved["spine"].end, 0.5),
                   (solved["spine"].end - solved["spine"].start).length(),
                   solved["spine"].world_angle, pal, {}, ow)

        head = skel.head(solved)
        if head is not None:
            hr = actor.character.head_radius * unit * design.head_scale
            center = head.end
            neck_top = center + (head.start - center).normalized() * (hr * 0.9)
            cv.limb([head.start, neck_top], out, skin, limb_out * 0.8, limb_fill * 0.8)
            ang = head.world_angle
            self._part(HEADS, design.part("head"), cv, center, hr, ang, pal, {}, ow)
            self._part(HAIRS, design.part("hair"), cv, center + lag("head") * 1.4,
                       hr, ang, pal, {}, ow)
            # expose world anchors for future engines (props/eye-targets/framing)
            self._set_anchors(node, cam, vp, par, solved, center)
            if self._silhouette:
                if flip:
                    cv.group_close()
                return
            face = posing.expr
            self._part(EYES, design.part("eyes"), cv, center, hr, ang, pal, face, ow)
            self._part(BROWS, design.part("brows"), cv, center, hr, ang, pal, face, ow)
            self._part(MOUTHS, design.part("mouth"), cv, center, hr, ang, pal, face, ow)
            self._part(ACCESSORIES, design.part("accessory"), cv, center, hr, ang,
                       pal, face, ow)

        if flip:
            cv.group_close()

    def _set_anchors(self, node, cam, vp, par, solved, head_center) -> None:
        """Store world-space anchors (head/hands/feet) by un-projecting screen
        joints — so the Cinematic/World engines can frame or attach to them."""
        wpos = node.world_pos()
        pts = {"head": head_center}
        if "forearm_l" in solved:
            pts["hand_l"] = solved["forearm_l"].end
        if "forearm_r" in solved:
            pts["hand_r"] = solved["forearm_r"].end
        feet = [solved[b].end for b in ("shin_l", "shin_r") if b in solved]
        if feet:
            pts["feet"] = Vec2(sum(p.x for p in feet) / len(feet),
                               max(p.y for p in feet))
        for name, sp in pts.items():
            w = cam.unproject(sp, vp, par)
            node.anchors[name] = Vec2(w.x - wpos.x, w.y - wpos.y)

    def _part(self, registry, name, cv, center, size, angle, palette, params, ow):
        if name in registry:
            drawer = registry.get(name)
            if callable(drawer):
                drawer(cv, PartFrame(center, size, angle, palette, params, ow))

    def _torso(self, cv, solved, unit, build, pal, ow):
        sp, sh = solved["spine"].start, solved["spine"].end
        perp = _perp(sp, sh)
        up = (sh - sp).normalized()
        sw = build["shoulder"] * unit
        hw = sw * 0.62
        belly = build.get("belly", 0.0) * unit
        SL, SR = sh + perp * sw, sh - perp * sw
        HL, HR = sp + perp * hw, sp - perp * hw
        neck = sh + up * (unit * 0.02)
        cl, cr = SL + perp * belly, SR - perp * belly
        d = (f"M {HL.x:.1f} {HL.y:.1f} "
             f"Q {cl.x:.1f} {(HL.y+SL.y)/2:.1f} {SL.x:.1f} {SL.y:.1f} "
             f"Q {SL.x:.1f} {(SL.y+neck.y)/2-unit*0.04:.1f} {neck.x:.1f} {neck.y:.1f} "
             f"Q {SR.x:.1f} {(SR.y+neck.y)/2-unit*0.04:.1f} {SR.x:.1f} {SR.y:.1f} "
             f"Q {cr.x:.1f} {(HR.y+SR.y)/2:.1f} {HR.x:.1f} {HR.y:.1f} Z")
        cv.filled_path(d, pal["shirt"], pal["outline"], ow)
        for shoulder in (SL, SR):
            cv.circle(shoulder.lerp(sh, 0.28), build["limb"] * unit * 1.15 + ow,
                      pal["outline"], ow, fill=pal["shirt"])

    # ------------------------------------------------------------------ #
    def _scenery(self, cv, node, cam: Camera2D, vp: Viewport) -> None:
        bg = node.content["bg"]
        kind = bg.get("type", "plain")
        size = vp.world_size()
        s = cam.screen_scale(vp)
        if kind == "night":
            moon = cam.project(Vec2(0.30 * size.x, -0.34 * size.y), vp, 0.12)
            cv.circle(moon, 0.075 * REFERENCE * s, "#e8eef7", 0, fill="#eef3fb")
            for i in range(46):
                wx = (_rng(i * 3 + 1)) * 0.5 * size.x
                wy = (_rng(i * 3 + 2) * 0.5 - 0.5) * size.y * 0.95
                star = cam.project(Vec2(wx, wy), vp, 0.2)
                cv.dot(star, max(0.8, 0.0016 * REFERENCE * s), "#cfd8ea")
        elif kind == "ground":
            gy = (bg.get("horizon", 0.82) - 0.5) * size.y
            a = cam.project(Vec2(-0.46 * size.x, gy), vp, 1.0)
            b = cam.project(Vec2(0.46 * size.x, gy), vp, 1.0)
            cv.stroke([a, b], bg.get("ink", "#48536b"), self.cfg.stroke_px * 0.8 * s)

    def _prop(self, cv, node, cam: Camera2D, vp: Viewport) -> None:
        prop = node.content["prop"]
        ptype = prop.get("type", "")
        par = node.effective_parallax
        s = cam.screen_scale(vp)
        p = cam.project(node.world_pos(), vp, par)
        if ptype == "label":
            cv.text(p.x, p.y, prop.get("text", ""),
                    prop.get("font", 0.030) * REFERENCE * s, prop.get("color", self.cfg.ink))
        elif ptype == "fx":
            from .fx import draw_fx
            draw_fx(cv, prop.get("name", ""), p,
                    prop.get("size", 0.06) * REFERENCE * s, prop.get("color", self.cfg.ink))

    def _caption(self, cv: SvgCanvas, text: str) -> None:
        cfg = self.cfg
        size = cfg.caption_size * cfg.min_dim
        y = cfg.height * 0.90
        cv.rect(0, y - size, cfg.width, size * 1.7, "#000000", 0.30)
        cv.text(cfg.width / 2, y + size * 0.2, text, size, cfg.caption_color)
