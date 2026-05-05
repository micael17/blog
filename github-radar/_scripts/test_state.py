import json
import os
import tempfile
import unittest
from datetime import date, timedelta

from state import load_covered, save_covered, is_covered, mark_covered


class TestState(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.path = os.path.join(self.tmpdir, "covered.json")

    def test_load_missing_file_returns_empty(self):
        self.assertEqual(load_covered(self.path), {})

    def test_save_creates_parent_dir(self):
        nested = os.path.join(self.tmpdir, "_state", "covered.json")
        save_covered({"a/b": "2026-01-01"}, nested)
        self.assertTrue(os.path.exists(nested))

    def test_save_and_load_roundtrip(self):
        save_covered({"a/b": "2026-01-01", "c/d": "2026-02-02"}, self.path)
        self.assertEqual(load_covered(self.path),
                         {"a/b": "2026-01-01", "c/d": "2026-02-02"})

    def test_save_is_atomic(self):
        save_covered({"a/b": "2026-01-01"}, self.path)
        self.assertFalse(os.path.exists(self.path + ".tmp"))

    def test_is_covered_recent(self):
        recent = (date.today() - timedelta(days=10)).isoformat()
        self.assertTrue(is_covered("a/b", {"a/b": recent}, cooldown_days=30))

    def test_is_covered_at_cooldown_boundary(self):
        boundary = (date.today() - timedelta(days=30)).isoformat()
        self.assertFalse(is_covered("a/b", {"a/b": boundary}, cooldown_days=30))

    def test_is_covered_expired(self):
        old = (date.today() - timedelta(days=31)).isoformat()
        self.assertFalse(is_covered("a/b", {"a/b": old}, cooldown_days=30))

    def test_is_covered_not_in_db(self):
        self.assertFalse(is_covered("a/b", {}, cooldown_days=30))

    def test_mark_covered_sets_today(self):
        db = {}
        mark_covered("a/b", db)
        self.assertEqual(db["a/b"], date.today().isoformat())

    def test_mark_covered_overwrites(self):
        db = {"a/b": "2020-01-01"}
        mark_covered("a/b", db)
        self.assertEqual(db["a/b"], date.today().isoformat())

    def test_mark_covered_with_explicit_date(self):
        db = {}
        mark_covered("a/b", db, today=date(2026, 5, 5))
        self.assertEqual(db["a/b"], "2026-05-05")


if __name__ == "__main__":
    unittest.main()
