# github-radar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** POC 코드(`collect.py`, `enrich.py`, `generate.py`)를 production 파이프라인으로 정리하고, dedup/scoring/orchestration을 추가해 Hermes에서 매일 자동 실행 가능한 단일 진입점을 제공한다.

**Architecture:** 기존 POC의 3개 스크립트를 `_scripts/` 하위로 이동 + 콜러블로 리팩터링. 신규 4개 모듈(`state`, `selector`, `post_writer`, `pipeline`) 추가. 모든 신규 모듈은 stdlib `unittest` 기반 TDD로 작성. covered.json은 git에 커밋되는 상태 SSOT.

**Tech Stack:** Python 3.9 stdlib only (urllib, json, unittest, subprocess). 외부 의존성 없음. Claude Code CLI(`claude -p`)는 구독 인증 사용. `GITHUB_TOKEN`은 환경변수.

---

## Spec Reference

본 plan은 `docs/superpowers/specs/2026-05-05-github-radar-design.md`를 구현한다. spec 변경 시 plan도 동기화 필요.

## Pre-flight Notes

- **CWD 가정**: `pipeline.py`는 어떤 CWD에서 호출되어도 동작해야 함. 모든 경로는 `__file__` 기준 절대경로로 계산.
- **Branch**: 메인 브랜치에서 직접 작업해도 무방. (사용자 승인됨)
- **Push 정책**: pipeline.py 자체는 자동 push (Hermes 운영 동작). 그러나 plan 실행 중 발생하는 commit들은 사용자 명시 승인 시에만 push.
- **테스트 실행**: `cd github-radar/_scripts && python3 -m unittest discover -p "test_*.py"`
- **개별 테스트 실행**: `cd github-radar/_scripts && python3 test_<module>.py`

## File Structure (목표 상태)

```
blog/github-radar/
├── README.md                         # NEW (Task 8)
├── _scripts/
│   ├── collect.py                    # MOVE + refactor (Task 1, 2)
│   ├── enrich.py                     # MOVE (Task 1)
│   ├── generate.py                   # MOVE + refactor (Task 1, 3)
│   ├── selector.py                   # NEW (Task 5)
│   ├── state.py                      # NEW (Task 4)
│   ├── post_writer.py                # NEW (Task 6)
│   ├── pipeline.py                   # NEW (Task 7)
│   ├── test_selector.py              # NEW (Task 5)
│   ├── test_state.py                 # NEW (Task 4)
│   ├── test_post_writer.py           # NEW (Task 6)
│   └── test_pipeline.py              # NEW (Task 7)
└── _state/
    └── covered.json                   # NEW (Task 8)
```

각 모듈의 단일 책임:
- `collect.py`: HN+Reddit 데이터 fetch → in-memory dict
- `enrich.py`: GitHub API → metadata + README
- `generate.py`: enriched + social context → 한국어 마크다운 (헤더/풋터 포함)
- `selector.py`: 후보 → 발행할 repo 리스트 (scoring + dedup)
- `state.py`: covered.json 읽기/쓰기 + 30일 cooldown 판정
- `post_writer.py`: post.md + source.json을 폴더에 저장
- `pipeline.py`: 위를 모두 묶어 호출하는 단일 진입점 (CLI: `--dry-run`, `--force`)

---

## Task 1: 파일 이동 — POC 스크립트를 `_scripts/`로

**Files:**
- Move: `github-radar/collect.py` → `github-radar/_scripts/collect.py`
- Move: `github-radar/enrich.py` → `github-radar/_scripts/enrich.py`
- Move: `github-radar/generate.py` → `github-radar/_scripts/generate.py`

이 단계는 단순 이동이며 동작 변화는 없다. 다음 task에서 콜러블화 리팩터링.

- [ ] **Step 1: `_scripts/` 디렉터리 생성 + git mv**

```bash
cd /Users/jihong/Documents/workspace/blog
mkdir -p github-radar/_scripts
git mv github-radar/collect.py github-radar/_scripts/collect.py
git mv github-radar/enrich.py github-radar/_scripts/enrich.py
git mv github-radar/generate.py github-radar/_scripts/generate.py
git status
```

Expected: 3 renamed files staged.

- [ ] **Step 2: 이동 후 스크립트 동작 확인 (collect.py)**

