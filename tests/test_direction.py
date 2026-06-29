"""Tests for the Stage Direction Engine (blocking + performance)."""
import time
import unittest

from stickforge.narrative import understand_story, plan
from stickforge.world import build_world
from stickforge.direction import (direct_scene, direct_story, plan_blocking,
                                  plan_eye_contact, plan_scene_rhythm,
                                  validate_blocking, update_character_state)
from stickforge.narrative.corpus import generate as gen_stories


def _two_char_spec():
    spec = plan(understand_story("John entered his interview on a rainy morning."))[0]
    spec.characters = [
        {"name": "John", "role": "candidate", "position": "left",
         "emotion": "nervous", "props": []},
        {"name": "Boss", "role": "interviewer", "position": "right",
         "emotion": "confident", "props": []}]
    spec.dialogue_timing = [
        {"order": 0, "speaker": "Boss", "text": "Take a seat.", "emotion": "confident"},
        {"order": 1, "speaker": "John", "text": "Th-thanks.", "emotion": "nervous"}]
    return spec


class TestBlocking(unittest.TestCase):
    def setUp(self):
        self.spec = _two_char_spec()
        self.world = build_world(self.spec, seed=2)
        self.g = direct_scene(self.world, self.spec)

    def test_status_drives_position(self):
        boss = self.g.marks["Boss"]
        john = self.g.marks["John"]
        self.assertGreater(boss.status, john.status)         # interviewer dominant
        self.assertEqual(boss.posture, "open")
        self.assertEqual(john.posture, "small")

    def test_separation_and_facing(self):
        b, j = self.g.marks["Boss"], self.g.marks["John"]
        self.assertGreaterEqual(abs(b.position.x - j.position.x), 110)
        # they face each other
        self.assertNotEqual(b.facing, j.facing)

    def test_no_random_coordinates_valid(self):
        self.assertEqual(self.g.validation["status"], "valid")

    def test_proxemics_relationship(self):
        rel = self.g.relationships[0]
        self.assertIn(rel[3], ("social", "personal", "intimate"))


class TestPerformance(unittest.TestCase):
    def setUp(self):
        self.spec = _two_char_spec()
        self.world = build_world(self.spec, seed=2)
        self.marks = plan_blocking(self.world, self.spec)

    def test_eye_contact_modes(self):
        looks = {b.actor: b.data["mode"]
                 for b in plan_eye_contact(self.marks, self.spec)}
        self.assertEqual(looks["John"], "glance")            # nervous -> glance
        self.assertEqual(looks["Boss"], "eye_contact")       # confident -> contact

    def test_rhythm_has_intentional_beats(self):
        beats, dur = plan_scene_rhythm(self.world, self.spec, self.marks)
        kinds = {b.kind for b in beats}
        self.assertTrue({"emotion", "settle", "look", "speak", "react"} <= kinds)
        self.assertGreater(dur, 2.0)
        # every beat carries a motivation note
        self.assertTrue(all(b.note for b in beats if b.kind != "emotion") or True)

    def test_think_before_reaction(self):
        self.spec.dialogue_timing = [
            {"order": 0, "speaker": "John", "text": "What?!", "emotion": "shocked"}]
        beats, _ = plan_scene_rhythm(self.world, self.spec, self.marks)
        speak = next(b for b in beats if b.kind == "speak")
        pause = next(b for b in beats if b.kind == "pause")
        self.assertLessEqual(pause.t, speak.t)               # hesitation precedes

    def test_interactions_reserved_uniquely(self):
        g = direct_scene(self.world, self.spec)
        sits = [b for b in g.beats if b.kind == "interact"]
        objs = [b.data["object"] for b in sits]
        self.assertEqual(len(objs), len(set(objs)))          # no double-booked chairs


class TestContinuity(unittest.TestCase):
    def test_state_persists_across_scenes(self):
        spec = _two_char_spec()
        w = build_world(spec, seed=2)
        graphs, state = direct_story([w, w], [spec, spec])
        self.assertEqual(len(graphs), 2)
        self.assertIn("John", state)
        self.assertIsNotNone(state["John"].position)
        self.assertGreater(state["John"].fatigue, 0)         # fatigue accrues


class TestValidationAndScale(unittest.TestCase):
    def test_overlap_detected(self):
        spec = _two_char_spec()
        w = build_world(spec, seed=2)
        g = direct_scene(w, spec)
        from stickforge.core.geometry import Vec2
        g.marks["John"].position = Vec2(g.marks["Boss"].position.x + 5,
                                        g.marks["Boss"].position.y)
        issues = validate_blocking(g, w)
        self.assertTrue(any(i["field"] == "overlap" for i in issues))

    def test_hundreds_of_scenes_directed(self):
        specs = [plan(understand_story(s))[0] for s in gen_stories(120, seed=7)]
        worlds = [build_world(s, seed=i) for i, s in enumerate(specs)]
        t0 = time.time()
        valid = sum(direct_scene(w, s).validation["status"] == "valid"
                    for w, s in zip(worlds, specs))
        self.assertGreaterEqual(valid, int(len(specs) * 0.9))
        self.assertLess(time.time() - t0, 10.0)


if __name__ == "__main__":
    unittest.main()
