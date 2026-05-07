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