```bash
cd github-radar/_scripts
python3 collect.py
```

Expected: 정상 동작, `poc_output.json`이 `_scripts/` 디렉터리에 생성됨. (이는 임시 — 다음 task에서 변경)

- [ ] **Step 3: enrich.py 동작 확인**

POC에서 만든 `github-radar/poc_output.json`이 루트에 있고, `_scripts/`에 새로 만들어진 게 있을 것. enrich.py는 `poc_output.json`을 같은 디렉토리에서 찾으므로 `_scripts/poc_output.json`을 사용.

```bash
python3 enrich.py
```

Expected: `_scripts/enriched_aattaran_deepclaude.json` 생성. 정상.

- [ ] **Step 4: generate.py 동작 확인 (skip — claude CLI 호출은 비용 발생)**

스킵. 다음 task에서 콜러블 리팩터링 후 통합 테스트로 검증.

- [ ] **Step 5: 임시 산출물 정리 + 커밋**

```bash
cd /Users/jihong/Documents/workspace/blog
# POC 시점에 만들어졌던 산출물(이전 위치)은 그대로 둠 — 이미 커밋되어 있음
# 새로 만들어진 _scripts/ 내부의 임시 산출물은 untracked
ls github-radar/_scripts/
git status
```

`_scripts/` 내부의 `poc_output.json`, `enriched_*.json` 같은 임시 파일은 커밋하지 않음. `.gitignore` 추가:

```bash
cat > github-radar/.gitignore <<'EOF'
# 파이프라인 실행 시 발생하는 임시 산출물 (post 폴더 안의 source.json은 트래킹됨)
_scripts/poc_output.json
_scripts/enriched_*.json
_scripts/article_*.md
_scripts/*.tmp
EOF

git add github-radar/.gitignore
git status
```

- [ ] **Step 6: Commit**

```bash
git commit -m "$(cat <<'EOF'
refactor: github-radar — POC 스크립트를 _scripts/ 하위로 이동

다음 task에서 콜러블 리팩터링 + 신규 모듈(state/selector/post_writer/pipeline)
추가를 위한 정리.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: collect.py 리팩터링 — 콜러블 함수 추출

**Files:**
- Modify: `github-radar/_scripts/collect.py`

`main()`이 print + JSON 저장까지 하던 것을 분리. 신규 함수 `collect_all()`이 dict를 반환. CLI 모드는 `main()`이 `collect_all()` 호출 후 출력.

- [ ] **Step 1: collect_all() 함수 추출**

`collect.py` 파일에서 기존 `main()` 함수를 다음과 같이 분리:

```python
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
    from datetime import datetime, timezone
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
```

기존 `main()`은 `collect_all()` 호출하는 버전으로 단순화:

```python
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
```

기존 코드의 변경 포인트:
- 기존 `main()`이 직접 했던 dict 빌드를 `collect_all()`로 이동
- 기존의 자동 JSON 저장은 `--save` flag로 옵션화 (CLI 디버깅용만)
- print 출력은 그대로 유지

- [ ] **Step 2: 검증 — CLI 모드 동작**

```bash
cd github-radar/_scripts
python3 collect.py
```

Expected: 콘솔에 HN + Reddit 결과 출력, JSON 저장 없음 (디폴트).

```bash
python3 collect.py --save
ls poc_output.json
```

Expected: `poc_output.json` 생성됨.

- [ ] **Step 3: 검증 — 콜러블 import 확인**

```bash
python3 -c "from collect import collect_all; d = collect_all(); print('hn:', len(d['hn']), 'reddit:', len(d['reddit']))"
```

Expected: `hn: NN reddit: NN` 출력.

- [ ] **Step 4: Commit**

```bash
cd /Users/jihong/Documents/workspace/blog
git add github-radar/_scripts/collect.py
git commit -m "$(cat <<'EOF'
refactor: collect.py — collect_all() 콜러블 분리

main()의 dict 빌드 로직을 collect_all() 함수로 추출. CLI 모드는
유지하되 JSON 저장은 --save flag로 옵션화.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: generate.py 리팩터링 — 콜러블 + 비파일 인풋

**Files:**
- Modify: `github-radar/_scripts/generate.py`

