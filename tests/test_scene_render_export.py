"""Tests for scene assembly, the SVG renderer, and exporters."""
import tempfile
import unittest
from pathlib import Path

from stickforge.render.config import RenderConfig
from stickforge.render.svg import SvgRenderer
from stickforge.scene.scene import Scene, Timeline
from stickforge.export.frames import render_frames, write_svg_frames
from stickforge.export.html import write_html_player
from stickforge.studio import load_core_library, build_demo_timeline, build_expression_showcase


class TestScene(unittest.TestCase):
    def test_from_spec_with_library(self):
        lib = load_core_library()
        scene = Scene.from_spec({
            "id": "s", "duration": 2.0,
            "actors": [{"id": "a", "character": "char.classic",
                        "clip_id": "clip.wave_hello"}],
        }, lib)
        self.assertEqual(len(scene.actors), 1)
        self.assertEqual(scene.actors[0].character.id, "char.classic")
        posing = scene.actors[0].posing_at(0.5)
        self.assertIn("upper_arm_r", posing.pose)

    def test_timeline_at(self):
        s1, s2 = Scene(id="a", duration=1.0), Scene(id="b", duration=2.0)
        tl = Timeline([s1, s2])
        self.assertEqual(tl.duration, 3.0)
        self.assertIs(tl.at(0.5)[0], s1)
        scene, local = tl.at(1.5)
        self.assertIs(scene, s2)
        self.assertAlmostEqual(local, 0.5)


class TestRenderer(unittest.TestCase):
    def test_render_frame_is_valid_svg(self):
        lib = load_core_library()
        scene = Scene.from_spec({
            "id": "s", "duration": 1.0, "background": {"type": "night"},
            "caption": "hello",
            "actors": [{"id": "a", "character": "char.amber",
                        "clip_id": "clip.wave_hello"}],
        }, lib)
        svg = SvgRenderer(RenderConfig.for_format("preview")).render_frame(scene, 0.4, 3)
        self.assertTrue(svg.startswith("<svg"))
        self.assertIn("</svg>", svg)
        self.assertIn("<path", svg)        # figure strokes
        self.assertIn("hello", svg)        # caption text

    def test_demo_renders_all_frames(self):
        tl = build_demo_timeline()
        frames = render_frames(tl, RenderConfig.for_format("preview"), fps=6)
        self.assertEqual(len(frames), max(1, int(round(tl.duration * 6))))
        self.assertTrue(all(f.endswith("</svg>") for f in frames))

    def test_showcase_renders(self):
        scene = build_expression_showcase()
        svg = SvgRenderer(RenderConfig.for_format("16:9")).render_frame(scene, 0.0)
        self.assertIn("happy", svg)        # an expression label prop


class TestExport(unittest.TestCase):
    def test_html_player_and_svg_frames(self):
        frames = render_frames(build_demo_timeline(),
                               RenderConfig.for_format("preview"), fps=4)
        with tempfile.TemporaryDirectory() as td:
            html = write_html_player(frames, Path(td) / "p.html", fps=4, title="t")
            text = html.read_text()
            self.assertIn("FRAMES", text)
            self.assertIn("requestAnimationFrame", text)
            paths = write_svg_frames(frames[:3], Path(td) / "frames")
            self.assertEqual(len(paths), 3)
            self.assertTrue(paths[0].exists())


if __name__ == "__main__":
    unittest.main()
