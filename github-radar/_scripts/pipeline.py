"""github-radar pipeline orchestrator.

Single entry point: collect → select → for-each(enrich → generate → write_post → mark_covered)
→ git commit + push.

CLI:
    python3 pipeline.py             # full run, commit, push
    python3 pipeline.py --dry-run   # 모든 단계 실행하나 commit/push 없음
    python3 pipeline.py --force owner/repo   # 특정 repo 강제 (dedup/threshold 무시)
"""

import argparse
import os
import subprocess
import sys

from collect import collect_all
from enrich import enrich
from generate import generate_article, find_social_context
from post_writer import make_folder_name, write_post
from selector import select_repos
from state import load_covered, mark_covered, save_covered

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GITHUB_RADAR_ROOT = os.path.dirname(SCRIPT_DIR)
STATE_FILE = os.path.join(GITHUB_RADAR_ROOT, "_state", "covered.json")


def passes_filters(enriched):
    """archived + fork + low stars 거름."""
    if enriched.get("archived"):
        return False
    if enriched.get("is_fork"):
        return False
    if (enriched.get("stars") or 0) < 50:
        return False
    return True


def git_commit_and_push(repo_root, files, message, dry_run=False):
    """git add → commit → push. dry_run이면 출력만."""
    if dry_run:
        print(f"[dry-run] would commit + push: {message}")
        return
    subprocess.run(["git", "add"] + files, check=True, cwd=repo_root)
    subprocess.run(["git", "commit", "-m", message], check=True, cwd=repo_root)
    subprocess.run(["git", "push"], check=True, cwd=repo_root)


def build_commit_message(successes):
    """Format: 'add: github-radar — N건 (a/b, c/d)' + 본문에 각 repo 정보."""
    summary = ", ".join(repo for repo, _, _ in successes)
    title = f"add: github-radar — {len(successes)}건 ({summary})"
    body_lines = []
    for repo, _, enriched in successes:
        stars = enriched.get("stars", 0)
        body_lines.append(f"- {repo} ({stars:,}★, {enriched.get('language') or '?'})")
    body = "\n".join(body_lines)
    return f"{title}\n\n{body}\n"


def main():
    parser = argparse.ArgumentParser(description="github-radar daily pipeline")
    parser.add_argument("--dry-run", action="store_true",
                        help="Run all stages but don't commit or push")
    parser.add_argument("--force", metavar="OWNER/REPO",
                        help="Process a specific repo, bypassing threshold and dedup")
    args = parser.parse_args()

    print(f"[1/5] Collecting candidates ...")
    candidates = collect_all()
    total = len(candidates.get("hn", [])) + len(candidates.get("reddit", []))
    print(f"  Total: {total} items")

    print(f"[2/5] Selecting repos ...")
    covered = load_covered(STATE_FILE)
    selected = select_repos(candidates, covered, forced=args.force)
    print(f"  Selected: {selected}")

    if not selected:
        print("No candidates above threshold. Exiting cleanly.")
        return 0

    successes = []  # list of (repo, post_dir, enriched)
    filter_skips = 0
    exception_failures = 0
    for repo in selected:
        try:
            print(f"\n[3/5] Enriching {repo} ...")
            owner, repo_name = repo.split("/", 1)
            enriched = enrich(owner, repo_name)

            if not passes_filters(enriched) and not args.force:
                print(f"  filtered out (archived/fork/low stars): {repo}")
                filter_skips += 1
                continue

            print(f"[4/5] Generating article for {repo} ...")
            social_ctx = find_social_context(repo, candidates)
            article_md = generate_article(enriched, social_ctx)

            if args.dry_run:
                print(f"  [dry-run] would write post: {len(article_md):,} chars")
                successes.append((repo, "(dry-run)", enriched))
                continue

            print(f"[5/5] Writing post for {repo} ...")
            folder_name = make_folder_name(repo)
            post_dir = write_post(GITHUB_RADAR_ROOT, folder_name, article_md, enriched)
            mark_covered(repo, covered)
            successes.append((repo, post_dir, enriched))
        except Exception as e:
            print(f"  ERROR processing {repo}: {type(e).__name__}: {e}",
                  file=sys.stderr)
            exception_failures += 1
            continue

    if not successes:
        if exception_failures > 0:
            print(f"\nAll selected repos failed (exceptions: {exception_failures}). No commit.")
            return 1
        print(f"\nAll selected repos filtered out (filter_skips: {filter_skips}). No commit.")
        return 0

    if args.dry_run:
        print(f"\n[dry-run] would have generated {len(successes)} posts.")
        return 0

    save_covered(covered, STATE_FILE)

    files_to_add = [STATE_FILE]
    for repo, post_dir, _ in successes:
        files_to_add.append(post_dir)

    msg = build_commit_message(successes)
    git_commit_and_push(GITHUB_RADAR_ROOT, files_to_add, msg, dry_run=args.dry_run)
    print(f"\nPublished {len(successes)} posts: {[r for r,_,_ in successes]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