기존 `main()`이 파일에서 enriched/poc_output을 읽었음. 다음 리팩터링:
- `find_social_context()`이 dict를 받도록 변경 (파일 의존 제거)
- `generate_article(enriched, social_ctx) -> str` 콜러블 추가
- CLI 모드에서는 파일에서 dict 로드해서 콜

- [ ] **Step 1: find_social_context를 dict-based로 변경**

기존:
```python
def find_social_context(full_name, poc_path="poc_output.json"):
    ...
    poc = json.load(open(poc_path))
    ...
```

변경:
```python
def find_social_context(full_name, candidates):
    """Build social context for a repo from already-loaded candidates dict.

    Args:
        full_name: 'owner/repo'
        candidates: dict with 'hn' and 'reddit' keys (from collect_all())

    Returns:
        dict with hn_title, hn_score, hn_comments, hn_url, reddit_posts
    """
    target = full_name.lower()
    hn_title, hn_score, hn_comments, hn_url = "(unknown)", 0, 0, ""

    for h in candidates.get("hn", []):
        if h["repo"].lower() == target and h.get("score", 0) > hn_score:
            hn_title = h.get("title", "(unknown)")
            hn_score = h["score"]
            hn_comments = h.get("comments", 0)
            hn_url = h.get("hn_url", "")

    reddit_posts = [
        r for r in candidates.get("reddit", [])
        if r["repo"].lower() == target
    ]
    return {
        "hn_title": hn_title,
        "hn_score": hn_score,
        "hn_comments": hn_comments,
        "hn_url": hn_url,
        "reddit_posts": reddit_posts,
    }
```

- [ ] **Step 2: generate_article() 콜러블 추가**

`generate.py`의 main 로직을 새 함수로 추출:

```python
def generate_article(enriched, social_ctx):
    """Generate full article markdown (header + body + footer).

    Args:
        enriched: dict from enrich.py (repo metadata + README)
        social_ctx: dict from find_social_context()

    Returns:
        Full assembled markdown string.
    """
    readme = enriched.get("readme") or "(README not available)"
    if len(readme) > MAX_README_CHARS:
        readme = readme[:MAX_README_CHARS] + "\n\n[... README truncated for length ...]"

    reddit_section = ""
    if social_ctx.get("reddit_posts"):
        reddit_section = "- Reddit: " + ", ".join(
            f"r/{r['subreddit']} ({r['score']} pts)"
            for r in social_ctx["reddit_posts"]
        )

    prompt = PROMPT_TEMPLATE.format(
        full_name=enriched.get("full_name") or "?",
        description=enriched.get("description") or "(no description)",
        stars=enriched.get("stars") or 0,
        forks=enriched.get("forks") or 0,
        open_issues=enriched.get("open_issues") or 0,
        language=enriched.get("language") or "?",
        topics=", ".join(enriched.get("topics") or []) or "-",
        license=enriched.get("license") or "-",
        created_at=enriched.get("created_at") or "-",
        pushed_at=enriched.get("pushed_at") or "-",
        homepage=enriched.get("homepage") or "-",
        hn_title=social_ctx["hn_title"],
        hn_score=social_ctx["hn_score"],
        hn_comments=social_ctx["hn_comments"],
        reddit_section=reddit_section,
        readme=readme,
    )

    body = call_claude_cli(prompt)
    return assemble(body, enriched, social_ctx)
```

- [ ] **Step 3: CLI main()을 새 콜러블 사용하도록 단순화**

```python
def main():
    if len(sys.argv) > 1:
        enriched_path = sys.argv[1]
    else:
        candidates_files = sorted(glob.glob("enriched_*.json"), key=os.path.getmtime, reverse=True)
        if not candidates_files:
            raise SystemExit("no enriched_*.json found — run enrich.py first")
        enriched_path = candidates_files[0]
        print(f"Auto-picked: {enriched_path}")

    enriched = json.load(open(enriched_path))

    # CLI 모드에서는 poc_output.json에서 social context 로드
    candidates = {}
    try:
        candidates = json.load(open("poc_output.json"))
    except FileNotFoundError:
        print("WARNING: poc_output.json not found, social context will be empty")

    social_ctx = find_social_context(enriched["full_name"], candidates)

    print(f"Calling claude -p (sonnet) ...")
    article = generate_article(enriched, social_ctx)

    safe_name = enriched["full_name"].replace("/", "_")
    out_path = f"article_{safe_name}.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(article)

    print(f"\n✓ Saved → {out_path} ({len(article):,} chars)")
```

