# github-radar — Design Spec

**Date:** 2026-05-05
**Status:** Brainstorming complete, awaiting user approval before implementation planning.

## Overview

github-radar는 영어권에서 화제가 된 GitHub 레포를 매일 자동으로 수집·분석해 한국어 블로그 글로 만드는 콘텐츠 파이프라인이다. 결과물은 git 저장소에 커밋되고, 외부 플랫폼 발행은 사용자가 수동으로 처리한다.

## Goals

- **Niche**: AI/LLM + 개발자 생산성 도구 (선정 로직이 자연스럽게 이 분야로 편향되도록 소스 선택)
- **Audience**: 한국 개발자 + 기획자/PM. 글 한 편이 두 독자를 모두 만족시키도록 layered 구조 (TL;DR for skimmers, deep dive for engineers)
- **Cadence**: 매일 1회 실행, **데이터 품질에 따라 0~5편 가변 발행**
- **Operating model**: 자동 생성 → git 커밋. 외부 플랫폼 발행은 사용자가 검토 후 수동 처리
- **Cost target**: 한계 비용 0원 (Claude Code 구독 기반 `claude -p` 사용)

## Non-Goals (현 단계)

- 외부 플랫폼 자동 발행 (Tistory/Velog/자체 사이트) — 추후 publisher 컴포넌트로 분리
- PR 기반 리뷰 워크플로우 — 사용자가 main 브랜치 직접 검수
- 썸네일/이미지 자동 생성
- 한국어 커버리지 교차 참조 (GeekNews dedup)
- Tier 2/3 소스 추가 (TLDR AI, HuggingFace, arXiv 등)
- 영어 버전 글 동시 생성

## Architecture

```
[Hermes cron @ 10:30 KST 매일]
       ↓
  pipeline.py
       ↓
┌──────────────────────────────────────────────────────┐
│                                                      │
│  1. collect      HN(Algolia) + Reddit(4 subs)        │
│       ↓                                              │
│  2. select       dedup(30일) + score + threshold     │
│       ↓                                              │
│  (for each selected repo, 0~5개)                     │
│       ↓                                              │
│  3. enrich       GitHub API → metadata + README      │
│       ↓                                              │
│  4. generate     claude -p → 본문                    │
│                  + header/footer 결정적 주입         │
│       ↓                                              │
│  5. commit       <slug>-<YYYYMMDD>/ 폴더 생성        │
│                  + covered.json 업데이트 + push      │
│                                                      │
└──────────────────────────────────────────────────────┘
       ↓
   사용자 검수 → 외부 플랫폼 발행 (별도 흐름)
```

## Components

### `_scripts/collect.py`

이미 POC에서 검증됨.
- HN: Algolia search API, `query=github.com&tags=story`, 최근 48h
- Reddit: `/r/{sub}/hot.json`, subs = `LocalLLaMA, MachineLearning, programming, selfhosted`
- Output: dict with `hn`, `reddit`, `multi_source` keys (in-memory, 또는 임시 JSON 파일)

### `_scripts/select.py` (NEW)

후보 풀에서 발행할 레포(들)를 결정.

**Inputs:** collect 결과 + `_state/covered.json`

**Filtering (스킵 조건):**
- `covered.json`에 등재되어 있고 마지막 커버일로부터 30일 이내
- 별 수 < 50 (너무 신상)
- archived, fork
- bot/joke repo 의심 (description에 `parody`, `joke` 등)

**Scoring formula:**

```
score = hn_points * 1.0
      + reddit_points * 0.5
      + (50 if appears_in_multiple_sources else 0)
      + (20 if description_matches_niche_keywords else 0)
```

`niche_keywords`: `ai, llm, agent, model, claude, gpt, mcp, rag, llama, devtool, cli, automation, ide` 등.

**Threshold + Cap:**
- 최소 점수 100점 미만은 스킵
- 점수 내림차순 상위 **최대 5개** 선택
- 0개도 정상 결과 (그날 발행 0편)

**Output:** 선정된 repo full_name 리스트.

### `_scripts/enrich.py`

POC에서 검증됨. 각 선정된 레포에 대해:
- `GET /repos/{owner}/{repo}` (메타데이터)
- `GET /repos/{owner}/{repo}/readme` → `download_url` raw fetch
- `GET /repos/{owner}/{repo}/languages`
- `GITHUB_TOKEN` 사용 (rate limit 60 → 5000/hr)

Output: `enriched_<owner>_<repo>.json` (post 폴더에 `source.json`으로 최종 저장)

### `_scripts/generate.py`

POC에서 검증됨.
- `claude -p --model sonnet --tools "" --no-session-persistence`
- 프롬프트: layered 한국어 블로그 구조 (TL;DR / 이게 뭔가 / 왜 화제 / 누가 써야 / 빠르게 써보기 / 비교 / 한 줄 평)
- Body 생성 후 코드에서 결정적으로 헤더(원본 URL) + 풋터(참고 출처) 주입 — 모델이 URL 환각하지 않도록 보장

### `_scripts/pipeline.py` (NEW)

Hermes에서 호출하는 단일 진입점.

**Pseudocode:**
```python
def main():
    candidates = collect()                       # 1
    selected = select(candidates, covered_db)    # 2
    if not selected:
        log("no candidates above threshold today")
        return 0

    successes = []
    for repo_full_name in selected:
        try:
            enriched = enrich(repo_full_name)        # 3
            article = generate(enriched, ctx)        # 4
            commit_post(repo_full_name, article, enriched)  # 5
            update_covered(repo_full_name)
            successes.append(repo_full_name)
        except Exception as e:
            log_error(repo_full_name, e)
            continue  # 다음 레포 진행

    if successes:
        git_push()
    return 0 if successes or not selected else 1
```

