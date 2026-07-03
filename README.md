# 옵션 심리 보드

미국 대장주 52종목의 옵션 풋/콜 데이터를 매일 수집해, 초보자도 시장 심리를
한눈에 볼 수 있게 만든 정적 사이트. 개인 학습용이며 투자 조언이 아닙니다.

## 구조
- `collector/` — Python 수집기 (yfinance → 심리 점수 → `site/data/*.json`)
- `site/` — 정적 프론트 (GitHub Pages 서빙 루트)
- `.github/workflows/collect.yml` — 매일 KST 06:10 자동 수집 + 배포

## 로컬 실행
```
pip install -r requirements.txt
python -m pytest -q
python -m collector.collect --tickers NVDA,AAPL   # 부분 수집
python -m http.server 8123 -d site                 # http://localhost:8123
```

## 점수 체계
풋/콜 거래량 비율을 종목별 최근 60일 백분위로 정규화한 0~100점.
이력 20거래일 미만이면 절대값 매핑(0.4→90 ~ 1.6→10) 콜드스타트.
