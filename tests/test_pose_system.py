"""Tests for the generative pose system: builder, scorer, and the test loop."""
import unittest

from stickforge.pose.builder import build_pose, ARM_LEFT
from stickforge.pose.score import score_pose
from stickforge.pose.pose import get_pose
from stickforge.pose import lab

_BONES = {"spine", "head", "upper_arm_l", "forearm_l", "upper_arm_r",
          "forearm_r", "thigh_l", "shin_l", "thigh_r", "shin_r"}


class TestBuilder(unittest.TestCase):
    def test_outputs_full_pose(self):
        p = build_pose(loa=10, weight=0.5, arm_l="reach", arm_r="hip")
        self.assertTrue(_BONES.issubset(set(p)))

    def test_line_of_action_sets_spine(self):
        self.assertGreater(build_pose(loa=20)["spine"], build_pose(loa=0)["spine"])

    def test_weight_shifts_support_leg(self):
        # weight on right -> right thigh near vertical (~178); on left -> left near 182
        right = build_pose(weight=1.0)
        left = build_pose(weight=-1.0)
        self.assertAlmostEqual(right["thigh_r"], 178, delta=2)
        self.assertAlmostEqual(left["thigh_l"], 182, delta=2)
        self.assertNotEqual(right["thigh_l"], left["thigh_l"])

    def test_arm_placement_mirrors(self):
        p = build_pose(arm_l="hip", arm_r="hip")
        # right is the mirror of the left placement
        self.assertAlmostEqual(p["upper_arm_r"], (360 - ARM_LEFT["hip"][0]) % 360, delta=1)


class TestScorer(unittest.TestCase):
    def test_dynamic_beats_stiff(self):
        stiff = {"upper_arm_l": 193, "forearm_l": -6, "upper_arm_r": 167,
                 "forearm_r": 6, "thigh_l": 198, "shin_l": -14,
                 "thigh_r": 162, "shin_r": 14}
        dynamic = build_pose(loa=14, weight=0.7, head=4, arm_l="reach", arm_r="hip")
        self.assertGreater(score_pose(dynamic)[0], score_pose(stiff)[0] + 1.0)

    def test_stiff_symmetric_has_no_line_of_action(self):
        stiff = {"spine": 0, "head": 0}
        self.assertEqual(score_pose(stiff)[1]["line_of_action"], 0.0)

    def test_generated_stand_is_contrapposto(self):
        # the regenerated default stand is no longer stiff/symmetric
        stand = get_pose("stand")
        self.assertNotEqual(stand.get("thigh_l"), -stand.get("thigh_r", 0))
        self.assertGreaterEqual(score_pose(stand)[0], 5.5)


class TestLab(unittest.TestCase):
    def test_loop_rejection_improves_mean(self):
        ev = lab.evaluate(100, seed=3)
        self.assertEqual(ev["n"], 100)
        self.assertGreaterEqual(ev["top_mean"], ev["all_mean"])
        self.assertLessEqual(ev["best"]["score"], 10.0)

    def test_deterministic(self):
        self.assertEqual(lab.evaluate(20, seed=5)["all_mean"],
                         lab.evaluate(20, seed=5)["all_mean"])


if __name__ == "__main__":
    unittest.main()