**플래그:**
- `--dry-run` : 수집·선정·생성까지 하지만 커밋·푸시 안 함 (개발/디버그용)
- `--force <repo>` : dedup 무시하고 특정 레포 강제 처리

## File Layout

```
blog/                                    # 기존 모노레포 루트
├── docs/superpowers/specs/
│   └── 2026-05-05-github-radar-design.md   # 본 문서
├── playandplay/                         # 기존 블로그 (변경 없음)
├── github-radar/                        # 신규 블로그
│   ├── README.md                        # 블로그 소개 + 운영 방식
│   ├── _scripts/
│   │   ├── collect.py
│   │   ├── select.py
│   │   ├── enrich.py
│   │   ├── generate.py
│   │   └── pipeline.py
│   ├── _state/
│   │   └── covered.json                 # {"owner/repo": "YYYY-MM-DD"}
│   └── <owner>-<repo>-<YYYYMMDD>/       # 각 발행 글
│       ├── post.md                      # 헤더 + 본문 + 풋터
│       └── source.json                  # enriched 원본 (재현/감사)
```

**`covered.json` 예시:**
```json
{
  "aattaran/deepclaude": "2026-05-05",
  "ggml-org/llama.cpp": "2026-05-04"
}
```

**폴더명 규칙:**
- `<owner>-<repo>-<YYYYMMDD>` (slash → dash)
- 같은 레포가 30일 후 재커버되면 새 날짜로 새 폴더 생성

**State는 git에 커밋:** Mac mini와 사용자 노트북 등 분산 환경에서 단일 진실 소스(SSOT) 유지를 위해.

## Data Flow & State

매 실행마다:
1. 새 candidates 풀 수집 (영구 저장 안 함, in-memory)
2. `_state/covered.json` 읽어 dedup 필터 적용
3. 선정된 각 레포: enrich → generate → 새 폴더에 `post.md` + `source.json` 저장
4. `_state/covered.json` 업데이트
5. 모든 신규 파일 git add + commit + push

**커밋 메시지 컨벤션:**
```
add: github-radar — <owner>/<repo> (N stars, HN N pts)
```
다중 발행 시 단일 커밋에 묶음.

## Error Handling

| 실패 시나리오 | 동작 |
|---------------|------|
| HN Algolia API 다운 | 경고 로그, Reddit만으로 진행 |
| Reddit API 다운 | 경고 로그, HN만으로 진행 |
| HN+Reddit 둘 다 다운 | exit 1, Hermes에 에러 |
| 임계점 100점 이상 후보 0 | exit 0, "no commit today" 로그 |
| GitHub API 429 | 지수 백오프 후 1회 재시도, 그래도 실패 시 해당 레포 스킵 |
| `claude -p` 실패 | 해당 레포 스킵, enriched.json은 디버그용 임시 보존 |
| 부분 실패 (5개 중 3개 성공) | 성공한 것만 커밋, 실패한 건 다음 날 재시도 가능 |

**관찰성:**
- 모든 로그 stdout (Hermes가 캡처)
- exit 0 = "정상 종료 (글 0편 이상 생성)"
- exit 1 = "인프라 장애 (둘 다 다운, 스크립트 버그 등)"

## Scheduling

- **Cron 시간**: 10:30 KST 매일
- **이유**: 07:10 KST 미국 브리핑과 14:30~18:00 KST 주식 분석 사이의 빈 슬롯. 미국 시장 마감(05:30 KST) + HN 활동 안정화 후 시점.
- **Hermes 호출**: `cd blog && python3 github-radar/_scripts/pipeline.py`

## Testing

**현 단계 (POC 완료):**
- collect: 2026-05-05 실데이터로 114 candidates 수집 검증
- enrich: aattaran/deepclaude로 메타+README 검증
- generate: claude -p 호출 → 한국어 글 3,374자 생성 검증
- header/footer 주입: deterministic, 환각 0

**구현 후 추가할 검증:**
- `--dry-run` 모드: 첫 1주일 매일 dry-run으로 어떤 레포가 픽되는지 모니터링
- 점수 가중치 캘리브레이션: 1~2주 후 좋은 픽/나쁜 픽 사례 보고 조정
- 회귀 테스트: 고정된 candidates fixture에 대해 select.py가 일관된 결과를 내는지

## Future Extensions

운영 안정화 후 검토:

1. **Publisher 컴포넌트** — Tistory/Velog/자체 사이트에 자동 발행. main 머지 webhook으로 트리거.
2. **Tier 2 소스 추가** — TLDR AI 아카이브, HuggingFace Trending, Papers With Code.
3. **GeekNews 역참조** — "한국에서 이미 다뤄진 것"을 제외해 차별화.
4. **AI 큐레이션 점수** — Claude로 "이 레포가 한국 개발자에게 newsworthy한가" 사전 평가.
5. **글 한 편당 비교 도구 자동 발견** — README에 "같은 카테고리 도구 X와 비교" 자동 첨부.
6. **뉴스레터 발송** — git에 누적된 글을 주간 다이제스트로 묶어 Stibee/Substack 자동 발송.
7. **다국어 버전** — 영어 버전을 같은 폴더에 `post.en.md`로 생성, dev.to/Medium 동시 발행.

## Open Questions

없음. 구현 단계로 진행 가능.
