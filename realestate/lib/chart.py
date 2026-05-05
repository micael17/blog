"""차트 컴포넌트 라이브러리 — matplotlib 기반 정적 PNG.

각 함수는 DataFrame/Series + 출력 경로를 받아 PNG 저장.
디자인 일관성을 위한 공통 스타일 적용.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

# 한글 폰트 (Mac)
plt.rcParams["font.family"] = "AppleGothic"
plt.rcParams["axes.unicode_minus"] = False

# 컬러 팔레트
COLOR_PRIMARY = "#2E5BFF"
COLOR_ACCENT = "#FF6B35"
COLOR_NEUTRAL = "#7A869A"
COLOR_GRID = "#E5E9F0"

DEFAULT_DPI = 130


def _setup_axes(ax: plt.Axes, title: str, xlabel: str = "", ylabel: str = "") -> None:
    ax.set_title(title, fontsize=14, fontweight="bold", pad=12)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=11)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=11)
    ax.grid(axis="y", alpha=0.3, color=COLOR_GRID)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def daily_volume(daily: pd.Series, title: str, out_path: str | Path) -> Path:
    """일별 거래 건수 막대그래프."""
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.bar(daily.index, daily.values, color=COLOR_PRIMARY)
    _setup_axes(ax, title, "거래일", "거래 건수")
    fig.autofmt_xdate()
    fig.tight_layout()
    out = Path(out_path)
    fig.savefig(out, dpi=DEFAULT_DPI)
    plt.close(fig)
    return out


def top_complexes(
    top: pd.DataFrame, title: str, out_path: str | Path, value_col: str = "거래수"
) -> Path:
    """단지 TOP10 가로 막대그래프.

    top : index=단지명, columns에 value_col 포함
    """
    fig, ax = plt.subplots(figsize=(10, 5))
    labels = top.index[::-1].tolist()
    values = top[value_col].values[::-1]
    ax.barh(labels, values, color=COLOR_ACCENT)
    _setup_axes(ax, title, value_col)
    fig.tight_layout()
    out = Path(out_path)
    fig.savefig(out, dpi=DEFAULT_DPI)
    plt.close(fig)
    return out


def price_timeline(
    df: pd.DataFrame, title: str, out_path: str | Path, by_size: bool = True
) -> Path:
    """단지의 거래일별 가격 시계열 (평형별 색 구분 옵션).

    df 컬럼: 거래일, 거래금액_억, [평형]
    """
    fig, ax = plt.subplots(figsize=(11, 5))
    if by_size and "평형" in df.columns and df["평형"].nunique() > 1:
        for size, sub in df.groupby("평형"):
            ax.scatter(
                sub["거래일"], sub["거래금액_억"], label=f"{size}평", s=60, alpha=0.8
            )
        ax.legend(loc="best", frameon=False)
    else:
        ax.scatter(
            df["거래일"], df["거래금액_억"], color=COLOR_PRIMARY, s=60, alpha=0.8
        )
    _setup_axes(ax, title, "거래일", "거래가 (억원)")
    fig.autofmt_xdate()
    fig.tight_layout()
    out = Path(out_path)
    fig.savefig(out, dpi=DEFAULT_DPI)
    plt.close(fig)
    return out


def size_distribution(
    df: pd.DataFrame, title: str, out_path: str | Path
) -> Path:
    """평형별 거래가 분포 박스플롯."""
    fig, ax = plt.subplots(figsize=(10, 5))
    sizes = sorted(df["평형"].dropna().unique())
    data = [df[df["평형"] == s]["거래금액_억"].values for s in sizes]
    bp = ax.boxplot(data, labels=[f"{s}평" for s in sizes], patch_artist=True)
    for patch in bp["boxes"]:
        patch.set_facecolor(COLOR_PRIMARY)
        patch.set_alpha(0.6)
    _setup_axes(ax, title, "평형", "거래가 (억원)")
    fig.tight_layout()
    out = Path(out_path)
    fig.savefig(out, dpi=DEFAULT_DPI)
    plt.close(fig)
    return out


def comparison_bar(
    df: pd.DataFrame,
    title: str,
    out_path: str | Path,
    value_col: str = "평균가_억",
    label_col: str | None = None,
) -> Path:
    """단지 비교 가로 막대 (인근 단지 비교용)."""
    if label_col:
        labels = df[label_col]
    else:
        labels = df.index
    fig, ax = plt.subplots(figsize=(10, max(4, len(df) * 0.4)))
    ax.barh(labels[::-1], df[value_col].values[::-1], color=COLOR_PRIMARY)
    _setup_axes(ax, title, value_col)
    fig.tight_layout()
    out = Path(out_path)
    fig.savefig(out, dpi=DEFAULT_DPI)
    plt.close(fig)
    return out
