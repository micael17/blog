"""Write a post folder: <slug>-<date>/{post.md, source.json}."""

import json
import os
from datetime import date


def make_slug(repo_full_name):
    """'owner/repo' → 'owner-repo' (lowercase, slash → dash)."""
    return repo_full_name.replace("/", "-").lower()


def make_folder_name(repo_full_name, today=None):
    """'owner/repo' + 2026-05-05 → 'owner-repo-20260505'."""
    today = today or date.today()
    return f"{make_slug(repo_full_name)}-{today.strftime('%Y%m%d')}"


def write_post(parent_dir, folder_name, article_md, source_data):
    """Write post.md + source.json into parent_dir/folder_name/.

    Returns the full post_dir path.
    """
    post_dir = os.path.join(parent_dir, folder_name)
    os.makedirs(post_dir, exist_ok=True)
    with open(os.path.join(post_dir, "post.md"), "w", encoding="utf-8") as f:
        f.write(article_md)
    with open(os.path.join(post_dir, "source.json"), "w", encoding="utf-8") as f:
        json.dump(source_data, f, ensure_ascii=False, indent=2)
    return post_dir
