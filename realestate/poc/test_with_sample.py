"""
PoC 보조: API 응답 형식의 sample로 normalize + chart 파이프라인 검증.

실제 API 호출 전에 데이터 처리·차트 생성 부분이 잘 작동하는지 미리 확인.
실 API 응답과 동일한 XML 필드 구조 사용.
"""
import pandas as pd
from pathlib import Path

from fetch_apt_trades import normalize, chart_daily_volume, chart_top_complexes

# 국토부 OpenAPI 응답 구조에 맞춘 sample (강남구 2026-04 가상)
SAMPLE_RAW = [
    # 은마아파트 5건
    {"aptNm": "은마", "umdNm": "대치동", "dealAmount": "320,000",
     "dealYear": "2026", "dealMonth": "4", "dealDay": "3",
     "excluUseAr": "76.79", "floor": "5", "buildYear": "1979"},
    {"aptNm": "은마", "umdNm": "대치동", "dealAmount": "335,000",
     "dealYear": "2026", "dealMonth": "4", "dealDay": "8",
     "excluUseAr": "84.43", "floor": "11", "buildYear": "1979"},
    {"aptNm": "은마", "umdNm": "대치동", "dealAmount": "342,000",
     "dealYear": "2026", "dealMonth": "4", "dealDay": "15",
     "excluUseAr": "84.43", "floor": "8", "buildYear": "1979"},
    {"aptNm": "은마", "umdNm": "대치동", "dealAmount": "318,000",
     "dealYear": "2026", "dealMonth": "4", "dealDay": "22",
     "excluUseAr": "76.79", "floor": "3", "buildYear": "1979"},
    {"aptNm": "은마", "umdNm": "대치동", "dealAmount": "350,000",
     "dealYear": "2026", "dealMonth": "4", "dealDay": "28",
     "excluUseAr": "84.43", "floor": "12", "buildYear": "1979"},
    # 래미안대치팰리스 3건
    {"aptNm": "래미안대치팰리스", "umdNm": "대치동", "dealAmount": "510,000",
     "dealYear": "2026", "dealMonth": "4", "dealDay": "5",
     "excluUseAr": "84.95", "floor": "15", "buildYear": "2015"},
    {"aptNm": "래미안대치팰리스", "umdNm": "대치동", "dealAmount": "525,000",
     "dealYear": "2026", "dealMonth": "4", "dealDay": "18",
     "excluUseAr": "84.95", "floor": "22", "buildYear": "2015"},
    {"aptNm": "래미안대치팰리스", "umdNm": "대치동", "dealAmount": "498,000",
     "dealYear": "2026", "dealMonth": "4", "dealDay": "25",
     "excluUseAr": "59.99", "floor": "8", "buildYear": "2015"},
    # 압구정현대 4건
    {"aptNm": "압구정현대", "umdNm": "압구정동", "dealAmount": "780,000",
     "dealYear": "2026", "dealMonth": "4", "dealDay": "10",
     "excluUseAr": "131.48", "floor": "7", "buildYear": "1976"},
    {"aptNm": "압구정현대", "umdNm": "압구정동", "dealAmount": "820,000",
     "dealYear": "2026", "dealMonth": "4", "dealDay": "16",
     "excluUseAr": "131.48", "floor": "10", "buildYear": "1976"},
    {"aptNm": "압구정현대", "umdNm": "압구정동", "dealAmount": "750,000",
     "dealYear": "2026", "dealMonth": "4", "dealDay": "20",
     "excluUseAr": "108.20", "floor": "5", "buildYear": "1976"},
    {"aptNm": "압구정현대", "umdNm": "압구정동", "dealAmount": "850,000",
     "dealYear": "2026", "dealMonth": "4", "dealDay": "27",
     "excluUseAr": "131.48", "floor": "13", "buildYear": "1976"},
    # 도곡렉슬 2건
    {"aptNm": "도곡렉슬", "umdNm": "도곡동", "dealAmount": "285,000",
     "dealYear": "2026", "dealMonth": "4", "dealDay": "12",
     "excluUseAr": "84.92", "floor": "20", "buildYear": "2006"},
    {"aptNm": "도곡렉슬", "umdNm": "도곡동", "dealAmount": "292,000",
     "dealYear": "2026", "dealMonth": "4", "dealDay": "24",
     "excluUseAr": "84.92", "floor": "25", "buildYear": "2006"},
    # 타워팰리스 2건
    {"aptNm": "타워팰리스", "umdNm": "도곡동", "dealAmount": "450,000",
     "dealYear": "2026", "dealMonth": "4", "dealDay": "9",
     "excluUseAr": "164.97", "floor": "30", "buildYear": "2002"},
    {"aptNm": "타워팰리스", "umdNm": "도곡동", "dealAmount": "475,000",
     "dealYear": "2026", "dealMonth": "4", "dealDay": "21",
     "excluUseAr": "164.97", "floor": "42", "buildYear": "2002"},
]


def main():
    print(f"[Sample] {len(SAMPLE_RAW)}건의 가상 데이터로 파이프라인 검증")

    df = pd.DataFrame(SAMPLE_RAW)
    df = normalize(df)

    print(f"[정규화 후 컬럼] {sorted(df.columns.tolist())}")
    print("\n[처리된 데이터]")
    print(df[["단지명", "법정동", "거래일", "전용면적", "거래금액_만원", "층"]].to_string(index=False))

    out_dir = Path(__file__).parent / "out"
    out_dir.mkdir(exist_ok=True)

    chart_daily_volume(df, "강남구 일별 거래량 (sample)", out_dir / "sample-daily-volume.png")
    chart_top_complexes(df, "강남구 거래 TOP 단지 (sample)", out_dir / "sample-top-complexes.png")

    print(f"\n[차트 저장]")
    print(f"  {out_dir / 'sample-daily-volume.png'}")
    print(f"  {out_dir / 'sample-top-complexes.png'}")

    print("\n[통계]")
    print(f"  단지 수: {df['단지명'].nunique()}")
    print(f"  거래 건수: {len(df)}")
    print(f"  평균가: {df['거래금액_만원'].mean():,.0f}만원")


if __name__ == "__main__":
    main()
