"""실거래 데이터 분석 함수 — 시리즈별 인사이트 추출.

각 함수는 DataFrame을 받아 해석 가능한 dict 또는 DataFrame 반환.
LLM이 읽고 글 쓸 수 있는 컨텍스트 생성이 목적.
"""
from __future__ import annotations

import pandas as pd


def filter_completed(df: pd.DataFrame) -> pd.DataFrame:
    """해제 거래 제외. 가격 분석엔 항상 이걸 통과시킴."""
    if "해제구분" not in df.columns:
        return df
    return df[df["해제구분"].fillna("").str.strip() == ""].copy()


def summarize_region(df: pd.DataFrame) -> dict:
    """자치구·월 단위 종합 요약 (월요일 트래커용)."""
    df = filter_completed(df)
    if df.empty:
        return {"건수": 0}

    return {
        "건수": int(len(df)),
        "유니크_단지": int(df["단지명"].nunique()),
        "평균가_억": round(df["거래금액_억"].mean(), 2),
        "중간가_억": round(df["거래금액_억"].median(), 2),
        "최고가_억": round(df["거래금액_억"].max(), 2),
        "최저가_억": round(df["거래금액_억"].min(), 2),
        "평균_평형": round(df["평형"].mean(), 1),
        "직거래_비율": round(
            (df["거래유형"].fillna("").str.contains("직거래")).mean() * 100, 1
        )
        if "거래유형" in df.columns
        else None,
        "법인매수_비율": round(
            (df["매수자"].fillna("").str.contains("법인")).mean() * 100, 1
        )
        if "매수자" in df.columns
        else None,
    }


def top_complexes(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """거래 많은 단지 TOP N. (단지명, 거래수, 평균가, 최고가)."""
    df = filter_completed(df)
    if df.empty:
        return pd.DataFrame()
    grouped = (
        df.groupby("단지명")
        .agg(
            거래수=("거래금액_억", "count"),
            평균가_억=("거래금액_억", "mean"),
            최고가_억=("거래금액_억", "max"),
            평균_평형=("평형", "mean"),
        )
        .round(2)
        .sort_values("거래수", ascending=False)
        .head(n)
    )
    return grouped


def shingo_top(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """단지·평형별 신고가 TOP N (해당 월에 가장 비싼 거래)."""
    df = filter_completed(df)
    if df.empty:
        return pd.DataFrame()
    return (
        df[["단지명", "평형", "거래일", "거래금액_억", "층", "법정동", "건축년도"]]
        .sort_values("거래금액_억", ascending=False)
        .head(n)
        .reset_index(drop=True)
    )


def daily_volume(df: pd.DataFrame) -> pd.Series:
    """일별 거래 건수 시계열."""
    df = filter_completed(df)
    if df.empty:
        return pd.Series(dtype=int)
    return df.groupby("거래일").size().sort_index()


def apt_timeline(df: pd.DataFrame, apt_name: str) -> pd.DataFrame:
    """특정 단지 거래 타임라인. 화·목 시리즈(단지 톺아보기)용."""
    df = filter_completed(df)
    sub = df[df["단지명"] == apt_name].copy()
    if sub.empty:
        return pd.DataFrame()
    return sub.sort_values("거래일").reset_index(drop=True)


def apt_summary(df: pd.DataFrame, apt_name: str) -> dict:
    """단지 종합 요약 (LLM이 글 쓸 컨텍스트)."""
    sub = apt_timeline(df, apt_name)
    if sub.empty:
        return {"단지명": apt_name, "거래수": 0}

    by_size = (
        sub.groupby("평형")
        .agg(거래수=("거래금액_억", "count"), 평균가_억=("거래금액_억", "mean"))
        .round(2)
    )
    return {
        "단지명": apt_name,
        "법정동": sub["법정동"].mode().iloc[0] if not sub["법정동"].empty else None,
        "건축년도": int(sub["건축년도"].mode().iloc[0])
        if not sub["건축년도"].empty
        else None,
        "거래수": int(len(sub)),
        "관측_기간": f"{sub['거래일'].min().date()} ~ {sub['거래일'].max().date()}",
        "평균가_억": round(sub["거래금액_억"].mean(), 2),
        "최고가_억": round(sub["거래금액_억"].max(), 2),
        "최저가_억": round(sub["거래금액_억"].min(), 2),
        "평형별": by_size.to_dict(orient="index"),
    }


def nearby_complexes(
    df_region: pd.DataFrame,
    target_apt: str,
    *,
    size_tolerance_pct: float = 15.0,
) -> pd.DataFrame:
    """타겟 단지와 같은 법정동에서 비슷한 평형의 단지들 시세 비교용 표.

    size_tolerance_pct : 평형 ±x% 이내 단지만 비교 대상
    """
    df = filter_completed(df_region)
    target = df[df["단지명"] == target_apt]
    if target.empty:
        return pd.DataFrame()
    target_sizes = target["평형"].dropna().unique()
    if len(target_sizes) == 0:
        return pd.DataFrame()
    median_size = pd.Series(target_sizes).median()
    low = median_size * (1 - size_tolerance_pct / 100)
    high = median_size * (1 + size_tolerance_pct / 100)

    same_dong = df[df["법정동"].isin(target["법정동"].unique())]
    similar_size = same_dong[(same_dong["평형"] >= low) & (same_dong["평형"] <= high)]

    return (
        similar_size.groupby("단지명")
        .agg(
            거래수=("거래금액_억", "count"),
            평균가_억=("거래금액_억", "mean"),
            평균_평형=("평형", "mean"),
            평균_건축년도=("건축년도", "mean"),
        )
        .round(2)
        .sort_values("평균가_억", ascending=False)
    )
