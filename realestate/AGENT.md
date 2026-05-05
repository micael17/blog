# 부동산 블로그 에이전트 — Hermes 운영 매뉴얼

> 이 문서는 **오케스트레이터 Hermes**가 부동산 블로그 콘텐츠를 생산할 때 참고하는 운영 매뉴얼이다. 에이전트(이 디렉토리의 코드)는 **데이터 수집·분석·차트 생성**까지 결정론적으로 처리하고, **글 본문**은 Hermes/Claude Code가 컨텍스트를 읽어 작성한다.

## 1. 에이전트의 역할 분담

```
[Hermes] 기획 (이번 주 시리즈·대상 선정)
   │
   ▼
[에이전트(이 코드)] 결정론적 처리
   ├─ 국토부 API 호출
   ├─ 데이터 정규화·분석
   ├─ 차트 PNG 생성
   └─ 컨텍스트 JSON 출력
   │
   ▼
[Hermes / Claude Code] 글 작성 (창의적)
   ├─ context.json 읽기
   ├─ {persona.md} 톤 적용
   ├─ post.md 작성
   └─ post.html 변환
   │
   ▼
[발행] 네이버 블로그 (수동/반자동)
```

**원칙**: 에이전트는 "사실"을 만든다. 글은 "해석"을 만든다. 사실에 해석을 입히지 않고, 해석에 사실을 박지 않는다.

## 2. 환경 셋업 (최초 1회)

```bash
cd /Users/jihong/blog/realestate

# 1. venv 생성 + 의존성 설치
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. 환경변수 (.env 파일)
cp .env.example .env
# .env 편집해서 MOLIT_API_KEY=발급받은_키 입력

# 3. 키 로드 (매 세션)
source .env  # 또는 export $(cat .env | xargs)
```

API 키 발급: https://www.data.go.kr/data/15126469/openapi.do (무료, 1만건/일).

## 3. 시리즈별 호출 가이드

### 3-1. 월요일 — 주간 실거래가 트래커

**언제 부르나**: 매주 월요일 오전 발행 직전.
**무엇을 보여주나**: 직전 한 달 자치구별 거래량·신고가 핫스팟.

```bash
# 기본: 서울 핵심 7개 자치구 (강남·서초·송파·강동·마포·용산·양천)
python scripts/weekly_tracker.py --ym 202604

# 자치구 직접 지정
python scripts/weekly_tracker.py --ym 202604 --regions 강남구,서초구,송파구

# 폴더명(slug) 지정
python scripts/weekly_tracker.py --ym 202604 --slug weekly-tracker-20260430
```

**출력**: `posts/{slug}/`
- `context.json` — 글 작성 컨텍스트
- `chart-volume-by-region.png` — 자치구별 거래량
- `chart-shingo-top.png` — 신고가 TOP 10
- `chart-daily-volume.png` — 일별 거래량
- `data.csv` — 원본 (재현성)

**context.json 스키마**
```json
{
  "시리즈": "weekly-tracker",
  "대상_월": "202604",
  "자치구_목록": ["강남구", "서초구", ...],
  "총_거래수": 276,
  "자치구_요약": {
    "강남구": {"건수": 190, "평균가_억": 24.79, "최고가_억": 85.3,
              "법인매수_비율": 8.4, "직거래_비율": 2.1, ...}
  },
  "신고가_TOP10": [{"단지명": "...", "거래일": "2026-04-22", "거래금액_억": 85.3, ...}],
  "자치구별_거래량": {"강남구": 190, ...},
  "차트_파일": ["chart-volume-by-region.png", ...]
}
```

### 3-2. 화·목요일 — 단지 톺아보기

**언제 부르나**: 화·목 발행 직전. 화요일은 서울 단지, 목요일은 수도권 단지.
**무엇을 보여주나**: 한 단지의 시세 추이·평형 분포·인근 단지 비교.

