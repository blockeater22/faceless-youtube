"""Tests for the asset library and pack loading."""
import unittest

from stickforge.assets.base import Asset
from stickforge.assets.library import AssetLibrary
from stickforge.assets.pack import AssetPack, load_pack, PackError
from stickforge.studio import packs_dir


def _lib():
    lib = AssetLibrary()
    lib.add(Asset("a.one", "character", "One", ["hero", "warm"]))
    lib.add(Asset("a.two", "character", "Two", ["villain", "warm"]))
    lib.add(Asset("p.wave", "pose", "Wave", ["greeting"]))
    return lib


class TestAsset(unittest.TestCase):
    def test_tag_normalization(self):
        a = Asset("x", "pose", tags=["Hero", "hero", " WARM "])
        self.assertEqual(a.tags, ["hero", "warm"])
        self.assertEqual(a.name, "x")  # defaults to id

    def test_roundtrip(self):
        a = Asset("x", "pose", "X", ["t"], {"k": 1})
        self.assertEqual(Asset.from_dict(a.to_dict()).data, {"k": 1})


class TestLibrary(unittest.TestCase):
    def test_indexing_and_dup(self):
        lib = _lib()
        self.assertEqual(len(lib), 3)
        self.assertEqual(len(lib.of_type("character")), 2)
        self.assertIn("pose", lib.types())
        with self.assertRaises(ValueError):
            lib.add(Asset("a.one", "character"))

    def test_search_tag_type_text(self):
        lib = _lib()
        self.assertEqual({a.id for a in lib.search(tags=["warm"])},
                         {"a.one", "a.two"})
        self.assertEqual([a.id for a in lib.search(type="pose")], ["p.wave"])
        hits = lib.search("two")
        self.assertEqual(hits[0].id, "a.two")
        self.assertEqual(lib.search("nomatch"), [])


class TestPack(unittest.TestCase):
    def test_load_core_pack(self):
        pack = load_pack(packs_dir() / "core.json")
        self.assertEqual(pack.id, "core")
        ids = {a.id for a in pack.assets}
        self.assertIn("char.classic", ids)
        self.assertIn("clip.wave_hello", ids)

    def test_duplicate_id_rejected(self, ):
        import json
        import tempfile
        from pathlib import Path
        bad = {"id": "p", "assets": [{"id": "x", "type": "pose"},
                                     {"id": "x", "type": "pose"}]}
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "bad.json"
            f.write_text(json.dumps(bad))
            with self.assertRaises(PackError):
                load_pack(f)

    def test_save_roundtrip(self):
        import tempfile
        from pathlib import Path
        pack = AssetPack("p", "1.0.0", assets=[Asset("x", "pose", data={"a": 1})])
        with tempfile.TemporaryDirectory() as td:
            f = pack.save(Path(td) / "p.json")
            again = load_pack(f)
            self.assertEqual(again.assets[0].data, {"a": 1})


if __name__ == "__main__":
    unittest.main()
