"""
github-radar POC step 2 — enrich a candidate repo with GitHub API data.

Pulls repo metadata + README so we have everything an article needs.
Uses GITHUB_TOKEN if available (5000 req/hr) else 60 req/hr unauthenticated.

Usage:
    python3 enrich.py                  # picks top HN candidate from poc_output.json
    python3 enrich.py owner/repo       # explicit repo
"""

import json
import os
import sys
import urllib.error
import urllib.request

GH_API = "https://api.github.com"


def gh_get(path):
    headers = {
        "User-Agent": "github-radar-poc",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = path if path.startswith("http") else f"{GH_API}{path}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def fetch_raw(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "github-radar-poc"},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", errors="replace")


def enrich(owner, repo):
    print(f"Fetching metadata for {owner}/{repo} ...")
    meta = gh_get(f"/repos/{owner}/{repo}")

    print("Fetching README ...")
    readme_text = None
    readme_url = None
    try:
        readme_meta = gh_get(f"/repos/{owner}/{repo}/readme")
        readme_url = readme_meta.get("html_url")
        download_url = readme_meta.get("download_url")
        if download_url:
            readme_text = fetch_raw(download_url)
    except urllib.error.HTTPError as e:
        print(f"  README not available (HTTP {e.code})")

    print("Fetching language breakdown ...")
    languages = {}
    try:
        languages = gh_get(f"/repos/{owner}/{repo}/languages")
    except urllib.error.HTTPError as e:
        print(f"  languages failed (HTTP {e.code})")

    return {
        "owner": owner,
        "repo": repo,
        "full_name": meta.get("full_name"),
        "description": meta.get("description"),
        "stars": meta.get("stargazers_count"),
        "forks": meta.get("forks_count"),
        "watchers": meta.get("watchers_count"),
        "open_issues": meta.get("open_issues_count"),
        "language": meta.get("language"),
        "languages_breakdown": languages,
        "topics": meta.get("topics") or [],
        "license": (meta.get("license") or {}).get("spdx_id"),
        "homepage": meta.get("homepage"),
        "created_at": meta.get("created_at"),
        "pushed_at": meta.get("pushed_at"),
        "default_branch": meta.get("default_branch"),
        "html_url": meta.get("html_url"),
        "size_kb": meta.get("size"),
        "is_fork": meta.get("fork"),
        "archived": meta.get("archived"),
        "readme_url": readme_url,
        "readme": readme_text,
        "readme_length": len(readme_text) if readme_text else 0,
    }


def pick_top_candidate():
    with open("poc_output.json") as f:
        data = json.load(f)
    hn = sorted(data.get("hn", []), key=lambda x: -(x.get("score") or 0))
    if not hn:
        raise SystemExit("no HN candidates in poc_output.json — run collect.py first")
    return hn[0]["repo"]


def main():
    if len(sys.argv) > 1:
        target = sys.argv[1].lstrip("/")
    else:
        target = pick_top_candidate()

    if "/" not in target:
        raise SystemExit(f"target must be owner/repo, got: {target}")
    owner, repo = target.split("/", 1)

    try:
        enriched = enrich(owner, repo)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"GitHub API error HTTP {e.code}: {body[:300]}")

    safe_name = enriched["full_name"].replace("/", "_")
    out_path = f"enriched_{safe_name}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(enriched, f, ensure_ascii=False, indent=2)

    sep = "=" * 70
    print("\n" + sep)
    print(f"Enriched: {enriched['full_name']}")
    print(sep)
    print(f"  Description : {enriched['description']}")
    print(f"  Stars       : {enriched['stars']:,}")
    print(f"  Forks       : {enriched['forks']:,}")
    print(f"  Open issues : {enriched['open_issues']:,}")
    print(f"  Language    : {enriched['language']}  (breakdown: {list(enriched['languages_breakdown'].keys())})")
    print(f"  Topics      : {', '.join(enriched['topics']) if enriched['topics'] else '-'}")
    print(f"  License     : {enriched['license'] or '-'}")
    print(f"  Homepage    : {enriched['homepage'] or '-'}")
    print(f"  Created     : {enriched['created_at']}")
    print(f"  Last push   : {enriched['pushed_at']}")
    print(f"  Size        : {enriched['size_kb']} KB")
    print(f"  README      : {enriched['readme_length']:,} chars")
    print(f"\nSaved → {out_path}")


if __name__ == "__main__":
    main()
