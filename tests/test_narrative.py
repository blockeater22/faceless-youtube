"""Tests for the cognitive layer: understanding, intent graph, scene planning."""
import time
import unittest

from stickforge.narrative import (understand_story, plan, summarize_story,
                                  segment_story, extract_characters,
                                  build_intent_graph, plan_scene,
                                  validate_scene_graph, infer_environment,
                                  infer_emotion_curve, SceneSpec)
from stickforge.narrative import corpus

EX = ("John nervously entered his first interview on a rainy morning. "
      "The interviewer smiled. John hoped to pass and prove himself.")


class TestSegmentation(unittest.TestCase):
    def test_multi_scene_split(self):
        seg = segment_story("Ann smiled at home.\nLater, Ann arrived at the office.")
        self.assertGreaterEqual(len(seg.scenes), 2)

    def test_dialogue_beats(self):
        seg = segment_story("ALEX: Hello there!\nSAM: Hi.")
        speakers = {b.speaker for s in seg.scenes for b in s.beats}
        self.assertEqual(speakers, {"ALEX", "SAM"})

    def test_always_one_scene(self):
        self.assertGreaterEqual(len(segment_story("x").scenes), 1)


class TestUnderstanding(unittest.TestCase):
    def setUp(self):
        self.u = understand_story(EX)

    def test_infers_setting_time_weather(self):
        self.assertEqual(self.u.analysis.extra["environment"].value, "office")
        self.assertEqual(self.u.analysis.time.value, "morning")
        self.assertEqual(self.u.analysis.weather.value, "rain")

    def test_mood_is_nervous_by_pov(self):
        self.assertEqual(self.u.analysis.mood.value, "nervous")

    def test_character_extracted_with_emotion_and_goal(self):
        self.assertIn("John", self.u.characters)
        john = self.u.characters["John"]
        self.assertEqual(john.current_emotion.value, "nervous")
        self.assertLess(john.confidence_level, 0.5)     # nervous -> low confidence
        self.assertTrue(john.goal.value)

    def test_confidence_scores_present(self):
        self.assertGreater(self.u.analysis.weather.confidence, 0.5)

    def test_summary(self):
        s = summarize_story(self.u)
        self.assertEqual(s["weather"], "rain")
        self.assertIn("John", s["characters"])


class TestIntentGraph(unittest.TestCase):
    def test_graph_has_core_intent(self):
        u = understand_story(EX)
        g = u.intent_graphs[0]
        types = {n.type for n in g.nodes}
        self.assertIn("goal", types)
        self.assertIn("emotion", types)
        self.assertIn("fear", types)
        self.assertIn("audience_emotion", types)
        self.assertIn("visual_opportunity", types)


class TestPlanning(unittest.TestCase):
    def setUp(self):
        self.specs = plan(understand_story(EX))

    def test_scene_graph_is_structured(self):
        s = self.specs[0]
        self.assertEqual(s.environment["environment"], "office")
        self.assertTrue(s.camera_targets)
        self.assertEqual(s.narrative["function"], "standalone")

    def test_props_are_semantic_not_assets(self):
        # the planner must NOT reference concrete assets — only queries
        for p in self.specs[0].prop_requirements:
            self.assertNotIn("id", p)
            self.assertIn("category", p)

    def test_camera_has_establishing_and_closeup(self):
        types = {c["type"] for c in self.specs[0].camera_targets}
        self.assertIn("establishing", types)
        self.assertIn("close_up", types)

    def test_validation_passes(self):
        self.assertEqual(self.specs[0].validation["status"], "valid")

    def test_invalid_scene_is_caught(self):
        bad = SceneSpec(id="x")              # empty -> no env/camera/narrative
        issues = validate_scene_graph(bad)
        self.assertTrue(any(i["level"] == "error" for i in issues))
        self.assertEqual(bad.validation["status"], "invalid")

    def test_emotion_curve_per_scene(self):
        u = understand_story("Ann was happy.\nLater, Ann was sad.")
        curve = infer_emotion_curve(u)
        self.assertEqual(len(curve), u.scene_count)


class TestCorpusScale(unittest.TestCase):
    def test_all_genres_understood_and_valid(self):
        for script in corpus.all_samples():
            u = understand_story(script)
            specs = plan(u)
            self.assertTrue(specs)
            for s in specs:
                self.assertEqual(s.validation["status"], "valid")

    def test_hundreds_of_synthetic_stories(self):
        scripts = corpus.generate(300, seed=1)
        t0 = time.time()
        valid = 0
        for sc in scripts:
            specs = plan(understand_story(sc))
            valid += all(s.validation["status"] == "valid" for s in specs)
        elapsed = time.time() - t0
        self.assertEqual(valid, len(scripts))           # every story validates
        self.assertLess(elapsed, 10.0)                  # generous CI bound


if __name__ == "__main__":
    unittest.main()
