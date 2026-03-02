# 대시보드 화면 모듈: 시장 개요, 지수, 종목 테이블, 뉴스 피드를 표시하는 메인 화면
# Dashboard screen module: main screen displaying market overview, indices, stock tables, and news feed

from __future__ import annotations

import asyncio
from datetime import datetime

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static, TabbedContent, TabPane

from components.market_card import MarketCard
from components.market_summary import MarketSummary
from components.sector_bar import SectorBar
from components.stock_table import StockTable
from components.indicators import IndicatorBar
from components.news_feed import NewsFeed
from config import US_STOCKS, KR_STOCKS, REFRESH_INTERVAL, NEWS_REFRESH_INTERVAL
from services import us_stocks, kr_stocks, indicators
from services.news import fetch_news


# 메인 대시보드 화면 클래스: 경제 지표, 시장 지수, 종목 목록, 뉴스를 한 화면에 표시
# Main dashboard screen class: displays economic indicators, market indices, stock lists, and news in one view
class DashboardScreen(Screen):
    """Main dashboard screen showing market overview."""

    # 키 바인딩 설정: r=새로고침, tab/shift+tab=섹션 이동
    # Key bindings: r=refresh, tab/shift+tab=navigate between sections
    BINDINGS = [
        Binding("r", "refresh", "Refresh"),
        Binding("tab", "focus_next_section", "Next Section", show=False),
        Binding("shift+tab", "focus_prev_section", "Prev Section", show=False),
    ]

    # 포커스 순환 순서: 종목 탭 -> 뉴스 피드
    # Focus cycle order: stock tabs -> news feed
    FOCUS_ORDER = ["stock-tabs", "news-feed"]

    # 대시보드 초기화: 캐시 데이터 변수 초기화 / Initialize dashboard: set up cache data variables
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        # 최신 데이터를 캐시하여 다른 화면에서 접근 가능하게 함
        # Cache latest data so other screens can access it
        self._last_us_quotes = []
        self._last_kr_quotes = []
        self._last_indicators = []
        self._last_news = []

    # UI 위젯 구성: 화면에 표시할 모든 위젯을 배치 / Compose UI widgets: lay out all widgets on screen
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with VerticalScroll():
            # 경제 지표 섹션 (상단) / Economic indicators section (top)
            yield Static(" Economic Indicators", classes="section-title")
            yield IndicatorBar(id="indicator-bar")

            # 시장 지수 섹션: 미국(S&P500, NASDAQ, DOW) + 한국(KOSPI, KOSDAQ)
            # Market indices section: US (S&P500, NASDAQ, DOW) + KR (KOSPI, KOSDAQ)
            yield Static(" Market Indices", classes="section-title")
            with Horizontal(id="indices-row"):
                # 미국 주요 지수 카드 / US major index cards
                with Horizontal(id="us-indices"):
                    yield MarketCard(id="idx-sp500")
                    yield MarketCard(id="idx-nasdaq")
                    yield MarketCard(id="idx-dow")
                # 한국 주요 지수 카드 / Korean major index cards
                with Horizontal(id="kr-indices"):
                    yield MarketCard(id="idx-kospi")
                    yield MarketCard(id="idx-kosdaq")

            # 시장 요약 + 섹터 바 (인사이트) / Market summary + sector bar (insights)
            yield MarketSummary(id="market-summary")
            yield SectorBar(id="sector-bar")

            # 종목 테이블 탭: 미국 50종목 / 한국 50종목 / Stock tables in tabs: US 50 stocks / KR 50 stocks
            with TabbedContent(id="stock-tabs"):
                with TabPane("US Stocks (50)", id="us-tab"):
                    yield StockTable(market="US", id="us-table")
                with TabPane("KR Stocks (50)", id="kr-tab"):
                    yield StockTable(market="KR", id="kr-table")

            # 뉴스 피드 (하단) / News feed (bottom)
            yield NewsFeed(id="news-feed")

            # 상태 표시 바 / Status display bar
            yield Static("Loading data...", id="status-bar")

        yield Footer()

    # 화면 마운트 시 데이터 로딩 시작 및 자동 갱신 타이머 설정
    # On screen mount: start data loading and set up auto-refresh timers
    def on_mount(self) -> None:
        self.load_all_data()
        self.load_news()
        # 주기적 자동 갱신 설정 / Set up periodic auto-refresh
        self.set_interval(REFRESH_INTERVAL, self.load_all_data)
        self.set_interval(NEWS_REFRESH_INTERVAL, self.load_news)

    # 다음 섹션으로 포커스 이동 (Tab 키) / Move focus to next section (Tab key)
    def action_focus_next_section(self) -> None:
        """Cycle focus through main interactive widgets."""
        # 포커스 가능한 위젯 목록 수집 / Collect list of focusable widgets
        focusable = []
        for wid in self.FOCUS_ORDER:
            try:
                w = self.query_one(f"#{wid}")
                focusable.append(w)
            except Exception:
                pass
        if not focusable:
            return
        current = self.focused
        # 현재 포커스된 섹션 찾기 / Find which section is focused
        for i, w in enumerate(focusable):
            if current and (current == w or w.is_ancestor_of(current)):
                # 다음 섹션으로 순환 이동 / Cycle to next section
                nxt = focusable[(i + 1) % len(focusable)]
                nxt.focus()
                return
        focusable[0].focus()

    # 이전 섹션으로 포커스 이동 (Shift+Tab 키) / Move focus to previous section (Shift+Tab key)
    def action_focus_prev_section(self) -> None:
        focusable = []
        for wid in self.FOCUS_ORDER:
            try:
                w = self.query_one(f"#{wid}")
                focusable.append(w)
            except Exception:
                pass
        if not focusable:
            return
        current = self.focused
        for i, w in enumerate(focusable):
            if current and (current == w or w.is_ancestor_of(current)):
                # 이전 섹션으로 순환 이동 / Cycle to previous section
                prev = focusable[(i - 1) % len(focusable)]
                prev.focus()
                return
        focusable[-1].focus()

    # 수동 새로고침 액션 (R 키) / Manual refresh action (R key)
    def action_refresh(self) -> None:
        self.query_one("#status-bar", Static).update("Refreshing...")
        self.load_all_data()
        self.load_news()

    # 모든 시장 데이터를 웨이브 방식으로 비동기 로딩 (지수 -> 지표 -> 종목 -> 시가총액)
    # Load all market data asynchronously in waves (indices -> indicators -> stocks -> market caps)
    @work(exclusive=True, group="refresh", exit_on_error=False)
    async def load_all_data(self) -> None:
        errors = []

        # 웨이브 1: 지수 데이터 (가볍고 빠름) — 즉시 표시
        # Wave 1: index data (small, fast) — show immediately
        w1 = await asyncio.gather(
            asyncio.to_thread(us_stocks.fetch_us_indices),
            asyncio.to_thread(kr_stocks.fetch_kr_indices),
            return_exceptions=True,
        )
        # 미국 지수 결과 처리 / Process US index results
        if not isinstance(w1[0], Exception) and w1[0]:
            self._apply_us_indices(w1[0])
        elif isinstance(w1[0], Exception):
            errors.append(f"US Index: {w1[0]}")
        # 한국 지수 결과 처리 / Process KR index results
        if not isinstance(w1[1], Exception) and w1[1]:
            self._apply_kr_indices(w1[1])
        elif isinstance(w1[1], Exception):
            errors.append(f"KR Index: {w1[1]}")

        # 웨이브 2: 경제 지표 — 즉시 표시
        # Wave 2: economic indicators — show immediately
        try:
            inds = await asyncio.to_thread(indicators.fetch_indicators)
            if inds:
                self._last_indicators = inds
                self.query_one("#indicator-bar", IndicatorBar).update_indicators(inds)
        except Exception as e:
            errors.append(f"Indicators: {e}")

        # 웨이브 3: 종목 목록 (데이터 큼) — 미국/한국 병렬 로딩
        # Wave 3: stock lists (heavy data) — US/KR loaded in parallel
        w3 = await asyncio.gather(
            asyncio.to_thread(us_stocks.fetch_us_quotes, US_STOCKS),
            asyncio.to_thread(kr_stocks.fetch_kr_quotes, KR_STOCKS),
            return_exceptions=True,
        )
        # 미국 종목 결과 처리 및 캐시 / Process and cache US stock results
        if not isinstance(w3[0], Exception) and w3[0]:
            self._last_us_quotes = w3[0]
            self.query_one("#us-table", StockTable).update_stocks(w3[0])
        elif isinstance(w3[0], Exception):
            errors.append(f"US Stocks: {w3[0]}")
        # 한국 종목 결과 처리 및 캐시 / Process and cache KR stock results
        if not isinstance(w3[1], Exception) and w3[1]:
            self._last_kr_quotes = w3[1]
            self.query_one("#kr-table", StockTable).update_stocks(w3[1])
        elif isinstance(w3[1], Exception):
            errors.append(f"KR Stocks: {w3[1]}")

        # 시장 요약 및 섹터 바 갱신 / Update market summary & sector bar
        self._update_market_summary()

        # 상태 바 갱신: 성공 시 갱신 시간, 실패 시 에러 메시지 표시
        # Update status bar: show update time on success, error messages on failure
        now = datetime.now().strftime("%H:%M:%S")
        if errors:
            status = f"Partial update at {now} | Errors: {'; '.join(errors)}"
        else:
            status = f"Updated: {now} | Next refresh in {REFRESH_INTERVAL}s"
        self.query_one("#status-bar", Static).update(status)

        # 웨이브 4: 시가총액 (백그라운드에서 로딩 후 테이블 업데이트)
        # Wave 4: market caps (load in background, update tables in-place)
        self.load_market_caps()

    # 시가총액 데이터를 백그라운드에서 로딩하여 종목 테이블에 반영
    # Load market cap data in background and update stock tables
    @work(exclusive=True, group="market-caps", exit_on_error=False)
    async def load_market_caps(self) -> None:
        """Fetch market caps and update stock tables."""
        from services.us_stocks import fetch_us_market_caps
        from services.kr_stocks import fetch_kr_market_caps

        # 미국/한국 시가총액 병렬 로딩 / Load US/KR market caps in parallel
        us_caps, kr_caps = await asyncio.gather(
            asyncio.to_thread(fetch_us_market_caps, US_STOCKS),
            asyncio.to_thread(fetch_kr_market_caps, KR_STOCKS),
            return_exceptions=True,
        )

        # 미국 시가총액을 캐시된 종목 데이터에 병합 후 테이블 갱신
        # Merge US market caps into cached stock data and refresh table
        if not isinstance(us_caps, Exception) and us_caps and self._last_us_quotes:
            for q in self._last_us_quotes:
                if q.symbol in us_caps:
                    q.market_cap = us_caps[q.symbol]
            self.query_one("#us-table", StockTable).update_stocks(self._last_us_quotes)

        # 한국 시가총액을 캐시된 종목 데이터에 병합 후 테이블 갱신
        # Merge KR market caps into cached stock data and refresh table
        if not isinstance(kr_caps, Exception) and kr_caps and self._last_kr_quotes:
            for q in self._last_kr_quotes:
                if q.symbol in kr_caps:
                    q.market_cap = kr_caps[q.symbol]
            self.query_one("#kr-table", StockTable).update_stocks(self._last_kr_quotes)


    # 뉴스 데이터를 비동기로 로딩하여 뉴스 피드 위젯 갱신
    # Load news data asynchronously and update news feed widget
    @work(exclusive=True, group="news", exit_on_error=False)
    async def load_news(self) -> None:
        try:
            news = await asyncio.to_thread(fetch_news, 10)
            if news:
                self._last_news = news
                self.query_one("#news-feed", NewsFeed).update_news(news)
        except Exception as e:
            pass

    # 시장 요약 및 섹터 바를 최신 종목 데이터로 갱신
    # Update market summary and sector bar with latest quote data
    def _update_market_summary(self) -> None:
        """Update MarketSummary and SectorBar with current quote data."""
        us = self._last_us_quotes or []
        kr = self._last_kr_quotes or []
        if us or kr:
            try:
                self.query_one("#market-summary", MarketSummary).update_data(us, kr)
            except Exception:
                pass
            try:
                self.query_one("#sector-bar", SectorBar).update_data(us, kr)
            except Exception:
                pass

    # 미국 지수 데이터를 해당 MarketCard 위젯에 적용 (심볼 -> 위젯 ID 매핑)
    # Apply US index data to corresponding MarketCard widgets (symbol -> widget ID mapping)
    def _apply_us_indices(self, indices):
        id_map = {"^GSPC": "idx-sp500", "^IXIC": "idx-nasdaq", "^DJI": "idx-dow"}
        for idx in indices:
            widget_id = id_map.get(idx.symbol)
            if widget_id:
                try:
                    self.query_one(f"#{widget_id}", MarketCard).update_data(idx)
                except Exception:
                    pass

    # 한국 지수 데이터를 해당 MarketCard 위젯에 적용 (심볼 -> 위젯 ID 매핑)
    # Apply KR index data to corresponding MarketCard widgets (symbol -> widget ID mapping)
    def _apply_kr_indices(self, indices):
        id_map = {"^KS11": "idx-kospi", "^KQ11": "idx-kosdaq"}
        for idx in indices:
            widget_id = id_map.get(idx.symbol)
            if widget_id:
                try:
                    self.query_one(f"#{widget_id}", MarketCard).update_data(idx)
                except Exception:
                    pass

    # 종목 테이블 행 선택 시 상세 화면으로 이동
    # Navigate to detail screen when a stock table row is selected
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        table = event.data_table
        if isinstance(table, StockTable):
            stock = table.get_stock_by_key(str(event.row_key.value))
            if stock:
                from screens.detail import DetailScreen
                self.app.push_screen(DetailScreen(stock.symbol, stock.market))

    # 뉴스 피드 항목 선택 시 기사 화면으로 이동
    # Navigate to article screen when a news feed item is selected
    def on_news_feed_news_selected(self, event: NewsFeed.NewsSelected) -> None:
        from screens.article import ArticleScreen
        self.app.push_screen(ArticleScreen(event.item))
