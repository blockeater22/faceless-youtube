"""Tests for the Acting Engine: emotional state machine + performance compiler."""
import unittest

from stickforge.acting.emotion import EMOTIONS, get_emotion
from stickforge.acting.performance import Beat, compile_performance, emotion_clip
from stickforge.expression.expression import NEUTRAL
from stickforge.render.config import RenderConfig
from stickforge.render.illustrated import IllustratedRenderer
from stickforge.studio import build_silent_story, build_emotion_board


class TestEmotionMachine(unittest.TestCase):
    def test_core_emotions_present(self):
        for e in ("happy", "excited", "nervous", "confident", "embarrassed",
                  "curious", "confused", "suspicious", "shocked", "angry",
                  "frustrated", "sad", "hopeful", "determined", "relieved",
                  "anxious"):
            self.assertIn(e, EMOTIONS)

    def test_emotion_affects_body_and_eyes(self):
        sad = get_emotion("sad")
        excited = get_emotion("excited")
        self.assertNotEqual(sad.body_pose(), excited.body_pose())  # posture differs
        # sad looks down, hopeful looks up — eyes carry intention
        self.assertGreater(sad.face()["pupil_y"], 0)               # down
        self.assertLess(get_emotion("hopeful").face()["pupil_y"], 0)  # up

    def test_face_is_complete(self):
        f = get_emotion("angry").face()
        self.assertEqual(set(f), set(NEUTRAL))

    def test_poses_read_without_face(self):
        # every emotion must change the body from a plain stand (silhouette read)
        from stickforge.pose.pose import get_pose
        stand = get_pose("stand")
        changed = sum(1 for e in EMOTIONS.names()
                      if get_emotion(e).body_pose() != stand)
        self.assertGreaterEqual(changed, len(EMOTIONS) - 2)


class TestPerformance(unittest.TestCase):
    def test_compile_produces_clip(self):
        clip = compile_performance([Beat("happy", 1.0), Beat("sad", 1.0)])
        self.assertGreater(clip.duration, 1.5)
        self.assertTrue(clip.pose_keys and clip.expr_keys and clip.hand_keys)

    def test_think_beat_is_a_held_pause(self):
        clip = compile_performance([Beat("neutral", 0.5),
                                    Beat("confused", 1.2, "think", look=(0.3, -0.5)),
                                    Beat("shocked", 1.0, "react")])
        # during the think beat the eyes drift up (intention before action)
        mid = clip.sample(0.5 + 0.6)
        self.assertLess(mid.expr["pupil_y"], 0)

    def test_react_uses_anticipation(self):
        clip = compile_performance([Beat("neutral", 0.5),
                                    Beat("shocked", 1.0, "react")])
        eases = {k.get("ease") for k in clip.pose_keys}
        self.assertIn("anticipate", eases)

    def test_emotion_clip_loops_and_holds(self):
        clip = emotion_clip("confident", dur=2.0)
        self.assertTrue(clip.loop)
        self.assertEqual(clip.sample(0.0).pose, clip.sample(2.0).pose)


class TestActingScenes(unittest.TestCase):
    def test_silent_story_renders(self):
        scene = build_silent_story()
        self.assertGreater(scene.duration, 3.0)
        svg = IllustratedRenderer(RenderConfig.for_format("preview")).render_frame(scene, 4.5, 108)
        self.assertIn("</svg>", svg)

    def test_emotion_board_builds(self):
        self.assertGreaterEqual(len(build_emotion_board().actors), 10)


if __name__ == "__main__":
    unittest.main()
