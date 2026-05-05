# 부동산 블로그

데이터 기반 부동산 분석 블로그 프로젝트. 국토부 실거래가 등 공공 데이터를 자동 수집·분석·시각화해 일일 콘텐츠를 생산한다.

## 빠른 시작

```bash
# 1. 셋업
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # MOLIT_API_KEY 입력

# 2. 주간 실거래가 트래커
python scripts/weekly_tracker.py --ym 202604

# 3. 단지 톺아보기
python scripts/apt_deepdive.py --apt 은마 --region 강남구 --months 6
```

출력: `posts/{slug}/` — 차트·데이터·컨텍스트 JSON.

## 문서

- **[_design.md](./_design.md)** — 시리즈 디자인, 인프라, 데이터 소스, 출범 로드맵
- **[_persona.md](./_persona.md)** — 타겟 독자, 톤, 글 구조 템플릿
- **[AGENT.md](./AGENT.md)** — Hermes(오케스트레이터) 운영 매뉴얼
- **[poc/FINDINGS.md](./poc/FINDINGS.md)** — PoC 검증 결과

## 구조

```
realestate/
├── lib/         재사용 모듈 (API·분석·차트)
├── scripts/     진입점 (시리즈별 CLI)
├── posts/       발행 콘텐츠 (시리즈별 폴더)
├── poc/         초기 검증 (참조용)
└── data/        월별 자치구 캐시 (gitignore)
```

## 라이선스 / 데이터 출처

- 부동산 실거래가: 국토교통부 (data.go.kr)
- 코드: 개인 프로젝트, 라이선스 미정
