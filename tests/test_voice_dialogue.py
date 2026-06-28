"""Tests for voice/lip-sync and multi-character dialogue staging."""
import unittest

from stickforge.voice.lipsync import visemes_for
from stickforge.voice.engine import say, estimate_duration, VOICES
from stickforge.story.dialogue import parse_dialogue, stage_dialogue
from stickforge.render.config import RenderConfig
from stickforge.render.illustrated import IllustratedRenderer


class TestLipSync(unittest.TestCase):
    def test_visemes_within_duration_and_open(self):
        vis = visemes_for("Hello there friend", 2.0)
        self.assertTrue(vis)
        self.assertTrue(all(0 <= t <= 2.0 for t, _, _ in vis))
        self.assertGreater(max(mo for _, mo, _ in vis), 0.3)   # mouth opens
        self.assertLess(min(mo for _, mo, _ in vis), 0.1)      # and closes

    def test_more_words_more_visemes(self):
        short = visemes_for("Hi", 2.0)
        long = visemes_for("This is a much longer spoken sentence", 2.0)
        self.assertGreater(len(long), len(short))

    def test_empty_duration(self):
        self.assertEqual(visemes_for("hi", 0), [])


class TestVoiceEngine(unittest.TestCase):
    def test_silent_backend_times_text(self):
        clip = say("one two three four")
        self.assertIsNone(clip.audio)
        self.assertGreater(clip.duration, 0.7)
        self.assertIn("silent", VOICES)

    def test_duration_scales_with_words(self):
        self.assertGreater(estimate_duration("a b c d e f"), estimate_duration("a"))


class TestDialogue(unittest.TestCase):
    def test_parse_speakers_and_narration(self):
        d = parse_dialogue("(night falls)\nALEX: Hi!\nSAM: Hello.")
        self.assertIsNone(d[0][0])
        self.assertEqual(d[1][0], "ALEX")
        self.assertEqual(d[2][0], "SAM")

    def test_stage_builds_synced_actors(self):
        scene = stage_dialogue("ALEX: Hey.\nSAM: Hi.",
                               {"ALEX": "actor.nova", "SAM": "actor.rex"})
        self.assertEqual(len(scene.actors), 2)
        # actors face each other and stay in sync (same duration)
        facings = {a.facing for a in scene.actors}
        self.assertEqual(facings, {1, -1})
        self.assertAlmostEqual(scene.actors[0].clip.duration,
                               scene.actors[1].clip.duration, places=3)
        # speaker labels appear in subtitles
        self.assertTrue(any("ALEX:" in s["text"] for s in scene.subtitles))

    def test_eye_contact_gaze_set(self):
        scene = stage_dialogue("ALEX: Look!\nSAM: What?",
                               {"ALEX": "actor.nova", "SAM": "actor.rex"})
        # at t=0 both look toward centre (positive local pupil_x)
        for a in scene.actors:
            self.assertGreater(a.clip.sample(0.2).expr["pupil_x"], 0.0)

    def test_renders(self):
        scene = stage_dialogue("ALEX: Hey.\nSAM: Hi.",
                               {"ALEX": "actor.nova", "SAM": "actor.rex"})
        svg = IllustratedRenderer(RenderConfig.for_format("preview")).render_frame(scene, 0.4, 9)
        self.assertIn("</svg>", svg)


if __name__ == "__main__":
    unittest.main()
