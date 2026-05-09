"""
github-radar POC step 3 — generate a Korean blog article from enriched repo data.

Uses `claude -p` (Claude Code CLI in non-interactive mode), so it runs on the
user's existing Claude Code subscription. No ANTHROPIC_API_KEY required.

Usage:
    python3 generate.py enriched_aattaran_deepclaude.json
    python3 generate.py                # auto-picks most recent enriched_*.json
"""

import glob
import json
import os
import subprocess
import sys

MAX_README_CHARS = 30000

PROMPT_TEMPLATE = """당신은 한국 개발자/기획자를 위한 GitHub 트렌드 큐레이터입니다.
영어권에서 화제가 된 GitHub 레포를 한국 독자에게 깊이 있게 설명하는 블로그 글을 씁니다.

# 글쓰기 원칙
- 군더더기 없이 명료. 영어 직역 어투 금지.
- 비전문가(PM/기획자)도 한 눈에 파악 가능한 TL;DR + 개발자가 만족하는 디테일을 동시에.
- 코드/명령어는 ```언어``` 코드 블록으로.
- "~합니다", "~입니다" 일관된 문어체.
- README 영어 표현 직역 금지. 본인이 이해한 내용을 본인의 한국어로.
- 과장 금지. 데이터(별 수, 시점)는 정확히 인용.

---

다음 GitHub 레포를 소개하는 한국어 블로그 글을 작성해주세요.

# 레포 메타데이터
- 이름: {full_name}
- 한 줄 설명: {description}
- 별: {stars:,} / 포크: {forks:,} / 오픈 이슈: {open_issues:,}
- 주 언어: {language}
- 토픽: {topics}
- 라이선스: {license}
- 생성일: {created_at}
- 마지막 푸시: {pushed_at}
- 홈페이지: {homepage}

# 소셜 화제도
- Hacker News: {hn_score} pts, {hn_comments} comments — "{hn_title}"
{reddit_section}

# README 원문
{readme}

---

# 글 작성 형식 (반드시 이 구조)

## (제목 — 50자 이내, 후킹 있게)

### TL;DR
- 3줄. 비개발자도 핵심 파악 가능하게.

### 이게 뭔가
- 1~2문단. 무엇을 하는 도구이고 어떤 가치를 주는지.

### 왜 지금 화제인가
- 1문단. 데이터(별 수, 생성 시점, HN/Reddit 점수) 활용.

### 누가 써야 하나
- 구체적 대상 + 사용 시나리오 2~3개를 bullet로.

### 빠르게 써보기
- 실제 설치/실행 명령어 (코드 블록).
- 5분 안에 결과 확인 가능한 분량.

### 비슷한 도구와 비교
- 1~2개 대안 + 핵심 차별점.

### 한 줄 평
- 솔직한 의견. 적합/유보/비추 중 한 톤.

---

지금 작성 시작:"""


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


def build_header(repo, ctx):
    """Programmatic source-attribution block, injected after the title."""
    parts = [f"⭐ {repo.get('stars', 0):,}"]
    if repo.get("language"):
        parts.append(repo["language"])
    if repo.get("license"):
        parts.append(repo["license"])
    meta = " · ".join(parts)

    lines = [
        f"> **원본 레포**: [{repo['full_name']}]({repo['html_url']}) · {meta}",
    ]
    if ctx["hn_url"] and ctx["hn_score"] > 0:
        lines.append(
            f"> **Hacker News**: "
            f"[{ctx['hn_score']} pts, {ctx['hn_comments']} comments]({ctx['hn_url']})"
        )
    for r in ctx["reddit_posts"][:2]:
        lines.append(
            f"> **Reddit r/{r['subreddit']}**: "
            f"[{r['score']} pts, {r['comments']} comments]({r['permalink']})"
        )
    return "\n".join(lines)


def build_footer(repo, ctx):
    """Reference + disclaimer block, appended at the end."""
    full = repo["full_name"]
    url = repo["html_url"]
    refs = [f"- **GitHub 레포**: [{full}]({url})"]
    if ctx["hn_url"]:
        refs.append(f"- **Hacker News 토론**: {ctx['hn_url']}")
    for r in ctx["reddit_posts"][:3]:
        refs.append(f"- **Reddit r/{r['subreddit']}**: {r['permalink']}")

    refs_block = "\n".join(refs)
    return (
        "---\n\n"
        "### 참고 및 출처\n\n"
        f"{refs_block}\n\n"
        "본 글은 위 GitHub 레포의 README와 소셜 토론(HN/Reddit)을 바탕으로 "
        "한국 독자를 위해 한국어로 정리·분석한 글입니다. "
        "가장 정확한 최신 정보는 원본 레포를 직접 확인해주세요.\n"
    )


def assemble(article_body, repo, ctx):
    """Inject header right after the first '## title' line; append footer."""
    body = article_body.strip()
    parts = body.split("\n", 1)
    title = parts[0]
    rest = parts[1].lstrip("\n") if len(parts) > 1 else ""
    header = build_header(repo, ctx)
    footer = build_footer(repo, ctx)
    return f"{title}\n\n{header}\n\n{rest}\n\n{footer}"


def call_claude_cli(prompt, model="sonnet"):
    cmd = [
        "claude", "-p",
        "--model", model,
        "--tools", "",                    # disable all tools — text generation only
        "--no-session-persistence",       # don't save this run as a resumable session
    ]
    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        input=prompt,
        capture_output=True,
        text=True,
        timeout=600,
    )
    if result.returncode != 0:
        sys.stderr.write(f"\n--- claude stderr ---\n{result.stderr}\n")
        sys.stderr.write(f"--- claude stdout (first 500 chars) ---\n{result.stdout[:500]}\n")
        raise RuntimeError(f"claude CLI failed (exit {result.returncode})")
    return result.stdout


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


if __name__ == "__main__":
    main()
