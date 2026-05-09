# blog repo — Claude Code 워커용 가이드

이 repo는 **사용자(jihongkim)의 모든 블로그 포스트가 모이는 private 모노레포**다. Hermes 오케스트레이터가 `claude -p` 로 위임할 때 워커가 이 파일을 자동 로드한다.

## 디렉토리 구조

```
blog/
├── playandplay/              # 티스토리 주식 블로그
│   └── {post-slug}/          # 포스트당 폴더 1개 (공유 images/ 금지)
│       ├── {post-slug}.md
│       ├── thumbnail.png
│       └── chart-*.png
└── 써봄/                      # 네이버 라이프스타일 블로그 (있으면)
    └── {post-slug}/
        ├── {post-slug}.md
        └── ...
```

**필수**: 글마다 폴더 1개. 절대 공유 `images/` 폴더 사용 금지.

## 이미지 호스팅 — `enterprise-agent-assets` (CRITICAL)

이 repo는 **private** 이라 raw.githubusercontent.com이 404를 반환한다. 따라서 모든 이미지는 **public repo `micael17/enterprise-agent-assets`** 에 업로드 후 raw URL로 참조한다.

### Push 순서 (반드시 이 순서)

1. 이미지를 `enterprise-agent-assets` 에 먼저 push
   ```bash
   cd /tmp/enterprise-agent-assets   # 로컬 클론 위치 (작업 전 git pull 필수)
   cp /path/to/image.png images/
   git add -A && git commit -m "add: <설명> image" && git push
   ```
2. md 파일에 이미지 URL 박기 — **반드시 raw URL** (상대경로 금지)
   ```
   ![설명](https://raw.githubusercontent.com/micael17/enterprise-agent-assets/main/images/{filename}.png)
   ```
3. blog repo push
   ```bash
   cd /Users/jihongkim/Documents/workspace/blog
   git add -A && git commit -m "<제목> - 폴더 정리 및 썸네일 추가" && git push
   ```

**썸네일은 md 파일 최상단 (제목 `# ...` 이전)에 삽입.**

## 썸네일 스펙 (Pillow 800x800)

- 폰트: `/System/Library/Fonts/AppleSDGothicNeo.ttc` index=6 (Bold)
- 크기: 800x800 흰 배경
- Line 1: 제목 (검정, 110px)
- Line 2: 날짜 `(YY/M/D)` 형식 (회색, 52px)
- Line 3: 부제 (빨강 RGB 200,40,40, 52px)

생성 위치: `/tmp/gen_thumbnail.py` 작성 후 `python3 /tmp/gen_thumbnail.py` 실행 (Hermes 샌드박스에 Pillow 없음 — 시스템 python 사용).

## 시리즈 prefix (티스토리 playandplay만)

| 유형 | prefix | SEO |
|---|---|---|
| 급등 이슈 | `[급등 이유]` | "종목명 급등이유" |
| 기업 분석 | `[기업 분석]` | "종목명 기업분석" |
| 특집 (비교/심층) | `[특집]` | "종목명A 종목명B 전망" |

종목당 이슈 발생 시 `[급등 이유]` + `[기업 분석]` 두 포스트 동시 작성, 같은 폴더에 저장.

## 말투/구조 룰

이 repo의 가이드는 **파일/폴더/이미지 메커니즘만** 다룬다. 말투·문장구조는 블로그별 Hermes skill 참조:
- 티스토리 playandplay → `~/.hermes/skills/media/blog-post-style/SKILL.md`
- 네이버 써봄 → `~/.hermes/skills/media/sseobom-blog-style/SKILL.md`
