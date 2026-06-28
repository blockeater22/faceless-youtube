"""Tests for the Story Engine (script -> beats -> subtitled scene) + live idle."""
import unittest

from stickforge.story.script import parse_script, infer_emotion
from stickforge.story.engine import script_to_beats, storyboard
from stickforge.animation.clip import AnimationClip
from stickforge.animation.procedural import apply_life, phase_for


class TestScriptParsing(unittest.TestCase):
    def test_action_vs_dialogue(self):
        lines = parse_script("(a dark room)\nhappy: Hello there!")
        self.assertEqual(lines[0].kind, "action")
        self.assertEqual(lines[1].kind, "dialogue")
        self.assertEqual(lines[1].emotion, "happy")

    def test_emotion_inference(self):
        self.assertEqual(infer_emotion("No way!"), "shocked")
        self.assertEqual(infer_emotion("What is that?"), "curious")
        self.assertEqual(infer_emotion("Hmm... let me think"), "thinking")
        self.assertEqual(infer_emotion("This is amazing!"), "excited")

    def test_comments_ignored(self):
        self.assertEqual(len(parse_script("# c\n\nhi there")), 1)


class TestDirector(unittest.TestCase):
    def test_think_precedes_reactions(self):
        beats = script_to_beats(parse_script("No way!"))   # shocked reaction
        kinds = [b.kind for b in beats]
        self.assertIn("think", kinds)
        ti, ri = kinds.index("think"), kinds.index("react")
        self.assertLess(ti, ri)                            # think BEFORE react

    def test_storyboard_has_synced_subtitles(self):
        scene = storyboard("happy: One.\nexcited: Two!")
        self.assertGreater(scene.duration, 2.0)
        texts = [s["text"] for s in scene.subtitles]
        self.assertIn("One.", texts)
        self.assertIn("Two!", texts)
        # subtitle is empty before the first dialogue, set after
        self.assertEqual(scene.subtitle_at(0.0), "")
        self.assertTrue(any(scene.subtitle_at(t) == "One."
                            for t in [s["t"] + 0.1 for s in scene.subtitles]))


class TestLiveIdle(unittest.TestCase):
    def test_idle_params_flow_through_clip(self):
        clip = AnimationClip.from_spec({
            "duration": 2.0, "poses": [{"t": 0, "pose": "stand"}],
            "idle": [{"t": 0, "amp": 1.6, "blink": 2.0}]})
        p = clip.sample(0.5)
        self.assertAlmostEqual(p.idle_amp, 1.6)
        self.assertAlmostEqual(p.blink_rate, 2.0)

    def test_higher_idle_amp_moves_more(self):
        base = AnimationClip.from_spec({"duration": 1, "poses": [{"t": 0, "pose": "stand"}]})
        calm = base.sample(0.4); calm.idle_amp = 0.3
        busy = base.sample(0.4); busy.idle_amp = 2.0
        lc = apply_life(calm, 0.4, phase_for("x"), 1.0)
        lb = apply_life(busy, 0.4, phase_for("x"), 1.0)
        # the agitated one deviates further from the resting spine angle
        self.assertGreater(abs(lb.pose["spine"]), abs(lc.pose["spine"]))


if __name__ == "__main__":
    unittest.main()
