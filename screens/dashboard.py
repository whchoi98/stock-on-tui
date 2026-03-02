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


class DashboardScreen(Screen):
    """Main dashboard screen showing market overview."""

    BINDINGS = [
        Binding("r", "refresh", "Refresh"),
        Binding("tab", "focus_next_section", "Next Section", show=False),
        Binding("shift+tab", "focus_prev_section", "Prev Section", show=False),
    ]

    FOCUS_ORDER = ["stock-tabs", "news-feed"]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._last_us_quotes = []
        self._last_kr_quotes = []
        self._last_indicators = []
        self._last_news = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with VerticalScroll():
            # Economic Indicators at top
            yield Static(" Economic Indicators", classes="section-title")
            yield IndicatorBar(id="indicator-bar")

            # Market Indices Section
            yield Static(" Market Indices", classes="section-title")
            with Horizontal(id="indices-row"):
                with Horizontal(id="us-indices"):
                    yield MarketCard(id="idx-sp500")
                    yield MarketCard(id="idx-nasdaq")
                    yield MarketCard(id="idx-dow")
                with Horizontal(id="kr-indices"):
                    yield MarketCard(id="idx-kospi")
                    yield MarketCard(id="idx-kosdaq")

            # Market Summary + Sector Bar (Insights)
            yield MarketSummary(id="market-summary")
            yield SectorBar(id="sector-bar")

            # Stock Tables in Tabs
            with TabbedContent(id="stock-tabs"):
                with TabPane("US Stocks (50)", id="us-tab"):
                    yield StockTable(market="US", id="us-table")
                with TabPane("KR Stocks (50)", id="kr-tab"):
                    yield StockTable(market="KR", id="kr-table")

            # News Feed at bottom
            yield NewsFeed(id="news-feed")

            # Status bar
            yield Static("Loading data...", id="status-bar")

        yield Footer()

    def on_mount(self) -> None:
        self.load_all_data()
        self.load_news()
        self.set_interval(REFRESH_INTERVAL, self.load_all_data)
        self.set_interval(NEWS_REFRESH_INTERVAL, self.load_news)

    def action_focus_next_section(self) -> None:
        """Cycle focus through main interactive widgets."""
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
        # Find which section is focused
        for i, w in enumerate(focusable):
            if current and (current == w or w.is_ancestor_of(current)):
                nxt = focusable[(i + 1) % len(focusable)]
                nxt.focus()
                return
        focusable[0].focus()

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
                prev = focusable[(i - 1) % len(focusable)]
                prev.focus()
                return
        focusable[-1].focus()

    def action_refresh(self) -> None:
        self.query_one("#status-bar", Static).update("Refreshing...")
        self.load_all_data()
        self.load_news()

    @work(exclusive=True, group="refresh", exit_on_error=False)
    async def load_all_data(self) -> None:
        errors = []

        # Wave 1: indices (small, fast) — show immediately
        w1 = await asyncio.gather(
            asyncio.to_thread(us_stocks.fetch_us_indices),
            asyncio.to_thread(kr_stocks.fetch_kr_indices),
            return_exceptions=True,
        )
        if not isinstance(w1[0], Exception) and w1[0]:
            self._apply_us_indices(w1[0])
        elif isinstance(w1[0], Exception):
            errors.append(f"US Index: {w1[0]}")
        if not isinstance(w1[1], Exception) and w1[1]:
            self._apply_kr_indices(w1[1])
        elif isinstance(w1[1], Exception):
            errors.append(f"KR Index: {w1[1]}")

        # Wave 2: indicators — show immediately
        try:
            inds = await asyncio.to_thread(indicators.fetch_indicators)
            if inds:
                self._last_indicators = inds
                self.query_one("#indicator-bar", IndicatorBar).update_indicators(inds)
        except Exception as e:
            errors.append(f"Indicators: {e}")

        # Wave 3: stock lists (heavy) — parallel with each other
        w3 = await asyncio.gather(
            asyncio.to_thread(us_stocks.fetch_us_quotes, US_STOCKS),
            asyncio.to_thread(kr_stocks.fetch_kr_quotes, KR_STOCKS),
            return_exceptions=True,
        )
        if not isinstance(w3[0], Exception) and w3[0]:
            self._last_us_quotes = w3[0]
            self.query_one("#us-table", StockTable).update_stocks(w3[0])
        elif isinstance(w3[0], Exception):
            errors.append(f"US Stocks: {w3[0]}")
        if not isinstance(w3[1], Exception) and w3[1]:
            self._last_kr_quotes = w3[1]
            self.query_one("#kr-table", StockTable).update_stocks(w3[1])
        elif isinstance(w3[1], Exception):
            errors.append(f"KR Stocks: {w3[1]}")

        # Update market summary & sector bar
        self._update_market_summary()

        # Update status
        now = datetime.now().strftime("%H:%M:%S")
        if errors:
            status = f"Partial update at {now} | Errors: {'; '.join(errors)}"
        else:
            status = f"Updated: {now} | Next refresh in {REFRESH_INTERVAL}s"
        self.query_one("#status-bar", Static).update(status)

        # Wave 4: market caps (background, updates table in-place)
        self.load_market_caps()

    @work(exclusive=True, group="market-caps", exit_on_error=False)
    async def load_market_caps(self) -> None:
        """Fetch market caps and update stock tables."""
        from services.us_stocks import fetch_us_market_caps
        from services.kr_stocks import fetch_kr_market_caps

        us_caps, kr_caps = await asyncio.gather(
            asyncio.to_thread(fetch_us_market_caps, US_STOCKS),
            asyncio.to_thread(fetch_kr_market_caps, KR_STOCKS),
            return_exceptions=True,
        )

        if not isinstance(us_caps, Exception) and us_caps and self._last_us_quotes:
            for q in self._last_us_quotes:
                if q.symbol in us_caps:
                    q.market_cap = us_caps[q.symbol]
            self.query_one("#us-table", StockTable).update_stocks(self._last_us_quotes)

        if not isinstance(kr_caps, Exception) and kr_caps and self._last_kr_quotes:
            for q in self._last_kr_quotes:
                if q.symbol in kr_caps:
                    q.market_cap = kr_caps[q.symbol]
            self.query_one("#kr-table", StockTable).update_stocks(self._last_kr_quotes)


    @work(exclusive=True, group="news", exit_on_error=False)
    async def load_news(self) -> None:
        try:
            news = await asyncio.to_thread(fetch_news, 10)
            if news:
                self._last_news = news
                self.query_one("#news-feed", NewsFeed).update_news(news)
        except Exception as e:
            pass

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

    def _apply_us_indices(self, indices):
        id_map = {"^GSPC": "idx-sp500", "^IXIC": "idx-nasdaq", "^DJI": "idx-dow"}
        for idx in indices:
            widget_id = id_map.get(idx.symbol)
            if widget_id:
                try:
                    self.query_one(f"#{widget_id}", MarketCard).update_data(idx)
                except Exception:
                    pass

    def _apply_kr_indices(self, indices):
        id_map = {"^KS11": "idx-kospi", "^KQ11": "idx-kosdaq"}
        for idx in indices:
            widget_id = id_map.get(idx.symbol)
            if widget_id:
                try:
                    self.query_one(f"#{widget_id}", MarketCard).update_data(idx)
                except Exception:
                    pass

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        table = event.data_table
        if isinstance(table, StockTable):
            stock = table.get_stock_by_key(str(event.row_key.value))
            if stock:
                from screens.detail import DetailScreen
                self.app.push_screen(DetailScreen(stock.symbol, stock.market))

    def on_news_feed_news_selected(self, event: NewsFeed.NewsSelected) -> None:
        from screens.article import ArticleScreen
        self.app.push_screen(ArticleScreen(event.item))
