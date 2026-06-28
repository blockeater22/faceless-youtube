"""Tests for rig FK, poses, expressions, animation clips, procedural life."""
import math
import unittest

from stickforge.character.skeleton import default_humanoid
from stickforge.character.character import build_character
from stickforge.core.geometry import Vec2
from stickforge.pose.pose import get_pose, blend_pose, POSES
from stickforge.expression.expression import get_expression, blend_expression, NEUTRAL
from stickforge.animation.clip import AnimationClip
from stickforge.animation.procedural import apply_life, blink_amount, phase_for


class TestSkeleton(unittest.TestCase):
    def setUp(self):
        self.sk = default_humanoid()

    def test_spine_length_and_head(self):
        solved = self.sk.solve(Vec2(0, 0), 100.0, {})
        spine = solved["spine"]
        self.assertAlmostEqual((spine.end - spine.start).length(), 34.0, places=3)
        self.assertIsNotNone(self.sk.head(solved))

    def test_lean_carries_arm(self):
        base = self.sk.solve(Vec2(0, 0), 100.0, {})
        leaned = self.sk.solve(Vec2(0, 0), 100.0, {"spine": 20})
        d = leaned["upper_arm_l"].world_angle - base["upper_arm_l"].world_angle
        self.assertAlmostEqual(d, 20.0, places=3)  # child inherits parent rotation

    def test_attach_points(self):
        solved = self.sk.solve(Vec2(0, 0), 100.0, {})
        # arms attach at spine tip (shoulder); legs at spine base (hip = root)
        self.assertAlmostEqual(
            (solved["upper_arm_l"].start - solved["spine"].end).length(), 0, places=3)
        self.assertAlmostEqual(
            (solved["thigh_l"].start - solved["spine"].start).length(), 0, places=3)


class TestPose(unittest.TestCase):
    def test_builtins_present(self):
        for name in ("stand", "wave", "think", "walk_a", "celebrate"):
            self.assertIn(name, POSES)

    def test_blend_midpoint(self):
        out = blend_pose({"head": 0}, {"head": 20}, 0.5)
        self.assertAlmostEqual(out["head"], 10.0)

    def test_passthrough_dict(self):
        self.assertEqual(get_pose({"x": 1}), {"x": 1})


class TestExpression(unittest.TestCase):
    def test_merge_over_neutral(self):
        e = get_expression("happy")
        self.assertEqual(set(e), set(NEUTRAL))
        self.assertGreater(e["mouth_curve"], 0.5)

    def test_blend(self):
        m = blend_expression(get_expression("neutral"),
                             get_expression("happy"), 0.5)
        self.assertAlmostEqual(m["mouth_curve"],
                               get_expression("happy")["mouth_curve"] / 2, places=4)


class TestClip(unittest.TestCase):
    def test_sample_endpoints_and_mid(self):
        clip = AnimationClip.from_spec({
            "duration": 2.0,
            "poses": [{"t": 0, "pose": "stand"}, {"t": 2, "pose": "wave"}],
            "expressions": [{"t": 0, "expr": "neutral"}, {"t": 2, "expr": "happy"}],
            "offset": [{"t": 0, "value": [0, 0]}, {"t": 2, "value": [1, 0]}],
        })
        start, mid, end = clip.sample(0), clip.sample(1), clip.sample(2)
        self.assertEqual(start.offset.x, 0.0)
        self.assertEqual(end.offset.x, 1.0)
        self.assertTrue(0 < mid.offset.x < 1)
        self.assertGreater(end.expr["mouth_curve"], start.expr["mouth_curve"])

    def test_loop_wraps(self):
        clip = AnimationClip.from_spec({
            "duration": 2.0, "loop": True,
            "poses": [{"t": 0, "pose": "stand"}, {"t": 2, "pose": "wave"}]})
        # t=2.0 wraps to 0.0 under loop
        self.assertEqual(clip.sample(2.0).pose, clip.sample(0.0).pose)


class TestProcedural(unittest.TestCase):
    def test_blink_range(self):
        vals = [blink_amount(t / 100, 0.0) for t in range(400)]
        self.assertTrue(all(0 <= v <= 1 for v in vals))
        self.assertGreater(max(vals), 0.5)  # blinks actually happen

    def test_apply_life_changes_pose(self):
        clip = AnimationClip.from_spec({"duration": 1, "poses": [{"t": 0, "pose": "stand"}]})
        base = clip.sample(0.3)
        lived = apply_life(base, 0.3, phase_for("x"), 1.0)
        self.assertIn("spine", lived.pose)
        # life=0 is a no-op
        self.assertIs(apply_life(base, 0.3, 0.0, 0.0), base)


class TestCharacter(unittest.TestCase):
    def test_build_from_dict(self):
        c = build_character({"id": "z", "ink": "#fff", "attachments": [{"type": "bowtie"}]})
        self.assertEqual(c.id, "z")
        self.assertEqual(len(c.attachments), 1)
        self.assertGreater(c.head_radius, 0)


if __name__ == "__main__":
    unittest.main()
