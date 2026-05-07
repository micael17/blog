"""Repo selection from collected candidates.

Pure logic: scoring, threshold, cap, dedup. No I/O.
"""

from state import is_covered

NICHE_KEYWORDS = [
    "ai", "llm", "agent", "model", "claude", "gpt", "mcp", "rag",
    "llama", "devtool", "cli", "automation", "ide", "embedding",
    "transformer", "diffusion",
]


def has_niche_keyword(text):
    if not text:
        return False
    lower = text.lower()
    return any(kw in lower for kw in NICHE_KEYWORDS)


def score_candidate(items):
    """Composite score for a single repo from its source items.

    Formula: HN_max × 1.0 + Reddit_sum × 0.5 + multi_source(50) + niche(20)
    """
    hn_items = [c for c in items if c["source"] == "hacker_news"]
    reddit_items = [c for c in items if c["source"].startswith("reddit/")]

    hn_score = max((c.get("score", 0) for c in hn_items), default=0)
    reddit_score = sum(c.get("score", 0) for c in reddit_items)

    platforms = set()
    for c in items:
        platforms.add(c["source"].split("/")[0])
    multi_source = len(platforms) >= 2

    titles = " ".join((c.get("title") or "") for c in items)

    score = hn_score * 1.0 + reddit_score * 0.5
    if multi_source:
        score += 50.0
    if has_niche_keyword(titles):
        score += 20.0
    return score


def select_repos(candidates, covered_db, threshold=100, max_n=5, today=None,
                 forced=None):
    """Return list of repo full_names to publish today.

    Args:
        candidates: dict with 'hn' and 'reddit' keys (from collect_all)
        covered_db: dict from load_covered()
        threshold: minimum score to consider
        max_n: max number of repos to return
        today: date override for testing
        forced: if set, bypass all filters and return [forced]
    """
    if forced:
        return [forced.lower()]

    by_repo = {}
    for item in list(candidates.get("hn", [])) + list(candidates.get("reddit", [])):
        by_repo.setdefault(item["repo"].lower(), []).append(item)

    scored = []
    for repo, items in by_repo.items():
        score = score_candidate(items)
        if score >= threshold:
            scored.append((repo, score))

    scored.sort(key=lambda x: -x[1])

    selected = []
    for repo, _score in scored:
        if is_covered(repo, covered_db, today=today):
            continue
        selected.append(repo)
        if len(selected) >= max_n:
            break
    return selected