```bash
# 강남구 은마, 직전 6개월
python scripts/apt_deepdive.py --apt 은마 --region 강남구 --months 6

# 정확 일치 단지명, 12개월
python scripts/apt_deepdive.py --apt "래미안대치팰리스" --region 강남구 --months 12

# 폴더명 지정
python scripts/apt_deepdive.py --apt 은마 --region 강남구 --slug apt-eunma-0505
```

`--apt`는 부분 일치. 자치구 거래에 등장하는 단지 중 거래수 최다 매칭 단지를 자동 선택.

**출력**: `posts/apt-{slug}-{MMDD}/`
- `context.json`
- `chart-price-timeline.png` — 시세 추이 (평형별 색)
- `chart-size-distribution.png` — 평형별 분포 (단지에 평형 2개+일 때)
- `chart-nearby-comparison.png` — 인근 단지 비교
- `data.csv`

**context.json 스키마**
```json
{
  "시리즈": "apt-deepdive",
  "단지명": "은마",
  "자치구": "강남구",
  "관측_개월": 6,
  "단지_요약": {
    "단지명": "은마", "법정동": "대치동", "건축년도": 1979,
    "거래수": 6, "관측_기간": "2025-11-03 ~ 2026-02-13",
    "평균가_억": 38.91, "최고가_억": 42.0, "최저가_억": 36.4,
    "평형별": {"23.2": {"거래수": 4, "평균가_억": 37.49}, ...}
  },
  "거래_타임라인": [{"거래일": "2025-11-03", "평형": 25.5, "층": 4,
                   "거래금액_억": 41.5, "거래유형": "중개거래", "매수자": "개인"}, ...],
  "인근_비교": [{"단지명": "래미안대치팰리스", "거래수": 6, "평균가_억": 43.57, ...}],
  "차트_파일": ["chart-price-timeline.png", ...]
}
```

## 4. 글 작성 워크플로우 (Hermes / Claude Code)

에이전트가 폴더와 컨텍스트를 만든 후, Hermes는 다음 단계를 따른다.

### 4-1. 컨텍스트 읽기
```python
import json
context = json.load(open("posts/{slug}/context.json"))
```

### 4-2. 톤 가이드 적용
- `_persona.md` 의 "말투 & 페르소나" 섹션 참고
- 분석가 톤. 단정·선동 금지. 데이터 출처 명시.

### 4-3. 글 구조 (시리즈별)

**weekly-tracker** 글 구조:
```
# {YYYY년 M월 N주차} 부동산 실거래 트래커

도입 (1~2문장): 이번주 핵심 시그널 한 줄

## 자치구별 흐름
- 표 + 한 줄 해석 (자치구별 거래량·평균가)
- {chart-volume-by-region.png}

## 이번달 신고가 TOP 10
- 표 (단지·평형·금액·날짜)
- {chart-shingo-top.png}
- 신고가 1~2건의 의미 짚기

## 일별 거래 흐름
- {chart-daily-volume.png}
- 피크일·둔화일 짚기

## 한줄 요약
- 실수요 관점 / 투자 관점

[데이터 출처: 국토부 실거래가 ({YYYY-MM} 신고분 기준)]
```

**apt-deepdive** 글 구조 (`_design.md` 참조):
```
# {단지명} — 데이터로 본 시세·입지·전망

## 단지 개요
- 위치·세대수·건축년도

## 시세 추이
- 평균가, 최고가, 최저가
- {chart-price-timeline.png}

## 평형별 시세
- {chart-size-distribution.png} (해당 시)

## 인근 단지 비교
- 표
- {chart-nearby-comparison.png}

## 실수요 관점
- 학군·교통·생활권 (사용자/Hermes가 외부 지식으로 보강)

## 투자 관점
- 갭·전세가율·재건축 진척 (외부 지식 보강)

## 한줄평
- 실수요: ...
- 투자: ...

[데이터 출처: 국토부 실거래가, {관측_기간}]
```

### 4-4. 파일 저장
```
posts/{slug}/
├── post.md      ← Hermes/Claude Code가 작성
├── post.html    ← .md 변환 (네이버 발행용)
└── thumbnail.png ← 차트 중 하나를 썸네일로 (선택)
```

