"""단지 톺아보기 (화·목 시리즈).

한 단지 심층 분석. 자치구의 N개월치 데이터를 누적해 단지 시계열·평형 분포·인근
비교를 만든 후 컨텍스트 JSON을 출력. Hermes/Claude Code가 이 컨텍스트로 글 본문 작성.

사용 예시
---------
  # 강남구 은마아파트, 직전 6개월
  python scripts/apt_deepdive.py --apt 은마 --region 강남구 --months 6

  # 정확 일치 단지명, 12개월
  python scripts/apt_deepdive.py --apt "래미안대치팰리스" --region 강남구 --months 12

출력
----
  posts/apt-{slug}-{MMDD}/
    ├── context.json
    ├── chart-price-timeline.png    시세 추이 (평형별 색)
    ├── chart-size-distribution.png 평형별 거래가 분포
    ├── chart-nearby-comparison.png 인근 단지 비교
    └── data.csv
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# bootstrap import
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import analyze, chart, lawd, molit_api  # noqa: E402
from scripts._common import df_to_records, post_dir, write_context  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="단지 톺아보기")
    p.add_argument("--apt", required=True, help="단지명 (부분 일치)")
    p.add_argument("--region", required=True, help="자치구명 (예: 강남구)")
    p.add_argument(
        "--months", type=int, default=6, help="누적 분석 개월 (기본 6)"
    )
    p.add_argument("--slug", default=None, help="출력 폴더명 (기본: apt-{단지슬러그}-{MMDD})")
    return p.parse_args()


def slugify(text: str) -> str:
    """한국어/영문 → 폴더 슬러그. 한국어는 그대로 유지."""
    t = re.sub(r"\s+", "", text)
    t = re.sub(r"[^\w가-힣\-]", "", t)
    return t[:30]  # 너무 길지 않게


def months_back(n: int) -> list[str]:
    """오늘로부터 n개월치 YYYYMM 리스트 (최신부터 과거 순)."""
    out = []
    today = datetime.today()
    y, m = today.year, today.month
    for _ in range(n):
        m -= 1
        if m == 0:
            m = 12
            y -= 1
        out.append(f"{y}{m:02d}")
    return out


def find_apt_match(df: pd.DataFrame, query: str) -> str | None:
    """부분 일치로 단지명 찾기. 거래수 가장 많은 매칭 단지 반환."""
    if df.empty or "단지명" not in df.columns:
        return None
    matches = df[df["단지명"].str.contains(query, na=False, regex=False)]
    if matches.empty:
        return None
    by_count = matches["단지명"].value_counts()
    return by_count.index[0]


def main() -> int:
    args = parse_args()
    region_code = lawd.code_of(args.region)
    ymds = months_back(args.months)

    print(f"[수집] {args.region}({region_code}) {args.months}개월: {ymds[-1]}~{ymds[0]}")
    df_region = molit_api.fetch_months(region_code, ymds)
    if df_region.empty:
        print("[ERROR] 데이터 없음", file=sys.stderr)
        return 1
    print(f"[OK] 자치구 {len(df_region)}건 수신")

    apt_name = find_apt_match(df_region, args.apt)
    if apt_name is None:
        print(f"[ERROR] '{args.apt}' 단지를 찾지 못함. 자치구 거래에 등장하지 않음.", file=sys.stderr)
        return 2
    print(f"[매칭] '{args.apt}' → '{apt_name}'")

    df_apt = analyze.apt_timeline(df_region, apt_name)
    if df_apt.empty:
        print("[ERROR] 단지 거래 0건", file=sys.stderr)
        return 3

    slug = args.slug or f"apt-{slugify(apt_name)}-{datetime.now().strftime('%m%d')}"
    out = post_dir(slug)

    # 1) 시세 추이 차트 (평형별)
    chart.price_timeline(
        df_apt,
        f"{apt_name} — 시세 추이 ({args.months}개월)",
        out / "chart-price-timeline.png",
    )

    # 2) 평형별 분포 (단지 내 평형이 2개 이상일 때만 의미 있음)
    if df_apt["평형"].nunique() >= 2:
        chart.size_distribution(
            df_apt,
            f"{apt_name} — 평형별 거래가 분포",
            out / "chart-size-distribution.png",
        )

    # 3) 인근 단지 비교
    nearby = analyze.nearby_complexes(df_region, apt_name)
    if not nearby.empty and len(nearby) >= 2:
        chart.comparison_bar(
            nearby.head(8),
            f"{apt_name} 인근 — 평균가 비교 ({args.months}개월)",
            out / "chart-nearby-comparison.png",
            value_col="평균가_억",
        )

    # 4) 컨텍스트 JSON
    context = {
        "시리즈": "apt-deepdive",
        "단지명": apt_name,
        "자치구": args.region,
        "관측_개월": args.months,
        "관측_월": ymds,
        "단지_요약": analyze.apt_summary(df_region, apt_name),
        "거래_타임라인": df_to_records(
            df_apt[["거래일", "평형", "층", "거래금액_억", "거래유형", "매수자"]]
        ),
        "인근_비교": df_to_records(nearby.reset_index().head(10)),
        "차트_파일": [
            "chart-price-timeline.png",
            "chart-size-distribution.png" if df_apt["평형"].nunique() >= 2 else None,
            "chart-nearby-comparison.png" if not nearby.empty else None,
        ],
    }
    context["차트_파일"] = [c for c in context["차트_파일"] if c]
    ctx_path = write_context(out, context)

    # 5) 원본 CSV
    df_apt.to_csv(out / "data.csv", index=False)

    print(f"[완료] {out}")
    print(f"  컨텍스트: {ctx_path}")
    print(f"  차트 {len(context['차트_파일'])}장 + data.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
