"""Tests for the spatial foundation: transform, world, camera, nodes, graph."""
import unittest

from stickforge.core.geometry import Vec2
from stickforge.stage import (Transform2D, Camera2D, Viewport, World, REFERENCE,
                              SceneNode, SceneGraph, Layer)
from stickforge.stage.layers import PARALLAX


class TestTransform(unittest.TestCase):
    def test_translate_scale(self):
        self.assertEqual(Transform2D.translate(3, 4).apply(Vec2(1, 1)).as_tuple(), (4, 5))
        self.assertEqual(Transform2D.scale(2).apply(Vec2(1, 1)).as_tuple(), (2, 2))

    def test_compose_applies_child_first(self):
        parent = Transform2D.translate(10, 0)
        child = Transform2D.scale(2)
        w = parent @ child                       # scale then translate
        self.assertEqual(w.apply(Vec2(1, 1)).as_tuple(), (12, 2))

    def test_inverse_roundtrip(self):
        t = Transform2D.translate(5, -3) @ Transform2D.scale(2, 3)
        p = Vec2(7, 9)
        back = t.inverse().apply(t.apply(p))
        self.assertAlmostEqual(back.x, 7, places=5)
        self.assertAlmostEqual(back.y, 9, places=5)

    def test_rotate_clockwise(self):
        r = Transform2D.rotate(90).apply(Vec2(1, 0))
        self.assertAlmostEqual(r.x, 0, places=5)
        self.assertAlmostEqual(r.y, 1, places=5)


class TestCameraWorld(unittest.TestCase):
    def setUp(self):
        self.vp = Viewport(1920, 1080)

    def test_project_unproject_roundtrip(self):
        cam = Camera2D(center=Vec2(40, -20), zoom=1.3)
        p = Vec2(123, -45)
        s = cam.project(p, self.vp, 1.0)
        back = cam.unproject(s, self.vp, 1.0)
        self.assertAlmostEqual(back.x, 123, places=4)
        self.assertAlmostEqual(back.y, -45, places=4)

    def test_world_origin_maps_to_screen_centre(self):
        s = Camera2D().project(Vec2(0, 0), self.vp, 1.0)
        self.assertAlmostEqual(s.x, 960, places=3)
        self.assertAlmostEqual(s.y, 540, places=3)

    def test_zoom_scales_distance(self):
        far = Camera2D(zoom=1.0).project(Vec2(100, 0), self.vp).x
        near = Camera2D(zoom=2.0).project(Vec2(100, 0), self.vp).x
        self.assertGreater(near - 960, (far - 960) * 1.9)   # ~2x further out

    def test_parallax_reduces_camera_response(self):
        cam = Camera2D(center=Vec2(200, 0))
        near = cam.project(Vec2(0, 0), self.vp, 1.0).x
        far = cam.project(Vec2(0, 0), self.vp, 0.2).x
        # a far layer shifts less from rest (960) when the camera pans
        self.assertLess(abs(far - 960), abs(near - 960))

    def test_frac_to_world_centre(self):
        w = World.frac_to_world(0.5, 0.5, self.vp)
        self.assertAlmostEqual(w.x, 0, places=5)
        self.assertAlmostEqual(w.y, 0, places=5)


class TestNodesGraph(unittest.TestCase):
    def test_world_transform_and_anchor(self):
        root = SceneNode("root", Transform2D.translate(100, 0))
        child = SceneNode("child", Transform2D.translate(0, 50),
                          anchors={"tip": Vec2(0, -10)})
        root.add(child)
        self.assertEqual(child.world_pos().as_tuple(), (100, 50))
        self.assertEqual(child.anchor("tip").as_tuple(), (100, 40))

    def test_effective_parallax_from_layer(self):
        n = SceneNode("bg", layer=Layer.FAR)
        self.assertEqual(n.effective_parallax, PARALLAX[Layer.FAR])
        self.assertEqual(SceneNode("x", layer=Layer.FAR, parallax=0.9).effective_parallax, 0.9)

    def test_render_order_sorted_by_layer(self):
        g = SceneGraph()
        g.spawn("fg", Vec2(0, 0), Layer.FOREGROUND, content={"kind": "p"})
        g.spawn("bg", Vec2(0, 0), Layer.BACKGROUND, content={"kind": "p"})
        g.spawn("act", Vec2(0, 0), Layer.ACTORS, content={"kind": "p"})
        order = [n.name for n in g.renderables()]
        self.assertEqual(order, ["bg", "act", "fg"])

    def test_graph_find_and_anchor(self):
        g = SceneGraph()
        g.spawn("hero", Vec2(10, 20), Layer.ACTORS,
                content={"kind": "a"}, anchors={"hand": Vec2(5, 0)})
        self.assertIsNotNone(g.find("hero"))
        self.assertEqual(g.anchor("hero", "hand").as_tuple(), (15, 20))


class TestRendererBridge(unittest.TestCase):
    def test_build_graph_places_actor_in_world(self):
        from stickforge.render.illustrated import IllustratedRenderer
        from stickforge.scene.scene import Scene, Actor
        from stickforge.character.character import build_character
        from stickforge.animation.clip import AnimationClip
        clip = AnimationClip.from_spec({"duration": 1, "poses": [{"t": 0, "pose": "stand"}]})
        a = Actor(character=build_character({"id": "h"}), clip=clip,
                  pos=(0.5, 0.5), unit_scale=0.34, id="h")
        scene = Scene(id="s", duration=1, actors=[a])
        vp = Viewport(1080, 1920)
        g = IllustratedRenderer().build_graph(scene, vp)
        node = g.find("h")
        self.assertEqual(node.world_pos().as_tuple(), (0.0, 0.0))   # centre -> origin
        self.assertEqual(node.layer, Layer.ACTORS)


if __name__ == "__main__":
    unittest.main()
