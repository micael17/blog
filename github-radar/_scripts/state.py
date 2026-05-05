"""covered.json (dedup state) read/write + cooldown check."""

import json
import os
from datetime import date, datetime


def load_covered(path):
    """Read covered DB. Returns empty dict if file missing."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_covered(db, path):
    """Atomic write of covered DB. Creates parent dir if missing."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2, sort_keys=True)
    os.replace(tmp, path)


def is_covered(repo, db, cooldown_days=30, today=None):
    """True if repo was covered within the cooldown window (strictly less than)."""
    if repo not in db:
        return False
    today = today or date.today()
    last = datetime.strptime(db[repo], "%Y-%m-%d").date()
    return (today - last).days < cooldown_days


def mark_covered(repo, db, today=None):
    """Mutate db in place: set repo's last-covered date to today."""
    today = today or date.today()
    db[repo] = today.isoformat()
