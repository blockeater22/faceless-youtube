"""Tests for the pure core: geometry, easing, keyframes, registry."""
import math
import unittest

from stickforge.core.geometry import Vec2, polar, angle_between
from stickforge.core import easing
from stickforge.core.keyframe import Track, Keyframe, sample_track, lerp_angle
from stickforge.core.registry import Registry, RegistryError


class TestGeometry(unittest.TestCase):
    def test_polar_directions(self):
        o = Vec2(0, 0)
        up, right, down = polar(o, 1, 0), polar(o, 1, 90), polar(o, 1, 180)
        self.assertAlmostEqual(up.y, -1, places=5)
        self.assertAlmostEqual(right.x, 1, places=5)
        self.assertAlmostEqual(down.y, 1, places=5)

    def test_arithmetic_and_lerp(self):
        a, b = Vec2(0, 0), Vec2(2, 4)
        self.assertEqual((a + b).as_tuple(), (2, 4))
        self.assertEqual((b * 0.5).as_tuple(), (1, 2))
        self.assertEqual(a.lerp(b, 0.5).as_tuple(), (1, 2))

    def test_rotate_and_angle_between(self):
        v = Vec2(0, -1)  # up
        r = v.rotated(90)  # clockwise -> right
        self.assertAlmostEqual(r.x, 1, places=5)
        self.assertAlmostEqual(angle_between(Vec2(0, 0), Vec2(1, 0)), 90, places=4)


class TestEasing(unittest.TestCase):
    def test_endpoints_and_bounds(self):
        for name in ("linear", "ease", "ease_in", "ease_out", "pop", "bounce"):
            fn = easing.get(name)
            self.assertAlmostEqual(fn(0.0), 0.0, places=6)
            self.assertAlmostEqual(fn(1.0), 1.0, places=6)

    def test_resolve_callable_and_default(self):
        self.assertIs(easing.get(None), easing.ease_in_out)
        f = lambda t: t
        self.assertIs(easing.get(f), f)
        with self.assertRaises(RegistryError):
            easing.get("nope")


class TestKeyframe(unittest.TestCase):
    def test_sample_endpoints_and_mid(self):
        tr = Track("x", [Keyframe(0, 0.0, "linear"), Keyframe(1, 10.0, "linear")])
        self.assertEqual(sample_track(tr, -1), 0.0)
        self.assertEqual(sample_track(tr, 2), 10.0)
        self.assertAlmostEqual(sample_track(tr, 0.5), 5.0)

    def test_angle_shortest_arc(self):
        self.assertAlmostEqual(lerp_angle(350, 10, 0.5) % 360, 0.0, places=5)

    def test_step_and_vec(self):
        tr = Track("s", [Keyframe(0, 1.0), Keyframe(1, 9.0)], interp="step")
        self.assertEqual(sample_track(tr, 0.5), 1.0)
        tv = Track("v", [Keyframe(0, [0, 0]), Keyframe(1, [2, 4])], interp="vec")
        self.assertEqual(sample_track(tv, 0.5), [1.0, 2.0])


class TestRegistry(unittest.TestCase):
    def test_register_get_decorator(self):
        r: Registry = Registry("thing")
        r.register("a", 1)

        @r.register("b")
        def b():
            return 2

        self.assertEqual(r.get("a"), 1)
        self.assertIn("b", r)
        self.assertEqual(sorted(r.names()), ["a", "b"])

    def test_duplicate_and_unknown(self):
        r: Registry = Registry("thing")
        r.register("a", 1)
        with self.assertRaises(RegistryError):
            r.register("a", 2)
        r.register("a", 3, overwrite=True)
        self.assertEqual(r.get("a"), 3)
        with self.assertRaises(RegistryError):
            r.get("missing")


if __name__ == "__main__":
    unittest.main()
