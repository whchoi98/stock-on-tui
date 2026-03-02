# Stock-on-TUI

Textual 기반 실시간 글로벌 주식 모니터 TUI 앱

미국 50종목 + 한국 50종목의 시세, 차트, 호가, 투자자 동향, AI 분석을 터미널에서 한눈에 확인할 수 있습니다.

## Screenshots

| Dashboard | Detail |
|-----------|--------|
| ![Dashboard](dashboard.png) | ![Detail](detail.png) |

## Features

### Dashboard
- **경제지표 바**: WTI, Gold, USD/KRW, US 10Y, Bitcoin 등 11개 지표
- **시장 지수**: S&P 500, NASDAQ, DOW, KOSPI, KOSDAQ
- **시장 요약**: US/KR 상승·하락 종목수, Top 상승/하락 (종목명+거래량), 거래량 Top
- **섹터 등락**: US/KR 섹터별 평균 등락률 바 차트
- **주식 테이블**: 50종목 (Symbol, Name, Price, Change, %, Mkt Cap, Volume)
- **뉴스 피드**: Yahoo Finance + 한경/매경 RSS

### Detail (종목 상세)
- **가격 헤더**: 현재가, 등락률, 거래량(평균 대비 배율)
- **핵심 지표**: Market Cap, PER, EPS, Beta/PBR, Volume, Avg Volume
- **차트**: 1W/1M/3M/1Y 기간별 Sparkline + MA5/MA20 (골든/데드크로스)
- **호가**: 매수/매도 10단계
- **투자자 동향**: 개인/외국인/기관 10일간 추이
- **기간별 수익률**: 1W, 1M, 3M, 1Y 수익률
- **관련 지표**: 섹터 기반 경제지표 상관관계
- **AI 종목 분석**: Bedrock Claude를 통한 기술적 분석/투자 포인트/리스크 (`A` 키)

### Article (뉴스 AI 분석)
- 뉴스 기사 전문 + Claude AI 요약/분석/투자 인사이트

## Getting Started

### Prerequisites
- Python 3.11+
- AWS credentials (Bedrock AI 기능 사용 시)

### Installation
```bash
git clone <repo-url>
cd stock-on-tui
pip install -r requirements.txt
```

### Run
```bash
python3 app.py
```

## Key Bindings

### Dashboard
| Key | Action |
|-----|--------|
| `R` | 데이터 새로고침 |
| `Tab` / `Shift+Tab` | 섹션 이동 |
| `Enter` / Click | 종목 상세 |
| `Q` | 종료 |

### Detail
| Key | Action |
|-----|--------|
| `1` `2` `3` `4` | 차트 기간 (1W/1M/3M/1Y) |
| `Left` / `Right` / `P` | 차트 기간 전환 |
| `A` | AI 종목 분석 토글 |
| `Enter` | 뉴스 AI 분석 |
| `R` | 새로고침 |
| `B` / `Escape` | 뒤로 |

## Architecture

```
app.py ─── DashboardScreen ─┬─ MarketSummary (시장요약)
                             ├─ SectorBar (섹터등락)
                             ├─ StockTable (종목테이블)
                             └─ NewsFeed (뉴스)
       ─── DetailScreen ────┬─ RichChart (차트+MA)
                             ├─ OrderBook (호가)
                             ├─ InvestorTrends (투자자)
                             ├─ Returns (수익률)
                             ├─ RelatedIndicators (관련지표)
                             └─ AI Analysis (종목분석)
       ─── ArticleScreen ──── AI Article Analysis
```

## Dependencies
- `textual` >= 0.40.0 — TUI framework
- `yfinance` >= 0.2.31 — US stock data
- `pykrx` >= 1.0.45 — KR stock data
- `httpx` >= 0.25.0 — HTTP client (RSS, scraping)
- `boto3` — AWS Bedrock (AI analysis)

## License
MIT
