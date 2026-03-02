# Services Layer

데이터 소스별 동기 함수를 제공하는 서비스 레이어.
모든 함수는 **동기**로 작성하고, 호출부에서 `asyncio.to_thread()`로 감쌈.

## 파일별 역할
- `us_stocks.py` — yfinance 기반 미국 주식 (quotes, indices, detail, fundamentals, market caps)
- `kr_stocks.py` — pykrx 기반 한국 주식 (동일 구조)
- `indicators.py` — yfinance 기반 경제지표 11개
- `news.py` — httpx RSS 뉴스 수집 + 영→한 번역
- `stock_detail_data.py` — 호가/투자자동향 시뮬레이션 (seed 기반)
- `bedrock.py` — AWS Bedrock Claude AI (기사 분석, 종목 분석)

## 규칙
- 외부 API 호출은 반드시 try/except 처리
- Rate limit 대응: retry + exponential backoff
- 반환 타입: `List[Model]` 또는 `Optional[Model]`
