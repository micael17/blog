"""
github-radar POC — Tier 1 source collection.

Hits 2 sources without auth or external libraries (Python stdlib only):
  1. Hacker News (Algolia search API)
  2. Reddit (public JSON endpoint, multiple subreddits)

Goal: verify each source is reachable, see what fields we get,
and surface multi-source repos as a quality signal.
"""

import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta

USER_AGENT = "github-radar-poc/0.1 (research)"


def fetch(url, timeout=20):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


GITHUB_REPO_RE = re.compile(r"github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)")


def normalize_repo(url):
    """Extract 'owner/repo' from any github.com URL, or None."""
    m = GITHUB_REPO_RE.search(url or "")
    if not m:
        return None
    owner, repo = m.group(1), m.group(2)
    repo = re.sub(r"\.git$", "", repo)
    if owner.lower() in ("orgs", "users", "search", "marketplace", "topics", "trending"):
        return None
    return f"{owner}/{repo}"


# ---------- Hacker News (Algolia) ----------
def fetch_hn(hours_back=48):
    cutoff = int((datetime.now(timezone.utc) - timedelta(hours=hours_back)).timestamp())
    url = (
        "https://hn.algolia.com/api/v1/search"
        f"?query=github.com&tags=story&numericFilters=created_at_i>{cutoff}"
        "&hitsPerPage=100"
    )
    data = json.loads(fetch(url))
    items = []
    for hit in data.get("hits", []):
        link = hit.get("url") or ""
        repo = normalize_repo(link)
        if not repo:
            continue
        items.append({
            "source": "hacker_news",
            "repo": repo,
            "url": link,
            "title": hit.get("title", ""),
            "score": hit.get("points", 0) or 0,
            "comments": hit.get("num_comments", 0) or 0,
            "hn_url": f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
            "created_at": hit.get("created_at"),
        })
    return items


# ---------- Reddit ----------
def fetch_reddit(subs=("LocalLLaMA", "MachineLearning", "programming", "selfhosted")):
    items = []
    for sub in subs:
        try:
            data = json.loads(fetch(f"https://www.reddit.com/r/{sub}/hot.json?limit=50"))
        except urllib.error.HTTPError as e:
            print(f"  reddit/{sub} HTTP {e.code}", file=sys.stderr)
            time.sleep(1)
            continue
        except Exception as e:
            print(f"  reddit/{sub} ERROR: {e}", file=sys.stderr)
            continue

        for child in data.get("data", {}).get("children", []):
            d = child.get("data", {})
            link = d.get("url_overridden_by_dest") or d.get("url") or ""
            repo = normalize_repo(link)
            if not repo:
                # also check selftext for github links
                selftext = d.get("selftext") or ""
                repo = normalize_repo(selftext)
                if not repo:
                    continue
                link = f"github.com/{repo}"
            items.append({
                "source": f"reddit/r/{sub}",
                "repo": repo,
                "url": link,
                "title": d.get("title", ""),
                "score": d.get("score", 0),
                "comments": d.get("num_comments", 0),
                "subreddit": sub,
                "permalink": f"https://reddit.com{d.get('permalink', '')}",
                "created_utc": d.get("created_utc"),
            })
        time.sleep(0.5)  # gentle rate limiting
    return items


# ---------- Data builder ----------
def collect_all():
    """Collect candidates from all Tier 1 sources. Returns dict.

    Returns:
        {
            "run_at": ISO timestamp,
            "hn": [...items...],
            "reddit": [...items...],
            "multi_source": [...repos appearing in 2+ sources...]
        }
    """
    hn = []
    reddit = []
    try:
        hn = fetch_hn(hours_back=48)
    except Exception as e:
        print(f"  HN fetch failed: {type(e).__name__}: {e}")
    try:
        reddit = fetch_reddit()
    except Exception as e:
        print(f"  Reddit fetch failed: {type(e).__name__}: {e}")

    all_items = hn + reddit
    sources_per_repo = {}
    for it in all_items:
        sources_per_repo.setdefault(it["repo"].lower(), set()).add(it["source"])
    multi = [
        {"repo": repo, "sources": sorted(srcs)}
        for repo, srcs in sources_per_repo.items()
        if len(srcs) >= 2
    ]
    multi.sort(key=lambda x: -len(x["sources"]))

    return {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "hn": hn,
        "reddit": reddit,
        "multi_source": multi,
    }


# ---------- CLI ----------
def main():
    sep = "=" * 70
    print(sep)
    print("github-radar collector — Tier 1")
    print(sep)

    data = collect_all()
    hn = data["hn"]
    reddit = data["reddit"]
    multi = data["multi_source"]

    print(f"\n[1/2] Hacker News: {len(hn)} repos")
    for r in sorted(hn, key=lambda x: -x["score"])[:5]:
        print(f"  - {r['repo']:<40} ({r['score']:>4} pts) {r['title'][:60]}")

    print(f"\n[2/2] Reddit: {len(reddit)} repos")
    for r in sorted(reddit, key=lambda x: -x["score"])[:5]:
        print(f"  - {r['repo']:<40} ({r['score']:>4} pts) {r['title'][:60]}")

    print(f"\nUnique repos: {len({**{i['repo'].lower(): 1 for i in hn}, **{i['repo'].lower(): 1 for i in reddit}})}")
    print(f"Multi-source: {len(multi)}")
    if len(sys.argv) > 1 and sys.argv[1] == "--save":
        out = "poc_output.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Saved → {out}")


if __name__ == "__main__":
    main()
