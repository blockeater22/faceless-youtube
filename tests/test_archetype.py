"""Tests for the personality-first archetype system (distinct silhouettes)."""
import unittest

from stickforge.character.archetype import (
    ARCHETYPES, get_archetype, parametric_skeleton)
from stickforge.character.character import build_character
from stickforge.character.design import ActorDesign
from stickforge.core.geometry import Vec2
from stickforge.pose.pose import POSES
from stickforge.render.config import RenderConfig
from stickforge.render.illustrated import IllustratedRenderer
from stickforge.studio import build_cast, build_silhouette_test


class TestArchetypes(unittest.TestCase):
    def test_founding_cast_registered(self):
        for a in ("hero", "kid", "brute", "sage", "clerk", "diva"):
            self.assertIn(a, ARCHETYPES)

    def test_signature_stances_registered(self):
        for p in ("arms_crossed", "hands_clasped", "hand_on_hip", "power_stance"):
            self.assertIn(p, POSES)

    def test_proportions_are_distinct(self):
        # the whole point: archetypes must NOT share proportions
        def metrics(a):
            arch = get_archetype(a)
            return (round(arch.head_radius, 3), round(arch.spine, 3),
                    round(arch.thigh + arch.shin, 3))
        sigs = {a: metrics(a) for a in ("hero", "kid", "brute", "sage")}
        self.assertEqual(len(set(sigs.values())), 4)      # all different
        # the Kid's head dwarfs the Brute's; the Sage out-legs the Kid
        self.assertGreater(get_archetype("kid").head_radius,
                           get_archetype("brute").head_radius * 1.5)
        self.assertGreater(get_archetype("sage").thigh,
                           get_archetype("kid").thigh * 1.5)

    def test_parametric_skeleton_reflects_archetype(self):
        kid = parametric_skeleton(get_archetype("kid"))
        sage = parametric_skeleton(get_archetype("sage"))
        self.assertGreater(kid.head_radius, sage.head_radius)
        sk = kid.solve(Vec2(0, 0), 100.0, {})
        sp = sage.solve(Vec2(0, 0), 100.0, {})
        kid_leg = (sk["shin_l"].end - sk["thigh_l"].start).length()
        sage_leg = (sp["shin_l"].end - sp["thigh_l"].start).length()
        self.assertGreater(sage_leg, kid_leg)

    def test_build_character_uses_archetype(self):
        c = build_character({"id": "h", "archetype": "hero"})
        self.assertEqual(c.design.archetype, "hero")
        self.assertEqual(c.skeleton.name, "hero")
        self.assertIsNotNone(c.design.build)
        self.assertEqual(c.design.base_pose, "power_stance")

    def test_archetype_overrides_apply(self):
        d = ActorDesign.from_dict({"id": "x", "archetype": "kid",
                                   "palette": "blue", "parts": {"hair": "spikes"}})
        self.assertEqual(d.archetype, "kid")
        self.assertEqual(d.part("hair"), "spikes")        # override wins
        self.assertEqual(d.part("eyes"), "round")         # archetype default kept


class TestCastAndSilhouette(unittest.TestCase):
    def test_cast_builds_six(self):
        self.assertEqual(len(build_cast().actors), 6)

    def test_silhouette_render(self):
        scene = build_silhouette_test()
        svg = IllustratedRenderer(RenderConfig.for_format("16:9")).render_frame(
            scene, 0.0, silhouette=True)
        self.assertIn("</svg>", svg)
        # silhouette suppresses face detail: no white catch-lights
        self.assertNotIn("#ffffff", svg.split("<rect")[-1])


if __name__ == "__main__":
    unittest.main()
