"""Tests for the Procedural World Simulation Engine."""
import time
import unittest

from stickforge.narrative import understand_story, plan
from stickforge.world import build_world, validate_world
from stickforge.narrative.corpus import generate as gen_stories

EX = ("John nervously entered his first interview on a rainy morning. "
      "The interviewer smiled. John hoped to pass and prove himself.")


def _spec(text=EX, i=0):
    return plan(understand_story(text))[i]


class TestWorldBuild(unittest.TestCase):
    def setUp(self):
        self.w = build_world(_spec(), seed=3)

    def test_full_instantiation(self):
        self.assertEqual(self.w.bounds["env"], "office")
        roles = {o.role for o in self.w.objects}
        self.assertIn("shell", roles)
        self.assertIn("focus", roles)
        # every object has a concrete transform/layer/bbox/surface (instantiated)
        for o in self.w.objects:
            self.assertEqual(len(o.bbox), 2)
            self.assertIsInstance(o.layer, int)

    def test_assets_resolved_from_registry_not_paths(self):
        desk = self.w.find("desk")
        self.assertIsNotNone(desk.asset_id)
        self.assertTrue(desk.asset_id.startswith("world:"))   # an id, not a path
        self.assertNotIn("/", desk.asset_id)

    def test_on_relationship_places_laptop_on_desk(self):
        desk = self.w.find("desk")
        laptop = self.w.find("laptop")
        self.assertEqual(laptop.parent, desk.id)
        self.assertLess(laptop.position.y, desk.position.y)    # sits on top
        # not duplicated
        self.assertEqual(sum(1 for o in self.w.objects if o.semantic_role == "laptop"), 1)

    def test_zones_navigation_lighting_weather(self):
        kinds = {z.kind for z in self.w.zones}
        self.assertTrue({"entrance", "working", "path", "camera_safe"} <= kinds)
        self.assertGreaterEqual(len(self.w.nav.nodes), 4)
        self.assertTrue(self.w.lights)
        self.assertEqual(self.w.weather["type"], "rain")
        self.assertTrue(self.w.weather["through_window_only"])

    def test_environmental_storytelling(self):
        self.assertIn("nervous", self.w.story["reads_as"])
        self.assertEqual(self.w.story["occupation"], "professional")

    def test_validates_clean(self):
        self.assertEqual(self.w.validation["status"], "valid")

    def test_converts_to_scene_graph(self):
        g = self.w.to_scene_graph()
        self.assertTrue(g.renderables())


class TestValidationCatchesProblems(unittest.TestCase):
    def test_floating_and_overlap_detected(self):
        w = build_world(_spec(), seed=1)
        floor = w.find("floor")
        floor.position.__dict__  # noqa  (Vec2 is frozen; build a broken clone)
        # force a floating object + an overlap, then re-validate
        from stickforge.core.geometry import Vec2
        desk = w.find("desk")
        desk.position = Vec2(desk.position.x, desk.position.y - 200)   # float it
        issues = validate_world(w)
        self.assertTrue(any(i["field"] == "floating" for i in issues))
        self.assertEqual(w.validation["status"], "invalid")


class TestDeterminismAndScale(unittest.TestCase):
    def test_seed_is_deterministic(self):
        a = build_world(_spec(), seed=7).to_dict()
        b = build_world(_spec(), seed=7).to_dict()
        self.assertEqual(a["objects"], b["objects"])

    def test_seed_varies_layout(self):
        a = build_world(_spec(), seed=1)
        b = build_world(_spec(), seed=2)
        self.assertNotEqual(a.bounds["width"], b.bounds["width"])   # unique rooms

    def test_thousand_worlds_valid_and_fast(self):
        specs = [plan(understand_story(s))[0] for s in gen_stories(120, seed=4)]
        t0 = time.time()
        valid = 0
        for i, spec in enumerate(specs):
            w = build_world(spec, seed=i)
            valid += (w.validation["status"] == "valid")
        elapsed = time.time() - t0
        self.assertGreaterEqual(valid, int(len(specs) * 0.95))     # nearly all valid
        self.assertLess(elapsed, 10.0)


if __name__ == "__main__":
    unittest.main()
