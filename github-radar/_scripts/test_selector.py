import unittest
from datetime import date, timedelta

from selector import score_candidate, select_repos, has_niche_keyword


def _hn(repo, score=100, comments=10, title="some tool"):
    return {"source": "hacker_news", "repo": repo, "score": score,
            "comments": comments, "title": title}


def _rd(repo, sub="LocalLLaMA", score=100, comments=10, title="some tool"):
    return {"source": f"reddit/r/{sub}", "repo": repo, "score": score,
            "comments": comments, "subreddit": sub, "title": title}


class TestNicheKeyword(unittest.TestCase):
    def test_has_keyword_lowercase(self):
        self.assertTrue(has_niche_keyword("Build llm agents"))

    def test_has_keyword_mixed_case(self):
        self.assertTrue(has_niche_keyword("AI Tool for Devs"))

    def test_no_keyword(self):
        self.assertFalse(has_niche_keyword("Mobile game engine"))

    def test_empty_string(self):
        self.assertFalse(has_niche_keyword(""))

    def test_none_input(self):
        self.assertFalse(has_niche_keyword(None))


class TestScoreCandidate(unittest.TestCase):
    def test_hn_only_no_niche(self):
        items = [_hn("a/b", score=200, title="generic project")]
        self.assertAlmostEqual(score_candidate(items), 200.0)

    def test_hn_only_with_niche(self):
        items = [_hn("a/b", score=200, title="LLM agent")]
        self.assertAlmostEqual(score_candidate(items), 220.0)

    def test_reddit_score_halved(self):
        items = [_rd("a/b", score=100, title="generic")]
        self.assertAlmostEqual(score_candidate(items), 50.0)

    def test_multi_source_bonus(self):
        items = [_hn("a/b", score=100, title="generic"),
                 _rd("a/b", score=50, title="generic")]
        self.assertAlmostEqual(score_candidate(items), 175.0)

    def test_multi_source_plus_niche(self):
        items = [_hn("a/b", score=100, title="ai tool"),
                 _rd("a/b", score=50, title="ai tool")]
        self.assertAlmostEqual(score_candidate(items), 195.0)

    def test_multiple_hn_takes_max(self):
        items = [_hn("a/b", score=80, title="x"),
                 _hn("a/b", score=200, title="y")]
        self.assertAlmostEqual(score_candidate(items), 200.0)


class TestSelectRepos(unittest.TestCase):
    def test_threshold_filters_low_score(self):
        candidates = {"hn": [_hn("a/b", score=50, title="minor")], "reddit": []}
        self.assertEqual(select_repos(candidates, {}), [])

    def test_above_threshold_included(self):
        candidates = {"hn": [_hn("a/b", score=200, title="ai tool")], "reddit": []}
        self.assertEqual(select_repos(candidates, {}), ["a/b"])

    def test_dedup_skips_recently_covered(self):
        recent = (date.today() - timedelta(days=10)).isoformat()
        candidates = {"hn": [_hn("a/b", score=500, title="ai")], "reddit": []}
        self.assertEqual(select_repos(candidates, {"a/b": recent}), [])

    def test_dedup_allows_after_cooldown(self):
        old = (date.today() - timedelta(days=31)).isoformat()
        candidates = {"hn": [_hn("a/b", score=500, title="ai")], "reddit": []}
        self.assertEqual(select_repos(candidates, {"a/b": old}), ["a/b"])

    def test_caps_at_max_n(self):
        items = [_hn(f"o/r{i}", score=200, title="ai") for i in range(10)]
        result = select_repos({"hn": items, "reddit": []}, {}, max_n=3)
        self.assertEqual(len(result), 3)

    def test_force_bypasses_threshold_and_dedup(self):
        recent = date.today().isoformat()
        result = select_repos({"hn": [], "reddit": []},
                              {"x/y": recent}, forced="x/y")
        self.assertEqual(result, ["x/y"])

    def test_orders_by_score_desc(self):
        items = [
            _hn("low/score", score=110, title="tool"),
            _hn("high/score", score=500, title="ai"),
        ]
        result = select_repos({"hn": items, "reddit": []}, {})
        self.assertEqual(result[0], "high/score")
        self.assertEqual(result[1], "low/score")

    def test_empty_candidates(self):
        self.assertEqual(select_repos({"hn": [], "reddit": []}, {}), [])

    def test_case_insensitive_repo_grouping(self):
        """Same repo with different casing should be deduped/grouped together."""
        candidates = {"hn": [_hn("OpenBMB/MiniCPM", score=200, title="ai")],
                      "reddit": [_rd("openbmb/minicpm", score=100, title="ai")]}
        result = select_repos(candidates, {})
        # Should appear only once (grouped) and in lowercase
        self.assertEqual(result, ["openbmb/minicpm"])

    def test_case_insensitive_dedup(self):
        """Recently covered repo (lowercase in db) blocks even if input has different casing."""
        recent = (date.today() - timedelta(days=10)).isoformat()
        covered = {"openbmb/minicpm": recent}
        candidates = {"hn": [_hn("OpenBMB/MiniCPM", score=500, title="ai")], "reddit": []}
        self.assertEqual(select_repos(candidates, covered), [])

    def test_force_returns_lowercase(self):
        """Forced repo is returned in lowercase for consistency."""
        result = select_repos({"hn": [], "reddit": []}, {}, forced="OpenBMB/MiniCPM")
        self.assertEqual(result, ["openbmb/minicpm"])


if __name__ == "__main__":
    unittest.main()