- [ ] **Step 4: 검증 — import 가능한지**

```bash
cd github-radar/_scripts
python3 -c "from generate import generate_article, find_social_context; print('imports OK')"
```

Expected: `imports OK`

- [ ] **Step 5: 검증 — find_social_context dict 인풋**

```bash
python3 -c "
from generate import find_social_context
fake = {'hn': [{'repo': 'a/b', 'score': 100, 'title': 'X', 'comments': 5, 'hn_url': 'http://hn'}], 'reddit': []}
ctx = find_social_context('a/b', fake)
assert ctx['hn_score'] == 100
assert ctx['hn_url'] == 'http://hn'
print('OK')
"
```

Expected: `OK`

- [ ] **Step 6: Commit**

```bash
cd /Users/jihong/Documents/workspace/blog
git add github-radar/_scripts/generate.py
git commit -m "$(cat <<'EOF'
refactor: generate.py — generate_article() 콜러블 + dict-based social ctx

find_social_context()가 파일 대신 dict를 받도록 변경. generate_article()
함수로 전체 생성 흐름을 추출해 pipeline.py에서 import 가능하게 함.
CLI 동작은 유지.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: state.py — covered.json 관리 (TDD)

**Files:**
- Create: `github-radar/_scripts/state.py`
- Test: `github-radar/_scripts/test_state.py`

`covered.json`은 `{"owner/repo": "YYYY-MM-DD", ...}` 형식. 30일 cooldown 판정 + atomic write.

- [ ] **Step 1: 실패하는 테스트 작성**

`github-radar/_scripts/test_state.py`:

```python
import json
import os
import tempfile
import unittest
from datetime import date, timedelta

from state import load_covered, save_covered, is_covered, mark_covered