`.html` 변환은 playandplay에서 쓰는 도구를 재사용 가능 (확인 필요).

## 5. 발행 워크플로우

1. `posts/{slug}/post.html` 복사
2. 네이버 블로그 글쓰기 → HTML 모드 → 붙여넣기
3. 차트 PNG들 본문 위치에 업로드
4. 카테고리 지정·발행

미래에 브라우저 자동화로 이 단계 자동화 가능.

## 6. 출력 폴더 컨벤션

```
posts/
├── weekly-tracker-{YYYYMMDD}/    월요일 시리즈
├── apt-{단지슬러그}-{MMDD}/        화·목 시리즈
├── dongnae-{동명}-{MMDD}/         수요일 (2단계)
├── compare-{X}-vs-{Y}-{MMDD}/    일요일 (2단계)
└── ...
```

playandplay 패턴(`{topic}-{date}/`)과 일관.

## 7. 트러블슈팅

| 증상 | 원인 | 대응 |
|------|------|------|
| `401 Unauthorized` | 키 활성화 대기 | 신청 후 5~10분 대기 후 재시도 |
| `500 Unexpected errors` | 엔드포인트 path 누락 | `/get{서비스명}` 추가 확인 |
| `MOLIT_API_KEY 환경변수 없음` | .env 미로드 | `source .env` 또는 export |
| 단지명 매칭 실패 | 자치구·기간 잘못 | `--region` 확인, `--months` 늘리기 |
| 단지 거래 0건 | 6개월 내 거래 없음 | `--months 12` 등으로 확장 |
| 한글 깨짐 | 폰트 미적용 | mac이면 AppleGothic, 리눅스는 NanumGothic 설치 후 코드 수정 |

## 8. 데이터 한계 (글에서 짚어야 할 점)

- **신고 시차**: 거래 후 30일 이내 신고. 직전 7~10일 거래는 누락 가능.
- **법정동 단위**: API는 자치구 단위로만 호출 가능. 동 단위 분석은 클라이언트 필터링.
- **호가 정보 없음**: 실거래만. 매물 호가는 별도 소스 필요.
- **해제 거래**: `해제구분` 필드로 필터링 (`analyze.filter_completed` 자동 처리).

## 9. 확장 — 새 시리즈 추가 시

새 시리즈를 추가하려면:

1. `lib/analyze.py`에 분석 함수 추가
2. `lib/chart.py`에 필요시 차트 함수 추가 (가능한 재사용)
3. `scripts/{series_name}.py` 진입점 작성 (`weekly_tracker.py` 참조)
4. 본 문서의 "3. 시리즈별 호출 가이드" 섹션에 추가
5. `_design.md` 업데이트

## 10. 참조 문서

- `_design.md` — 시리즈 디자인·인프라·데이터 소스
- `_persona.md` — 톤·타겟·글 구조 템플릿
- `poc/FINDINGS.md` — PoC 검증 결과·API 함정
- `README.md` — 프로젝트 개요

## 11. 디렉토리 맵

```
realestate/
├── _design.md          시리즈 디자인
├── _persona.md         톤·페르소나
├── AGENT.md            (이 문서) Hermes 운영 매뉴얼
├── README.md           프로젝트 개요
├── requirements.txt    의존성
├── .env.example        환경변수 템플릿
├── lib/                재사용 모듈
│   ├── molit_api.py    국토부 API 클라이언트
│   ├── lawd.py         법정동 코드 매핑
│   ├── analyze.py      분석 함수
│   └── chart.py        차트 컴포넌트
├── scripts/            진입점 (시리즈별)
│   ├── weekly_tracker.py
│   └── apt_deepdive.py
├── poc/                PoC (검증 완료, 참조용)
├── data/               월별 자치구 캐시 (gitignore)
└── posts/              발행 콘텐츠
    └── {slug}/
        ├── context.json
        ├── chart-*.png
        ├── data.csv
        └── post.md (Hermes 작성)
```
