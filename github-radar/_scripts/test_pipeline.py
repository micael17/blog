import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import pipeline


def _hn(repo, score=200, title="ai tool"):
    return {"source": "hacker_news", "repo": repo, "score": score,
            "comments": 10, "title": title, "hn_url": "http://hn"}


class TestPassesFilters(unittest.TestCase):
    def test_archived_rejected(self):
        self.assertFalse(pipeline.passes_filters(
            {"archived": True, "is_fork": False, "stars": 1000}))

    def test_fork_rejected(self):
        self.assertFalse(pipeline.passes_filters(
            {"archived": False, "is_fork": True, "stars": 1000}))

    def test_low_stars_rejected(self):
        self.assertFalse(pipeline.passes_filters(
            {"archived": False, "is_fork": False, "stars": 30}))

    def test_qualified_passes(self):
        self.assertTrue(pipeline.passes_filters(
            {"archived": False, "is_fork": False, "stars": 100}))


class TestPipelineMain(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self._old_root = pipeline.GITHUB_RADAR_ROOT
        self._old_state = pipeline.STATE_FILE
        pipeline.GITHUB_RADAR_ROOT = self.tmpdir
        pipeline.STATE_FILE = os.path.join(self.tmpdir, "_state", "covered.json")

    def tearDown(self):
        pipeline.GITHUB_RADAR_ROOT = self._old_root
        pipeline.STATE_FILE = self._old_state

    @patch("pipeline.collect_all")
    def test_no_candidates_above_threshold(self, mock_collect):
        mock_collect.return_value = {"hn": [_hn("a/b", score=10)], "reddit": []}
        with patch("sys.argv", ["pipeline.py", "--dry-run"]):
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = pipeline.main()
        self.assertEqual(rc, 0)
        self.assertIn("No candidates above threshold", buf.getvalue())

    @patch("pipeline.generate_article")
    @patch("pipeline.enrich")
    @patch("pipeline.collect_all")
    def test_dry_run_does_not_write_files(self, mock_collect, mock_enrich, mock_generate):
        mock_collect.return_value = {"hn": [_hn("a/b", score=300, title="ai tool")],
                                     "reddit": []}
        mock_enrich.return_value = {"full_name": "a/b", "stars": 100,
                                    "is_fork": False, "archived": False, "readme": "x",
                                    "html_url": "http://gh/a/b", "language": "Python",
                                    "license": "MIT"}
        mock_generate.return_value = "# title\n\nbody"
        with patch("sys.argv", ["pipeline.py", "--dry-run"]):
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = pipeline.main()
        self.assertEqual(rc, 0)
        post_folders = [d for d in os.listdir(self.tmpdir)
                        if d.startswith("a-b-")]
        self.assertEqual(post_folders, [])

    @patch("pipeline.generate_article")
    @patch("pipeline.enrich")
    @patch("pipeline.collect_all")
    def test_archived_repo_filtered_out(self, mock_collect, mock_enrich, mock_generate):
        mock_collect.return_value = {"hn": [_hn("a/b", score=300, title="ai tool")],
                                     "reddit": []}
        mock_enrich.return_value = {"full_name": "a/b", "stars": 1000,
                                    "is_fork": False, "archived": True, "readme": "x",
                                    "html_url": "http://gh", "language": "Py",
                                    "license": "MIT"}
        with patch("sys.argv", ["pipeline.py", "--dry-run"]):
            buf = io.StringIO()
            with redirect_stdout(buf):
                pipeline.main()
        mock_generate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