class TestState(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.path = os.path.join(self.tmpdir, "covered.json")

    def test_load_missing_file_returns_empty(self):
        self.assertEqual(load_covered(self.path), {})

    def test_save_creates_parent_dir(self):
        nested = os.path.join(self.tmpdir, "_state", "covered.json")
        save_covered({"a/b": "2026-01-01"}, nested)
        self.assertTrue(os.path.exists(nested))

    def test_save_and_load_roundtrip(self):
        save_covered({"a/b": "2026-01-01", "c/d": "2026-02-02"}, self.path)
        self.assertEqual(load_covered(self.path),
                         {"a/b": "2026-01-01", "c/d": "2026-02-02"})

    def test_save_is_atomic(self):
        # tmp file should not remain after save
        save_covered({"a/b": "2026-01-01"}, self.path)
        self.assertFalse(os.path.exists(self.path + ".tmp"))

    def test_is_covered_recent(self):
        recent = (date.today() - timedelta(days=10)).isoformat()
        self.assertTrue(is_covered("a/b", {"a/b": recent}, cooldown_days=30))

    def test_is_covered_at_cooldown_boundary(self):
        # exactly 30 days ago: cooldown is "less than 30 days", so should be FALSE
        boundary = (date.today() - timedelta(days=30)).isoformat()
        self.assertFalse(is_covered("a/b", {"a/b": boundary}, cooldown_days=30))

    def test_is_covered_expired(self):
        old = (date.today() - timedelta(days=31)).isoformat()
        self.assertFalse(is_covered("a/b", {"a/b": old}, cooldown_days=30))

    def test_is_covered_not_in_db(self):
        self.assertFalse(is_covered("a/b", {}, cooldown_days=30))

    def test_mark_covered_sets_today(self):
        db = {}
        mark_covered("a/b", db)
        self.assertEqual(db["a/b"], date.today().isoformat())

    def test_mark_covered_overwrites(self):
        db = {"a/b": "2020-01-01"}
        mark_covered("a/b", db)
        self.assertEqual(db["a/b"], date.today().isoformat())

    def test_mark_covered_with_explicit_date(self):
        db = {}
        mark_covered("a/b", db, today=date(2026, 5, 5))
        self.assertEqual(db["a/b"], "2026-05-05")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
cd github-radar/_scripts
python3 test_state.py
```

Expected: `ModuleNotFoundError: No module named 'state'` (state.py 미존재)

- [ ] **Step 3: state.py 구현**

`github-radar/_scripts/state.py`:

```python
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
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```bash
python3 test_state.py
```

Expected: 모든 테스트 OK (11 tests).

- [ ] **Step 5: Commit**

```bash
cd /Users/jihong/Documents/workspace/blog
git add github-radar/_scripts/state.py github-radar/_scripts/test_state.py
git commit -m "$(cat <<'EOF'
add: state.py — covered.json read/write + cooldown check

30일 dedup cooldown 판정 + atomic write. unittest 11 cases 통과.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: selector.py — 후보 점수화 + 선정 (TDD)

**Files:**
- Create: `github-radar/_scripts/selector.py`
- Test: `github-radar/_scripts/test_selector.py`

수집된 후보 풀에서 발행할 repo 리스트를 결정. score = `HN×1.0 + Reddit×0.5 + multi(50) + niche_kw(20)`. 임계점 100, 상위 5개 cap, dedup 적용.

- [ ] **Step 1: 실패하는 테스트 작성**

`github-radar/_scripts/test_selector.py`:

```python
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
        # 200 base, no multi, no niche — expect ~200
        self.assertAlmostEqual(score_candidate(items), 200.0)

    def test_hn_only_with_niche(self):
        items = [_hn("a/b", score=200, title="LLM agent")]
        # 200 + 20 niche
        self.assertAlmostEqual(score_candidate(items), 220.0)

    def test_reddit_score_halved(self):
        items = [_rd("a/b", score=100, title="generic")]
        # 100 * 0.5 = 50
        self.assertAlmostEqual(score_candidate(items), 50.0)

    def test_multi_source_bonus(self):
        items = [_hn("a/b", score=100, title="generic"),
                 _rd("a/b", score=50, title="generic")]
        # 100 + 25 + 50 multi = 175
        self.assertAlmostEqual(score_candidate(items), 175.0)

    def test_multi_source_plus_niche(self):
        items = [_hn("a/b", score=100, title="ai tool"),
                 _rd("a/b", score=50, title="ai tool")]
        # 100 + 25 + 50 multi + 20 niche = 195
        self.assertAlmostEqual(score_candidate(items), 195.0)

    def test_multiple_hn_takes_max(self):
        items = [_hn("a/b", score=80, title="x"),
                 _hn("a/b", score=200, title="y")]
        # max HN score = 200, no multi, niche check joined ("x y")
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
            _hn("low/score", score=110, title="tool"),  # 110
            _hn("high/score", score=500, title="ai"),    # 520
        ]
        result = select_repos({"hn": items, "reddit": []}, {})
        self.assertEqual(result[0], "high/score")
        self.assertEqual(result[1], "low/score")

    def test_empty_candidates(self):
        self.assertEqual(select_repos({"hn": [], "reddit": []}, {}), [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
cd github-radar/_scripts
python3 test_selector.py
```

Expected: `ModuleNotFoundError: No module named 'selector'`

- [ ] **Step 3: selector.py 구현**

`github-radar/_scripts/selector.py`:

```python
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
        return [forced]

    by_repo = {}
    for item in list(candidates.get("hn", [])) + list(candidates.get("reddit", [])):
        by_repo.setdefault(item["repo"], []).append(item)

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
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```bash
python3 test_selector.py
```

Expected: 모든 테스트 OK (~17 tests).

- [ ] **Step 5: 실데이터로 정성 검증**

```bash
python3 -c "
import json
from selector import select_repos

# 기존 POC 데이터 사용 (블로그 루트의 github-radar/poc_output.json)
poc = json.load(open('../poc_output.json')) if __import__('os').path.exists('../poc_output.json') else None
if poc is None:
    print('SKIP: ../poc_output.json not found')
else:
    result = select_repos(poc, {})
    print('Selected:', result)
"
```

Expected: 1~5개 repo 출력. 직관적으로 흥미로운 후보들 (deepclaude 등)이 포함되어야 함.

- [ ] **Step 6: Commit**

```bash
cd /Users/jihong/Documents/workspace/blog
git add github-radar/_scripts/selector.py github-radar/_scripts/test_selector.py
git commit -m "$(cat <<'EOF'
add: selector.py — 후보 점수화 + 임계점 + dedup + cap

Score 공식: HN_max + Reddit_sum*0.5 + multi(50) + niche(20).
임계점 100, 상위 5개 cap, --force flag로 dedup bypass 지원.
unittest 17 cases 통과.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: post_writer.py — 폴더 + 파일 출력 (TDD)

**Files:**
- Create: `github-radar/_scripts/post_writer.py`
- Test: `github-radar/_scripts/test_post_writer.py`

`<owner>-<repo>-<YYYYMMDD>/` 형식 폴더 + 그 안에 `post.md`, `source.json` 작성.

- [ ] **Step 1: 실패하는 테스트 작성**

`github-radar/_scripts/test_post_writer.py`:

```python
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
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
cd github-radar/_scripts
python3 test_post_writer.py
```

Expected: `ModuleNotFoundError: No module named 'post_writer'`

- [ ] **Step 3: post_writer.py 구현**

`github-radar/_scripts/post_writer.py`:

```python
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
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```bash
python3 test_post_writer.py
```

Expected: 모든 테스트 OK (~10 tests).

- [ ] **Step 5: Commit**

```bash
cd /Users/jihong/Documents/workspace/blog
git add github-radar/_scripts/post_writer.py github-radar/_scripts/test_post_writer.py
git commit -m "$(cat <<'EOF'
add: post_writer.py — 폴더 + post.md + source.json 출력

slug 변환 + 날짜 폴더 + 파일 작성. unittest 10 cases 통과.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: pipeline.py — 오케스트레이션 (TDD)

**Files:**
- Create: `github-radar/_scripts/pipeline.py`
- Test: `github-radar/_scripts/test_pipeline.py`

단일 진입점. CLI: `--dry-run`, `--force <repo>`. 부분 실패 허용.

- [ ] **Step 1: 실패하는 테스트 작성**

`github-radar/_scripts/test_pipeline.py`:

```python
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
        # No post folder created in dry-run
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
        # generate should NOT be called for archived repo
        mock_generate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
cd github-radar/_scripts
python3 test_pipeline.py
```

Expected: `ModuleNotFoundError: No module named 'pipeline'`

- [ ] **Step 3: pipeline.py 구현**

`github-radar/_scripts/pipeline.py`:

```python
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
    for repo in selected:
        try:
            print(f"\n[3/5] Enriching {repo} ...")
            owner, repo_name = repo.split("/", 1)
            enriched = enrich(owner, repo_name)

            if not passes_filters(enriched) and not args.force:
                print(f"  filtered out (archived/fork/low stars): {repo}")
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
            continue

    if not successes:
        print("\nAll selected repos failed. No commit.")
        return 1

    if args.dry_run:
        print(f"\n[dry-run] would have generated {len(successes)} posts.")
        return 0

    save_covered(covered, STATE_FILE)

    files_to_add = [STATE_FILE]
    for repo, post_dir, _ in successes:
        files_to_add.append(post_dir)

    msg = build_commit_message(successes)
    git_commit_and_push(GITHUB_RADAR_ROOT, files_to_add, msg, dry_run=args.dry_run)
    print(f"\n✓ Published {len(successes)} posts: {[r for r,_,_ in successes]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```bash
cd github-radar/_scripts
python3 test_pipeline.py
```

Expected: 모든 테스트 OK (~7 tests).

- [ ] **Step 5: 전체 테스트 일괄 실행**

```bash
python3 -m unittest discover -p "test_*.py" -v
```

Expected: 모든 모듈 테스트 통과 (총 ~45 tests).

- [ ] **Step 6: Commit**

```bash
cd /Users/jihong/Documents/workspace/blog
git add github-radar/_scripts/pipeline.py github-radar/_scripts/test_pipeline.py
git commit -m "$(cat <<'EOF'
add: pipeline.py — Hermes 단일 진입점

collect → select → enrich → generate → write_post → commit/push.
--dry-run, --force OWNER/REPO 플래그. archived/fork/low-star 필터.
부분 실패 허용 (한 repo 실패해도 나머지 처리).
unittest 7 cases 통과.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: README.md + 초기 covered.json + 통합 dry-run

**Files:**
- Create: `github-radar/README.md`
- Create: `github-radar/_state/covered.json`

- [ ] **Step 1: README.md 작성**

`github-radar/README.md`:

```markdown
# github-radar

영어권에서 화제가 된 GitHub 레포(특히 AI/LLM·개발자 도구)를 매일 자동 분석해
한국어 블로그 글로 만드는 콘텐츠 파이프라인.

## 운영 방식

매일 10:30 KST에 Hermes(Mac mini)가 `pipeline.py`를 실행. 각 실행마다:

1. **수집**: Hacker News (Algolia) + Reddit (LocalLLaMA, MachineLearning, programming, selfhosted)
2. **선정**: 점수화 (HN×1.0 + Reddit×0.5 + 다중소스(50) + 니치키워드(20)) → 임계점 100, 상위 5개, 30일 dedup 적용
3. **수집/생성**: 각 선정된 repo에 대해 GitHub API로 메타+README 수집 → `claude -p`로 한국어 글 생성
4. **저장**: `<owner>-<repo>-<YYYYMMDD>/` 폴더에 `post.md` + `source.json` → git commit + push

데이터 품질에 따라 0~5편/일 가변 발행.

## 폴더 구조

```
github-radar/
├── README.md           # 이 파일
├── _scripts/           # 파이프라인 코드
├── _state/
│   └── covered.json    # {repo: 마지막 커버일} (30일 dedup용)
└── <owner>-<repo>-<YYYYMMDD>/
    ├── post.md         # 발행할 한국어 글
    └── source.json     # 생성에 사용된 enriched 데이터 (감사/재현용)
```

## CLI

```bash
# 정상 실행 (Hermes가 호출)
python3 _scripts/pipeline.py

# 사이드 이펙트 없이 dry-run
python3 _scripts/pipeline.py --dry-run

# 특정 repo 강제 처리 (dedup·threshold 무시)
python3 _scripts/pipeline.py --force owner/repo
```

## 외부 발행

본 파이프라인은 **git에 글을 두기까지** 책임진다. 외부 플랫폼(Tistory, Velog,
자체 사이트 등) 발행은 사용자가 수동으로 처리하거나, 추후 publisher 컴포넌트로
분리한다.

## 환경 요구

- Python 3.9+
- `claude` CLI (Claude Code, 구독 인증 완료)
- `GITHUB_TOKEN` 환경변수 (rate limit 5000/hr; 없어도 60/hr로 동작)

## 테스트

```bash
cd _scripts
python3 -m unittest discover -p "test_*.py"
```

## Spec

설계 문서: `../docs/superpowers/specs/2026-05-05-github-radar-design.md`
```

- [ ] **Step 2: 초기 covered.json 생성**

```bash
cd /Users/jihong/Documents/workspace/blog
mkdir -p github-radar/_state
echo '{}' > github-radar/_state/covered.json
cat github-radar/_state/covered.json
```

Expected: `{}`

- [ ] **Step 3: 전체 통합 dry-run 실행**

```bash
cd github-radar/_scripts
python3 pipeline.py --dry-run
```

Expected:
- "Total: NN items" (HN + Reddit 합)
- "Selected: [...]" (1~5개 repo)
- 각 repo에 대해 enrich + generate 진행
- "[dry-run] would have generated N posts."
- exit 0
- post 폴더가 만들어지지 않음
- `_state/covered.json`이 그대로 `{}`

- [ ] **Step 4: 통합 테스트 결과 정성 확인**

dry-run 출력에서 다음 확인:
- 선정된 레포가 직관적으로 흥미로운가? (deepclaude, llama.cpp 같은 풀랭킹)
- 점수가 합리적인가? (HN 200pts → 약 200점)
- 생성된 글이 한국어로 잘 나오는가? (article_*.md 결과 확인)

문제 있을 시: 임계점·가중치를 spec과 selector.py에서 조정. (지금은 일단 통과).

- [ ] **Step 5: Commit**

```bash
cd /Users/jihong/Documents/workspace/blog
git add github-radar/README.md github-radar/_state/covered.json
git commit -m "$(cat <<'EOF'
add: github-radar README + 초기 covered.json

운영 방식, 폴더 구조, CLI 사용법 명시. 빈 covered.json으로 dedup
상태 시작.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: 첫 실제 발행 (사용자 승인 후)

**Files:**
- Generated: `github-radar/<slug>-<date>/post.md`, `source.json`
- Modified: `github-radar/_state/covered.json`

이 단계는 실제 글을 git에 commit하므로 사용자 명시 승인 필요.

- [ ] **Step 1: 사용자에게 실제 실행 승인 받기**

```
"dry-run 결과 보고 만족스러우면 실제 실행 (--dry-run 빼고) 승인해 주세요.
1~5편의 한국어 글이 commit되고 push됩니다."
```

- [ ] **Step 2: 사용자 승인 시 실제 실행**

```bash
cd /Users/jihong/Documents/workspace/blog/github-radar/_scripts
python3 pipeline.py
```

Expected:
- 발행할 repo들에 대해 enrich + generate + write_post 수행
- `_state/covered.json` 업데이트
- 새 commit 생성: "add: github-radar — N건 (...)"
- push 성공

- [ ] **Step 3: 결과 검증**

```bash
cd /Users/jihong/Documents/workspace/blog
git log -1 --stat
ls github-radar/ | grep -E "^[a-z0-9]+-[a-z0-9.-]+-[0-9]{8}$"
cat github-radar/_state/covered.json
```

Expected:
- 최근 commit에 새 post 폴더 + covered.json 변경 포함
- 폴더 1~5개 (오늘 생성)
- covered.json에 새 repo 항목들

- [ ] **Step 4: 한 글을 직접 열어 품질 검수**

```bash
cat github-radar/<slug>-<date>/post.md | head -50
```

발행 적합 판단 후 → 사용자가 외부 플랫폼에 수동 발행.

---

## Self-Review Checklist (작성 완료 후 인라인)

### Spec coverage 확인

| Spec 섹션 | 구현 task |
|-----------|-----------|
| Goals — 니치/audience/cadence | 전체 (selector + pipeline 동작으로 만족) |
| Non-Goals — publisher/PR/이미지 | 명시적으로 미구현 (deferred) |
| Architecture — pipeline diagram | Task 7 pipeline.py |
| Components — collect.py | Task 1 (이동) + Task 2 (콜러블) |
| Components — selector.py | Task 5 |
| Components — enrich.py | Task 1 (이동, 변경 없음) |
| Components — generate.py | Task 1 + Task 3 |
| Components — pipeline.py | Task 7 |
| File Layout | Task 1 + Task 8 |
| covered.json SSOT | Task 4 (state.py) + Task 8 (초기파일) |
| Selection logic — score 공식 | Task 5 |
| Selection logic — threshold 100, cap 5, 30일 dedup | Task 5 + Task 4 |
| Filter — 별 < 50, archived, fork | Task 7 (passes_filters) |
| Error handling — HN/Reddit 다운 | Task 2 (collect_all 내 try/except) |
| Error handling — claude -p 실패 | Task 7 (per-repo try/except) |
| Error handling — 0 후보 | Task 7 (early return 0) |
| Scheduling 10:30 KST | 본 plan 외부 (Hermes 설정) |
| Testing — POC validated | 본 plan 작성 시점에 이미 완료 |
| Testing — dry-run mode | Task 7 + Task 8 |

### Placeholder scan
- "TBD"/"TODO"/"implement later" 검색: 없음 ✓
- "appropriate error handling" 같은 모호한 표현: 없음 ✓
- 코드 블록 없는 step: 없음 ✓

### Type/symbol consistency
- `collect_all()` (Task 2) → import in pipeline.py (Task 7) ✓
- `enrich(owner, repo)` (기존) → import in pipeline.py (Task 7) ✓
- `generate_article(enriched, social_ctx)` (Task 3) → import in pipeline.py (Task 7) ✓
- `find_social_context(full_name, candidates)` (Task 3) → import in pipeline.py (Task 7) ✓
- `select_repos(candidates, covered_db, ...)` (Task 5) → import in pipeline.py (Task 7) ✓
- `load_covered(path)`, `save_covered(db, path)`, `mark_covered(repo, db, today=None)`, `is_covered(repo, db, cooldown_days, today)` (Task 4) → 사용 in selector.py + pipeline.py ✓
- `make_folder_name(repo, today=None)`, `write_post(parent, folder, article, source)` (Task 6) → import in pipeline.py ✓
- `passes_filters(enriched)` (Task 7) → 자체 모듈 내 사용 ✓

모순 없음.

### 스코프 체크
- 단일 implementation plan으로 적합 ✓
- 9 tasks, 총 ~3시간 추정 (스크립트 작성 + 테스트 + 검증)
