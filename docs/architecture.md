# Architecture

## Overview
Stock-on-TUI는 3-레이어 아키텍처로 구성됨: **Services** (데이터) → **Models** (도메인) → **Screens/Components** (UI)

## Layer Diagram
```
┌─────────────────────────────────────────────┐
│                  UI Layer                    │
│  screens/ (Dashboard, Detail, Article)       │
│  components/ (Chart, Table, Card, Bar, ...)  │
├─────────────────────────────────────────────┤
│               Domain Layer                   │
│  models/stock.py (StockQuote, StockDetail,   │
│                   MarketIndex, Indicator)     │
│  config.py (종목, 섹터, 지표, 매핑)            │
├─────────────────────────────────────────────┤
│              Service Layer                   │
│  services/us_stocks.py   (yfinance)          │
│  services/kr_stocks.py   (pykrx)             │
│  services/indicators.py  (yfinance)          │
│  services/news.py        (httpx RSS)         │
│  services/bedrock.py     (AWS Bedrock AI)    │
│  services/stock_detail_data.py (simulation)  │
└─────────────────────────────────────────────┘
```

## Data Flow

### Dashboard Loading (4-Wave)
```
on_mount()
  └─ load_all_data() [@work group="refresh"]
       ├─ Wave 1: fetch_us_indices + fetch_kr_indices  (parallel, fast)
       ├─ Wave 2: fetch_indicators                      (sequential)
       ├─ Wave 3: fetch_us_quotes + fetch_kr_quotes     (parallel, heavy)
       │    └─ _update_market_summary()  → MarketSummary + SectorBar
       └─ Wave 4: load_market_caps()    [@work group="market-caps"]
  └─ load_news() [@work group="news"]
```

### Detail Loading (Parallel Groups)
```
on_mount()
  ├─ load_detail()           [@work group="detail-refresh"]
  │    ├─ Phase 1: fetch stock detail (price, chart, history)
  │    │    └─ _apply_detail() → returns, related indicators
  │    └─ Phase 2: load_fundamentals() [@work group="fundamentals"]
  ├─ load_company_news()     [@work group="company-news"]
  ├─ load_order_book()       [@work group="order-book"]
  └─ load_investor_trends()  [@work group="investor-trends"]

  [User] 'A' key → load_ai_analysis() [@work group="ai-analysis"]
```

## Screen Navigation
```
DashboardScreen
  ├─ [Row Click] → DetailScreen(symbol, market)
  │                   ├─ [Enter on news] → ArticleScreen(item)
  │                   └─ [B/Escape] → back
  └─ [Enter on news] → ArticleScreen(item)
                         └─ [B/Escape] → back
```

## Key Design Decisions
1. **동기 서비스 + async wrapper**: 서비스 함수는 동기 → `asyncio.to_thread()`로 블로킹 방지
2. **Work Group 배타 실행**: 같은 그룹 내 중복 실행 방지 (`exclusive=True`)
3. **Wave Loading**: UI 반응성 — 가벼운 데이터부터 먼저 렌더링
4. **시뮬레이션 데이터**: 호가/투자자 동향은 실시간 API 없이 seed 기반 시뮬레이션
5. **섹터-지표 매핑**: config.py에서 정적 매핑, 종목 섹터에 따라 관련 경제지표 표시
