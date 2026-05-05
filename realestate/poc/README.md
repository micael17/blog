# 부동산 블로그 PoC

데이터 수집·차트 자동화 가능성 검증.

## 검증 항목

- [ ] 국토교통부 실거래가 OpenAPI 호출
- [ ] 데이터 파싱 (XML → pandas)
- [ ] 차트 자동 생성 (matplotlib PNG)
- [ ] 자치구·단지·일자 단위 집계

## 실행

```bash
cd /Users/jihong/blog/realestate/poc
source .venv/bin/activate
export MOLIT_API_KEY='발급받은_인증키'
python fetch_apt_trades.py
```

## API 키 발급

1. https://www.data.go.kr 회원가입
2. "국토교통부_아파트매매 실거래자료" 검색 후 활용신청
3. 일반 인증키(Decoding) 복사 → `MOLIT_API_KEY`로 설정
4. 1일 호출 한도: 10,000건 (무료)

## 출력

`poc/out/` 디렉토리에:
- `{지역}-{년월}-trades.csv` - 원본 데이터
- `{지역}-{년월}-daily-volume.png` - 일별 거래량 차트
- `{지역}-{년월}-top10-complexes.png` - 거래 많은 단지 TOP 10
