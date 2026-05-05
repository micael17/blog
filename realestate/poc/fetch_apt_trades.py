"""
PoC: 국토교통부 실거래가 OpenAPI 호출 검증

검증 항목
1. API 호출이 실제로 되는가
2. 응답 형식 / 필요한 필드가 다 나오는가
3. pandas로 파싱·집계 가능한가
4. matplotlib으로 차트 자동 생성 가능한가

사용법
- 환경변수 MOLIT_API_KEY 설정 후 실행
  (공공데이터포털에서 "국토교통부_아파트매매 실거래자료" 신청 → 일반 인증키)
- python fetch_apt_trades.py
"""
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import requests

# 한글 폰트 (mac)
plt.rcParams["font.family"] = "AppleGothic"
plt.rcParams["axes.unicode_minus"] = False

API_KEY = os.environ.get("MOLIT_API_KEY", "").strip()
BASE_URL = (
    "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"
)

OUT_DIR = Path(__file__).parent / "out"
OUT_DIR.mkdir(exist_ok=True)


def fetch_apt_trades(lawd_cd: str, deal_ymd: str) -> list[dict]:
    """한 자치구의 한 달치 아파트 매매 실거래 조회.

    lawd_cd: 법정동코드 앞 5자리 (강남구 11680, 서초구 11650, 송파구 11710...)
    deal_ymd: 거래년월 YYYYMM
    """
    if not API_KEY:
        print("[ERROR] MOLIT_API_KEY 환경변수 없음.")
        print("        공공데이터포털에서 무료 발급 필요:")
        print("        https://www.data.go.kr/data/15126469/openapi.do")
        sys.exit(2)

    params = {
        "serviceKey": API_KEY,
        "LAWD_CD": lawd_cd,
        "DEAL_YMD": deal_ymd,
        "numOfRows": 1000,
        "pageNo": 1,
    }

    print(f"[GET] {BASE_URL}")
    print(f"      LAWD_CD={lawd_cd}, DEAL_YMD={deal_ymd}")

    resp = requests.get(BASE_URL, params=params, timeout=30)
    resp.raise_for_status()

    root = ET.fromstring(resp.content)

    # 응답 코드 체크
    result_code = root.findtext(".//resultCode")
    result_msg = root.findtext(".//resultMsg")
    print(f"      resultCode={result_code} resultMsg={result_msg}")
    if result_code and result_code != "000":
        raise RuntimeError(f"API error: {result_code} {result_msg}")

    items = root.findall(".//item")
    return [{c.tag: (c.text or "").strip() for c in it} for it in items]


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """필드명·타입 정규화."""
    rename_map = {
        "aptNm": "단지명",
        "umdNm": "법정동",
        "jibun": "지번",
        "excluUseAr": "전용면적",
        "dealYear": "년",
        "dealMonth": "월",
        "dealDay": "일",
        "dealAmount": "거래금액_만원",
        "floor": "층",
        "buildYear": "건축년도",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    if "거래금액_만원" in df.columns:
        df["거래금액_만원"] = (
            df["거래금액_만원"].astype(str).str.replace(",", "").astype(float)
        )
    if "전용면적" in df.columns:
        df["전용면적"] = pd.to_numeric(df["전용면적"], errors="coerce")
    for c in ("년", "월", "일", "층", "건축년도"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    if {"년", "월", "일"}.issubset(df.columns):
        df["거래일"] = pd.to_datetime(
            dict(year=df["년"], month=df["월"], day=df["일"]), errors="coerce"
        )
    return df


def chart_daily_volume(df: pd.DataFrame, title: str, out_path: Path) -> None:
    daily = df.groupby("거래일").size()
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.bar(daily.index, daily.values, color="#2E5BFF")
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_xlabel("거래일")
    ax.set_ylabel("거래 건수")
    ax.grid(axis="y", alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def chart_top_complexes(df: pd.DataFrame, title: str, out_path: Path) -> None:
    top = (
        df.groupby("단지명")["거래금액_만원"]
        .agg(["count", "mean"])
        .sort_values("count", ascending=False)
        .head(10)
    )
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.barh(top.index[::-1], top["count"].values[::-1], color="#FF6B35")
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_xlabel("거래 건수")
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def main() -> int:
    # 강남구 직전 달 (PoC: 2026-04)
    lawd_cd = "11680"
    deal_ymd = "202604"
    region = "강남구"

    trades = fetch_apt_trades(lawd_cd, deal_ymd)
    print(f"[OK] {len(trades)}건 수신")

    if not trades:
        print("[WARN] 빈 결과")
        return 1

    df = pd.DataFrame(trades)
    print(f"[원본 컬럼] {sorted(df.columns.tolist())}")

    df = normalize(df)
    print(f"[정규화 컬럼] {sorted(df.columns.tolist())}")
    print("\n[샘플 3건]")
    print(
        df[["단지명", "전용면적", "거래일", "거래금액_만원", "층"]]
        .head(3)
        .to_string(index=False)
    )

    # 차트 1: 일별 거래량
    out1 = OUT_DIR / f"{region}-{deal_ymd}-daily-volume.png"
    chart_daily_volume(df, f"{region} 일별 거래량 ({deal_ymd})", out1)
    print(f"\n[차트 저장] {out1}")

    # 차트 2: 거래 많은 단지 TOP 10
    out2 = OUT_DIR / f"{region}-{deal_ymd}-top10-complexes.png"
    chart_top_complexes(df, f"{region} 거래 TOP 10 단지 ({deal_ymd})", out2)
    print(f"[차트 저장] {out2}")

    # 통계 요약
    print("\n[자치구 요약]")
    print(f"  총 거래: {len(df)}건")
    print(f"  유니크 단지: {df['단지명'].nunique()}곳")
    print(f"  평균 거래가: {df['거래금액_만원'].mean():,.0f}만원")
    print(f"  최고가: {df['거래금액_만원'].max():,.0f}만원")
    print(f"  최저가: {df['거래금액_만원'].min():,.0f}만원")

    # CSV로도 저장 (재현성)
    csv_path = OUT_DIR / f"{region}-{deal_ymd}-trades.csv"
    df.to_csv(csv_path, index=False)
    print(f"\n[CSV 저장] {csv_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
