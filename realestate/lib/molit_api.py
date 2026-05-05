"""국토교통부 실거래가 OpenAPI 클라이언트.

PoC에서 검증된 엔드포인트와 인증 방식 사용.
- BASE_URL: 서비스명 + operation 명 둘 다 필요
- 키: decoding 형식, requests params에 그대로 (자동 URL encoding)
- 신청 직후엔 401 (활성화 대기), 수 분 후 200 OK
"""
from __future__ import annotations

import os
import time
import xml.etree.ElementTree as ET
from typing import Iterator

import pandas as pd
import requests

BASE_URL = (
    "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"
)

# 응답 필드 → 한글 컬럼 매핑 (필요한 것만)
RENAME_MAP = {
    "aptNm": "단지명",
    "umdNm": "법정동",
    "jibun": "지번",
    "aptDong": "동",
    "excluUseAr": "전용면적",
    "dealYear": "년",
    "dealMonth": "월",
    "dealDay": "일",
    "dealAmount": "거래금액_만원",
    "floor": "층",
    "buildYear": "건축년도",
    "dealingGbn": "거래유형",  # 직거래/중개
    "buyerGbn": "매수자",  # 개인/법인 등
    "slerGbn": "매도자",
    "cdealType": "해제구분",
    "cdealDay": "해제일",
    "estateAgentSggNm": "중개_시군구",
    "rgstDate": "등기일",
    "landLeaseholdGbn": "토지임대부",
    "sggCd": "시군구코드",
}


def _api_key() -> str:
    key = os.environ.get("MOLIT_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "MOLIT_API_KEY 환경변수 없음. "
            "공공데이터포털에서 발급 후 .env 또는 export."
        )
    return key


def fetch_month(
    lawd_cd: str,
    deal_ymd: str,
    *,
    page_size: int = 1000,
    timeout: int = 30,
    retry: int = 2,
) -> list[dict]:
    """한 자치구의 한 달치 아파트 매매 실거래.

    Parameters
    ----------
    lawd_cd : 법정동코드 앞 5자리 (예: '11680' 강남구)
    deal_ymd : 거래년월 YYYYMM (예: '202604')
    page_size : 페이지당 행 수 (최대 1000으로 보임)
    retry : 401·일시 오류 재시도 횟수

    Returns
    -------
    list[dict] : 원본 필드명 그대로의 row 리스트
    """
    key = _api_key()
    all_items: list[dict] = []
    page = 1
    while True:
        params = {
            "serviceKey": key,
            "LAWD_CD": lawd_cd,
            "DEAL_YMD": deal_ymd,
            "numOfRows": page_size,
            "pageNo": page,
        }

        items, total = _call(params, timeout=timeout, retry=retry)
        all_items.extend(items)
        if len(all_items) >= total or not items:
            break
        page += 1

    return all_items


def _call(params: dict, *, timeout: int, retry: int) -> tuple[list[dict], int]:
    last_err: Exception | None = None
    for attempt in range(retry + 1):
        try:
            resp = requests.get(BASE_URL, params=params, timeout=timeout)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
            code = root.findtext(".//resultCode")
            msg = root.findtext(".//resultMsg")
            if code and code != "000":
                raise RuntimeError(f"API error {code}: {msg}")
            items = [
                {c.tag: (c.text or "").strip() for c in it}
                for it in root.findall(".//item")
            ]
            total = int(root.findtext(".//totalCount") or len(items))
            return items, total
        except (requests.HTTPError, requests.Timeout, ET.ParseError) as e:
            last_err = e
            if attempt < retry:
                time.sleep(2**attempt)  # 1, 2, 4초 백오프
            continue
    raise RuntimeError(f"API call failed after retries: {last_err}")


def to_dataframe(items: list[dict]) -> pd.DataFrame:
    """원본 items → 한글 컬럼·올바른 dtype의 DataFrame.

    추가 파생 컬럼:
    - 거래일 (datetime)
    - 거래금액_억 (float, 표시용)
    - 평형 (float, m² → 평)
    """
    if not items:
        return pd.DataFrame()

    df = pd.DataFrame(items)
    df = df.rename(columns={k: v for k, v in RENAME_MAP.items() if k in df.columns})

    if "거래금액_만원" in df.columns:
        df["거래금액_만원"] = (
            df["거래금액_만원"].astype(str).str.replace(",", "").astype(float)
        )
        df["거래금액_억"] = df["거래금액_만원"] / 10000

    for c in ("년", "월", "일", "층", "건축년도"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    if "전용면적" in df.columns:
        df["전용면적"] = pd.to_numeric(df["전용면적"], errors="coerce")
        df["평형"] = (df["전용면적"] / 3.3058).round(1)

    if {"년", "월", "일"}.issubset(df.columns):
        df["거래일"] = pd.to_datetime(
            dict(year=df["년"], month=df["월"], day=df["일"]), errors="coerce"
        )

    return df


def fetch_months(
    lawd_cd: str, ymds: Iterator[str], *, sleep_between: float = 0.3
) -> pd.DataFrame:
    """여러 달치 데이터 누적 수집 (단지 시계열 분석용).

    sleep_between : API rate limit 보호용 호출 간 sleep (초)
    """
    rows: list[dict] = []
    for ymd in ymds:
        rows.extend(fetch_month(lawd_cd, ymd))
        time.sleep(sleep_between)
    return to_dataframe(rows)
