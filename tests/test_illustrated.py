"""Tests for the Character Design System: parts, designs, illustrated render, FX."""
import unittest

from stickforge import parts
from stickforge.parts import CATEGORIES, catalog, combination_count
from stickforge.parts.frame import PartFrame
from stickforge.core.geometry import Vec2
from stickforge.character.design import ActorDesign, PALETTES, classic_design
from stickforge.character.character import build_character
from stickforge.character.skeleton import cartoon_humanoid
from stickforge.render.config import RenderConfig
from stickforge.render.illustrated import IllustratedRenderer
from stickforge.render.canvas import SvgCanvas
from stickforge.render.fx import FX, draw_fx
from stickforge.scene.scene import Scene, Actor
from stickforge.animation.clip import AnimationClip


class TestParts(unittest.TestCase):
    def test_seed_library_populated(self):
        cat = catalog()
        for required in ("head", "hair", "eyes", "brows", "mouth",
                         "hands", "feet", "body"):
            self.assertIn(required, cat)
            self.assertTrue(cat[required], f"{required} has no styles")
        self.assertIn("cartoon", cat["eyes"])
        self.assertIn("four_finger", cat["hands"])

    def test_combination_count_large(self):
        self.assertGreater(combination_count(), 100_000)

    def test_part_frame_orientation(self):
        f = PartFrame(Vec2(100, 100), 10.0, angle=0.0)
        p = f.at(1, 0)               # local +x, no rotation
        self.assertAlmostEqual(p.x, 110.0)
        self.assertAlmostEqual(p.y, 100.0)

    def test_every_drawer_runs(self):
        cv = SvgCanvas(200, 200)
        f = PartFrame(Vec2(100, 100), 30.0, 0.0,
                      palette=dict(PALETTES["classic"]),
                      params={"eye_open": 1.0, "mouth_curve": 0.5, "mouth_open": 0.4},
                      outline_w=3.0)
        for name, reg in CATEGORIES.items():
            if name == "body":
                continue            # body styles are param dicts, not drawers
            for style in reg.names():
                drawer = reg.get(style)
                if callable(drawer):
                    drawer(cv, f)    # must not raise
        self.assertTrue(cv.elements)


class TestDesign(unittest.TestCase):
    def test_default_is_cartoon_classic(self):
        d = ActorDesign()
        self.assertEqual(d.skeleton, "cartoon")
        self.assertEqual(d.palette["shirt"], "#f4c20d")
        self.assertEqual(d.part("hands"), "four_finger")

    def test_from_dict_named_palette_and_parts(self):
        d = ActorDesign.from_dict({"id": "x", "palette": "blue",
                                   "parts": {"hair": "spikes"}})
        self.assertEqual(d.palette["shirt"], PALETTES["blue"]["shirt"])
        self.assertEqual(d.part("hair"), "spikes")
        self.assertEqual(d.part("eyes"), "cartoon")   # default retained

    def test_build_character_attaches_design(self):
        c = build_character({"id": "z", "palette": "green",
                             "parts": {"body": "round"}})
        self.assertIsInstance(c.design, ActorDesign)
        self.assertEqual(c.skeleton.name, "cartoon")
        self.assertEqual(c.design.part("body"), "round")


class TestIllustratedRender(unittest.TestCase):
    def _scene(self, expr="happy", char=None):
        clip = AnimationClip.from_spec({
            "duration": 1.0, "poses": [{"t": 0, "pose": "stand"}],
            "expressions": [{"t": 0, "expr": expr}]})
        actor = Actor(character=build_character(char or {"id": "h"}),
                      clip=clip, pos=(0.5, 0.55), unit_scale=0.34, life=0.0)
        return Scene(id="s", duration=1.0,
                     background={"type": "plain", "color": "#fff"}, actors=[actor])

    def test_renders_valid_svg_with_parts(self):
        svg = IllustratedRenderer(RenderConfig.for_format("preview")).render_frame(
            self._scene(), 0.0)
        self.assertTrue(svg.startswith("<svg"))
        self.assertIn("</svg>", svg)
        self.assertIn("#f4c20d", svg)              # the yellow tee is present
        self.assertIn("<ellipse", svg)             # illustrated shapes, not just lines

    def test_palette_changes_output(self):
        blue = self._scene(char={"id": "b", "palette": "blue"})
        svg = IllustratedRenderer(RenderConfig.for_format("preview")).render_frame(blue, 0.0)
        self.assertIn(PALETTES["blue"]["shirt"], svg)

    def test_no_wobble_clean_lines(self):
        # the illustrated backend must not use the sketch 'boil' jitter
        r = IllustratedRenderer(RenderConfig.for_format("preview"))
        a = r.render_frame(self._scene(), 0.0, frame_index=0)
        b = r.render_frame(self._scene(), 0.0, frame_index=7)
        self.assertEqual(a, b)                      # deterministic, no per-frame jitter


class TestGesturesAndMotion(unittest.TestCase):
    def test_hand_gestures_registered(self):
        for g in ("open_hand", "point", "thumbs_up", "peace", "fist", "wave"):
            self.assertIn(g, parts.HANDS)

    def test_hands_track_holds_latest(self):
        clip = AnimationClip.from_spec({
            "duration": 3.0,
            "poses": [{"t": 0, "pose": "idle"}],
            "hands": [{"t": 0, "l": "fist", "r": "fist"},
                      {"t": 1.0, "r": "point"}]})
        self.assertEqual(clip.sample(0.5).hands.get("r"), "fist")
        self.assertEqual(clip.sample(2.0).hands.get("r"), "point")

    def test_secondary_motion_renders(self):
        lib = __import__("stickforge.studio", fromlist=["load_core_library"]).load_core_library()
        scene = Scene.from_spec({
            "id": "s", "duration": 1.0,
            "actors": [{"id": "a", "character": "actor.max",
                        "clip_id": "clip.explain", "pos": [0.5, 0.55],
                        "unit_scale": 0.34}]}, lib)
        svg = IllustratedRenderer(RenderConfig.for_format("preview")).render_frame(scene, 0.7, 17)
        self.assertIn("</svg>", svg)        # gesture + lag path must not crash

    def test_walk_clip_present(self):
        lib = __import__("stickforge.studio", fromlist=["load_core_library"]).load_core_library()
        self.assertIn("clip.walk", lib)


class TestFX(unittest.TestCase):
    def test_effects_registered_and_draw(self):
        for name in ("speed_lines", "impact", "sweat", "stars", "lightbulb",
                     "hearts", "anger", "question"):
            self.assertIn(name, FX)
        cv = SvgCanvas(100, 100)
        for name in FX.names():
            draw_fx(cv, name, Vec2(50, 50), 12.0, "#000")
        self.assertTrue(cv.elements)


if __name__ == "__main__":
    unittest.main()
