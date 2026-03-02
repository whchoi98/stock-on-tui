# Stock-on-TUI - Claude Code Project Context

## Project Overview
Textual 기반 실시간 글로벌 주식 모니터 TUI 앱.
미국(50종목) + 한국(50종목) 시장을 대시보드, 상세, 뉴스 AI 분석 화면으로 제공.

## Tech Stack
- **Framework**: Textual (Python TUI)
- **Data**: yfinance (US), pykrx (KR), httpx (RSS/scraping)
- **AI**: AWS Bedrock Claude Sonnet 4.6
- **Python**: 3.11+

## Project Structure
```
app.py              # 앱 엔트리포인트 (StockMonitorApp)
config.py           # 종목 목록, 섹터, 지표, RSS 피드, 섹터-지표 매핑
models/stock.py     # StockQuote, StockDetail, MarketIndex, EconomicIndicator
screens/
  dashboard.py      # 메인 대시보드 (시장요약, 섹터바, 테이블, 뉴스)
  detail.py         # 종목 상세 (차트, 호가, 투자자동향, AI분석)
  article.py        # 뉴스 기사 AI 분석
components/
  market_summary.py # 시장 요약 + Top 상승/하락 + 거래량 Top
  sector_bar.py     # 섹터별 등락률 바 (US/KR 분리)
  rich_chart.py     # 가격 차트 (MA5/MA20, 골든/데드크로스)
  stock_table.py    # 주식 데이터테이블
  market_card.py    # 지수 카드
  indicators.py     # 경제지표 바
  news_feed.py      # 뉴스 피드
services/
  us_stocks.py      # 미국 주식 데이터 (yfinance)
  kr_stocks.py      # 한국 주식 데이터 (pykrx)
  indicators.py     # 경제지표 (yfinance)
  news.py           # RSS 뉴스 + 번역
  stock_detail_data.py  # 호가/투자자동향 시뮬레이션
  bedrock.py        # AWS Bedrock AI (기사분석, 종목분석)
styles/app.tcss     # Textual CSS (다크 테마)
```

## Key Patterns
- **Async Work Groups**: `@work(exclusive=True, group="...")` — 그룹별 배타적 실행
- **Wave Loading**: Dashboard 4단계 순차 로딩 (indices → indicators → stocks → market caps)
- **Data Models**: dataclass 기반 (StockQuote=경량, StockDetail=상세)
- **색상 규칙**: 상승 `#F04452` (빨강), 하락 `#3182F6` (파랑)

## Coding Conventions
- `from __future__ import annotations` 모든 파일 상단
- 위젯은 `DEFAULT_CSS` 인라인 또는 `styles/app.tcss`에 정의
- 서비스 레이어는 동기 함수 → `asyncio.to_thread()`로 호출
- 한국어 UI, 영어 코드/변수명

## Commands
```bash
python3 app.py              # 앱 실행
python3 -c "import ast; ast.parse(open('파일').read())"  # 문법 검증
```

## Important Notes
- yfinance API는 Rate limit 있음 → fundamentals 로드 시 retry + backoff
- pykrx는 KRX 거래시간(평일 09:00-15:30 KST) 외 데이터 지연 가능
- Bedrock는 us-east-1 리전, AWS credentials 필요
- 호가/투자자동향은 시뮬레이션 데이터
