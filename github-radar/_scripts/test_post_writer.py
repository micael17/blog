import json
import os
import tempfile
import unittest
from datetime import date

from post_writer import make_slug, make_folder_name, write_post


class TestSlug(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(make_slug("aattaran/deepclaude"), "aattaran-deepclaude")

    def test_lowercase(self):
        self.assertEqual(make_slug("UpperCase/Repo"), "uppercase-repo")

    def test_preserves_dashes_and_dots(self):
        self.assertEqual(make_slug("my-org/repo.js"), "my-org-repo.js")


class TestFolderName(unittest.TestCase):
    def test_with_explicit_date(self):
        name = make_folder_name("a/b", today=date(2026, 5, 5))
        self.assertEqual(name, "a-b-20260505")

    def test_uses_today_if_no_date(self):
        name = make_folder_name("a/b")
        self.assertTrue(name.startswith("a-b-"))
        self.assertEqual(len(name), len("a-b-") + 8)


class TestWritePost(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def test_creates_folder(self):
        write_post(self.tmpdir, "abc-20260505", "# article", {"meta": "data"})
        self.assertTrue(os.path.isdir(os.path.join(self.tmpdir, "abc-20260505")))

    def test_writes_post_md(self):
        write_post(self.tmpdir, "abc-20260505", "# article body", {"meta": "data"})
        post_path = os.path.join(self.tmpdir, "abc-20260505", "post.md")
        self.assertEqual(open(post_path).read(), "# article body")

    def test_writes_source_json(self):
        write_post(self.tmpdir, "abc-20260505", "body", {"key": "value", "stars": 100})
        src_path = os.path.join(self.tmpdir, "abc-20260505", "source.json")
        loaded = json.load(open(src_path))
        self.assertEqual(loaded, {"key": "value", "stars": 100})

    def test_returns_post_dir(self):
        ret = write_post(self.tmpdir, "abc-20260505", "body", {})
        self.assertEqual(ret, os.path.join(self.tmpdir, "abc-20260505"))


if __name__ == "__main__":
    unittest.main()
