"""주간 실거래가 트래커 (월요일 시리즈).

사용 예시
---------
  # 2026년 4월 데이터로 서울 자치구 7곳 분석 (기본)
  python scripts/weekly_tracker.py --ym 202604

  # 자치구 직접 지정
  python scripts/weekly_tracker.py --ym 202604 --regions 강남구,서초구,송파구

  # 슬러그 지정 (출력 폴더명)
  python scripts/weekly_tracker.py --ym 202604 --slug weekly-tracker-20260430

출력
----
  posts/{slug}/
    ├── context.json                  Hermes/Claude Code가 글 쓸 컨텍스트
    ├── chart-volume-by-region.png    자치구별 거래량
    ├── chart-shingo-top.png          신고가 TOP 10
    ├── chart-daily-volume.png        일별 거래량
    └── data.csv                      원본 데이터 (재현성)
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# bootstrap import
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import analyze, chart, lawd, molit_api  # noqa: E402
from scripts._common import df_to_records, post_dir, write_context  # noqa: E402

# 1단계 디폴트: 서울 핵심 7개 자치구
DEFAULT_REGIONS = ["강남구", "서초구", "송파구", "강동구", "마포구", "용산구", "양천구"]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="주간 실거래가 트래커")
    p.add_argument("--ym", required=True, help="대상 월 YYYYMM (예: 202604)")
    p.add_argument(
        "--regions",
        default=",".join(DEFAULT_REGIONS),
        help="자치구 콤마 구분 (기본: 서울 핵심 7곳)",
    )
    p.add_argument(
        "--slug",
        default=None,
        help="출력 폴더명 (기본: weekly-tracker-{YYYYMMDD-of-today})",
    )
    return p.parse_args()


def collect(regions: list[str], ym: str) -> pd.DataFrame:
    """여러 자치구 한 달치 수집 → 합쳐서 DataFrame."""
    frames = []
    for name in regions:
        code = lawd.code_of(name)
        items = molit_api.fetch_month(code, ym)
        df = molit_api.to_dataframe(items)
        if not df.empty:
            df["자치구"] = name
            frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def main() -> int:
    args = parse_args()
    regions = [r.strip() for r in args.regions.split(",") if r.strip()]
    slug = args.slug or f"weekly-tracker-{datetime.now().strftime('%Y%m%d')}"

    print(f"[수집] {len(regions)}개 자치구, {args.ym}")
    df = collect(regions, args.ym)
    if df.empty:
        print("[ERROR] 데이터 없음", file=sys.stderr)
        return 1
    print(f"[OK] {len(df)}건 수신")

    out = post_dir(slug)

    # 1) 자치구별 종합 요약
    region_summary = {
        r: analyze.summarize_region(df[df["자치구"] == r]) for r in regions
    }

    # 2) 신고가 TOP 10 (전 자치구 통합)
    shingo = analyze.shingo_top(df, n=10)

    # 3) 자치구별 거래량 차트
    volume_by_region = (
        analyze.filter_completed(df).groupby("자치구").size().sort_values(ascending=False)
    )
    volume_df = volume_by_region.to_frame(name="거래수")
    chart.top_complexes(
        volume_df,
        f"자치구별 거래량 ({args.ym})",
        out / "chart-volume-by-region.png",
    )

    # 4) 신고가 TOP 차트
    if not shingo.empty:
        top_for_chart = shingo.set_index("단지명")[["거래금액_억"]].rename(
            columns={"거래금액_억": "거래수"}  # chart 함수 재사용
        )
        chart.top_complexes(
            top_for_chart,
            f"신고가 TOP 10 ({args.ym})",
            out / "chart-shingo-top.png",
            value_col="거래수",
        )

    # 5) 일별 거래량 (전 자치구 통합)
    daily = analyze.daily_volume(df)
    if not daily.empty:
        chart.daily_volume(
            daily, f"일별 거래량 ({args.ym})", out / "chart-daily-volume.png"
        )

    # 6) 컨텍스트 JSON
    context = {
        "시리즈": "weekly-tracker",
        "대상_월": args.ym,
        "자치구_목록": regions,
        "총_거래수": int(len(analyze.filter_completed(df))),
        "자치구_요약": region_summary,
        "신고가_TOP10": df_to_records(shingo),
        "자치구별_거래량": volume_by_region.to_dict(),
        "차트_파일": [
            "chart-volume-by-region.png",
            "chart-shingo-top.png",
            "chart-daily-volume.png",
        ],
    }
    ctx_path = write_context(out, context)

    # 7) 원본 CSV 저장
    df.to_csv(out / "data.csv", index=False)

    print(f"[완료] {out}")
    print(f"  컨텍스트: {ctx_path}")
    print(f"  차트 3장 + data.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
