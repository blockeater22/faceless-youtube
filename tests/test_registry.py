"""Tests for the Asset Intelligence Engine (semantic asset registry)."""
import time
import unittest

from stickforge.registry import (AssetMeta, AssetRegistry, Query, parse_query,
                                 default_registry, validate_meta, Placement)
from stickforge.registry.validate import errors
from stickforge.registry.synthetic import generate


class TestSchema(unittest.TestCase):
    def test_roundtrip_and_forward_compat(self):
        d = {"id": "p:furniture.chair", "category": "furniture",
             "styles": ["Modern"], "future_field": {"x": 1}}
        m = AssetMeta.from_dict(d)
        self.assertEqual(m.styles, ["modern"])           # normalized
        self.assertEqual(m.extra["future_field"], {"x": 1})  # preserved
        self.assertIn("future_field", m.to_dict())       # round-trips

    def test_name_derived_from_id(self):
        self.assertEqual(AssetMeta("p:furniture.office_desk").name, "Office Desk")


class TestValidation(unittest.TestCase):
    def test_errors_and_warnings(self):
        bad = AssetMeta("nonamespace", category="furniture")
        self.assertTrue(errors(validate_meta(bad)))      # id error
        warn = AssetMeta("p:furniture.x", category="furniture", styles=["zzz"])
        levels = {i.level for i in validate_meta(warn)}
        self.assertIn("warning", levels)                 # unknown style warns
        self.assertFalse(errors(validate_meta(warn)))    # but no errors

    def test_bbox_and_quality(self):
        self.assertTrue(errors(validate_meta(AssetMeta("p:f.x", category="furniture", bbox=[1]))))
        self.assertTrue(errors(validate_meta(AssetMeta("p:f.x", category="furniture", quality_score=99))))


class TestSemanticQuery(unittest.TestCase):
    def setUp(self):
        self.reg = default_registry()

    def test_world_pack_loaded(self):
        self.assertGreaterEqual(len(self.reg), 12)

    def test_queries_rank_correctly(self):
        self.assertEqual(self.reg.find_assets("cozy sofa for a living room", 1)[0].id,
                         "world:furniture.sofa_cozy")
        self.assertEqual(self.reg.find_assets("modern office chair", 1)[0].id,
                         "world:furniture.office_chair_modern")
        self.assertEqual(self.reg.find_assets("wooden dining table", 1)[0].id,
                         "world:furniture.dining_table")
        self.assertEqual(self.reg.find_assets("rainy office window", 1)[0].id,
                         "world:architecture.office_window")

    def test_parse_query_facets(self):
        q = parse_query("a modern wooden chair for the office")
        self.assertIn("modern", q.styles)
        self.assertIn("wood", q.materials)
        self.assertIn("office", q.environments)

    def test_no_filenames_anywhere(self):
        # access is purely by semantic id; metas carry no path field
        self.assertFalse(any(hasattr(m, "path") or hasattr(m, "filename")
                             for m in self.reg.all()))


class TestRelationshipsVariantsAnchors(unittest.TestCase):
    def setUp(self):
        self.reg = default_registry()

    def test_supports_and_inverse(self):
        self.assertIn("laptop", self.reg.supports("world:furniture.office_desk"))
        self.assertIn("world:furniture.office_desk", self.reg.hosts_for("laptop"))

    def test_variants_and_choice(self):
        v = self.reg.find_variants("chair.office")
        self.assertEqual(len(v), 2)
        self.assertEqual(self.reg.choose_variant("chair.office", "modern").id,
                         "world:furniture.office_chair_modern")

    def test_anchors_and_interactions(self):
        self.assertEqual(self.reg.anchor("world:furniture.office_desk", "top"), [0, -0.5])
        self.assertEqual(self.reg.interaction("world:architecture.office_door", "handle"),
                         [0.35, 0.1])

    def test_suggest_replacements(self):
        subs = self.reg.suggest_replacements("world:furniture.office_chair_classic")
        ids = {m.id for m in subs}
        self.assertIn("world:furniture.office_chair_modern", ids)
        self.assertNotIn("world:furniture.office_chair_classic", ids)


class TestConstraints(unittest.TestCase):
    def setUp(self):
        self.reg = default_registry()

    def test_bad_surface_rejected(self):
        issues = self.reg.validate_scene(
            [Placement("world:decoration.painting", "floor")])
        self.assertTrue(errors(issues))

    def test_valid_surface_ok(self):
        issues = self.reg.validate_scene(
            [Placement("world:decoration.painting", "wall")])
        self.assertFalse(errors(issues))

    def test_style_mixing_warns(self):
        m = AssetMeta("world:prop.dragon", category="decoration",
                      styles=["fantasy"], placement={"surface": "floor"})
        self.reg.add(m)
        issues = self.reg.validate_scene(
            [Placement("world:furniture.office_desk", "floor"),
             Placement("world:prop.dragon", "floor")])
        self.assertTrue(any(i.field == "style" for i in issues))


class TestScale(unittest.TestCase):
    def test_indexes_and_queries_at_scale(self):
        reg = AssetRegistry()
        metas = generate(5000, seed=2)
        t0 = time.time()
        for m in metas:
            reg.add(m, strict=False)
        self.assertEqual(len(reg), 5000)
        # a query stays index-narrowed and fast
        t0 = time.time()
        res = reg.find_assets("modern wooden furniture for office", limit=10)
        elapsed = time.time() - t0
        self.assertLessEqual(len(res), 10)
        self.assertLess(elapsed, 1.0)                    # generous CI bound
        self.assertTrue(reg.find_by_style("modern"))     # facet index works


if __name__ == "__main__":
    unittest.main()
