"""Tests for generate.py — focused on assemble() (the function that had a production bug)."""

import unittest

from generate import assemble


def _repo():
    """Minimal enriched dict for assemble()."""
    return {
        "full_name": "owner/repo",
        "html_url": "https://github.com/owner/repo",
        "stars": 100,
        "language": "Python",
        "license": "MIT",
    }


def _ctx(hn_url="https://news.ycombinator.com/item?id=1", hn_score=100, hn_comments=5,
         reddit_posts=None):
    """Minimal social context dict for assemble()."""
    return {
        "hn_url": hn_url,
        "hn_score": hn_score,
        "hn_comments": hn_comments,
        "hn_title": "title",
        "reddit_posts": reddit_posts or [],
    }


class TestAssemble(unittest.TestCase):
    def test_normal_title_first_line(self):
        body = "## Real Title\n\n### TL;DR\n- thing\n"
        result = assemble(body, _repo(), _ctx())
        # Title preserved as first line
        self.assertTrue(result.startswith("## Real Title"))
        # Header injected after title
        self.assertIn("**원본 레포**", result)
        self.assertIn("[owner/repo](https://github.com/owner/repo)", result)
        # Body preserved
        self.assertIn("### TL;DR", result)
        # Footer appended
        self.assertIn("### 참고 및 출처", result)

    def test_pre_title_garbage_stripped(self):
        """Regression for ★ Insight leak — model output has Insight block before title."""
        body = (
            "`★ Insight ─────────`\n"
            "Some commentary about the repo.\n"
            "`─────────`\n"
            "\n"
            "---\n"
            "\n"
            "## Real Title\n"
            "\n"
            "### TL;DR\n"
            "- content\n"
        )
        result = assemble(body, _repo(), _ctx())
        # First non-blank line should be the real title, not the Insight block
        self.assertTrue(result.lstrip().startswith("## Real Title"))
        # The Insight block content should NOT appear before the title
        before_title = result.split("## Real Title", 1)[0]
        self.assertNotIn("★ Insight", before_title)
        self.assertNotIn("Some commentary", before_title)

    def test_fallback_when_no_hash_title(self):
        """If model omits ## title entirely, fall back to first non-empty line."""
        body = "Just some plain text\n\n### TL;DR\n- fallback case\n"
        result = assemble(body, _repo(), _ctx())
        # Doesn't crash, produces something
        self.assertIn("Just some plain text", result)
        self.assertIn("**원본 레포**", result)
        self.assertIn("### 참고 및 출처", result)

    def test_blank_lines_before_title_handled(self):
        body = "\n\n\n## Title After Blanks\n\n### TL;DR\n"
        result = assemble(body, _repo(), _ctx())
        self.assertTrue(result.startswith("## Title After Blanks"))

    def test_header_includes_reddit_when_present(self):
        ctx = _ctx(reddit_posts=[
            {"subreddit": "LocalLLaMA", "score": 200, "comments": 30,
             "permalink": "https://reddit.com/r/LocalLLaMA/comments/x"},
        ])
        body = "## Title\n\n### TL;DR\n"
        result = assemble(body, _repo(), ctx)
        self.assertIn("Reddit r/LocalLLaMA", result)
        self.assertIn("200 pts", result)

    def test_header_omits_hn_when_no_url(self):
        body = "## Title\n\n### TL;DR\n"
        result = assemble(body, _repo(), _ctx(hn_url="", hn_score=0))
        self.assertNotIn("Hacker News", result)


if __name__ == "__main__":
    unittest.main()
