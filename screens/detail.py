from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional, List

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Footer, Header, ListView, ListItem, ProgressBar, Static, DataTable,
)

from components.rich_chart import RichChart
from config import SECTOR_INDICATOR_MAP, INDICATORS
from models.stock import StockDetail
from services.news import NewsItem
from services.stock_detail_data import (
    OrderBookEntry, InvestorRow,
    fetch_order_book, fetch_investor_trends,
)


class InfoCard(Static):
    DEFAULT_CSS = "InfoCard { width: 1fr; height: 2; padding: 0 2; }"

    def set_info(self, label: str, value: str, color: str = "") -> None:
        text = Text()
        text.append(f"{label}: ", style="dim")
        text.append(value, style=f"bold {color}" if color else "bold")
        self.update(text)


class NewsListItem(ListItem):
    DEFAULT_CSS = "NewsListItem { height: 2; padding: 0 2; }"

    def __init__(self, item: NewsItem, **kwargs):
        super().__init__(**kwargs)
        self.news_item = item

    def compose(self):
        text = Text()
        color = "#3182F6" if self.news_item.is_korean else "#F04452"
        text.append(f"[{self.news_item.source}] ", style=f"bold {color}")
        text.append(self.news_item.title[:80], style="")
        yield Static(text)


class Week52Bar(Vertical):
    DEFAULT_CSS = """
    Week52Bar { height: auto; padding: 1 2; border: solid $surface-lighten-2; margin: 0 2; }
    Week52Bar ProgressBar { height: 1; margin: 0 1; }
    Week52Bar .range-labels { height: 1; }
    """

    def compose(self):
        yield Static("52 Week Range", classes="range-title")
        with Horizontal(classes="range-labels"):
            yield Static("", id="w52-low")
            yield Static("", id="w52-high")
        yield ProgressBar(total=100, show_eta=False, show_percentage=False, id="w52-bar")

    def update_range(self, low, high, current, currency="USD"):
        fmt = ",.0f" if currency == "KRW" else ",.2f"
        pfx = "" if currency == "KRW" else "$"
        self.query_one("#w52-low", Static).update(f"Low {pfx}{low:{fmt}}")
        self.query_one("#w52-high", Static).update(f"High {pfx}{high:{fmt}}")
        pct = ((current - low) / (high - low) * 100) if high > low else 50
        self.query_one("#w52-bar", ProgressBar).update(progress=pct)


class DetailScreen(Screen):
    BINDINGS = [
        Binding("b", "go_back", "Back"),
        Binding("escape", "go_back", "Back"),
        Binding("r", "refresh", "Refresh"),
        Binding("p", "next_period", "Next Period"),
        Binding("1", "period_1w", "1W", show=False),
        Binding("2", "period_1m", "1M", show=False),
        Binding("3", "period_3m", "3M", show=False),
        Binding("4", "period_1y", "1Y", show=False),
        Binding("left", "prev_period", "Prev Period", show=False),
        Binding("right", "next_period_arrow", "Next Period", show=False),
        Binding("a", "toggle_ai", "AI Analysis"),
    ]

    def __init__(self, symbol: str, market: str = "US", **kwargs):
        super().__init__(**kwargs)
        self._symbol = symbol
        self._market = market
        self._detail: Optional[StockDetail] = None
        self._news: List[NewsItem] = []
        self._order_book: List[OrderBookEntry] = []
        self._investor_rows: List[InvestorRow] = []
        self._ob_loaded = False
        self._inv_loaded = False
        self._ai_result: str = ""
        self._ai_loading = False
        self._ai_visible = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with VerticalScroll():
            # ── Header ──
            yield Static("", id="detail-title")
            yield Static("Loading...", id="price-header")
            yield Static("", id="price-sub")
            yield Static(
                "  Market Cap: 시가총액  PER: 주가수익비율  EPS: 주당순이익"
                "  Beta/PBR: 변동성/주가순자산  Vol: 당일거래량  Avg Vol: 평균거래량",
                id="api-notice",
            )

            # ── 시세 Key Metrics ──
            with Horizontal(id="metrics-row"):
                yield InfoCard(id="m-mktcap")
                yield InfoCard(id="m-per")
                yield InfoCard(id="m-eps")
                yield InfoCard(id="m-beta")
                yield InfoCard(id="m-vol")
                yield InfoCard(id="m-avgvol")

            # ── 차트 ──
            yield RichChart(id="chart-panel")

            # ── 호가 + 시세/투자자 (좌우 배치) ──
            with Horizontal(id="mid-row"):
                # 호가 (왼쪽)
                with Vertical(id="ob-section"):
                    yield Static(" 호가", classes="section-title")
                    yield Static("Loading...", id="ob-status")
                    yield DataTable(id="ob-table")

                # 시세 + 투자자 (오른쪽)
                with Vertical(id="quote-inv-section"):
                    # 시세
                    with Horizontal(id="info-row"):
                        with Vertical(id="price-info", classes="info-box"):
                            yield Static(" Price Info", classes="box-title")
                            yield InfoCard(id="info-open")
                            yield InfoCard(id="info-high")
                            yield InfoCard(id="info-low")
                            yield InfoCard(id="info-prev")
                        with Vertical(id="trading-info", classes="info-box"):
                            yield Static(" Trading Info", classes="box-title")
                            yield InfoCard(id="info-volume")
                            yield InfoCard(id="info-avg-vol")
                            yield InfoCard(id="info-day-range")
                            yield InfoCard(id="info-sector")
                    yield Week52Bar(id="w52-range")

                    # 기간별 수익률
                    yield Static("", id="period-returns")

                    # 투자자
                    yield Static(" 투자자 동향", classes="section-title")
                    yield Static("Loading...", id="inv-status")
                    yield DataTable(id="inv-table")

            # ── 관련 지표 ──
            yield Static("", id="related-indicators")

            # ── AI 종목 분석 ──
            yield Static("", id="ai-analysis")

            # ── 뉴스 (하단) ──
            yield Static(" Company News  [Enter] AI Analysis  [A] AI 종목분석", classes="section-title")
            yield ListView(id="company-news")

            yield Static("Loading...", id="detail-status")
        yield Footer()

    def on_mount(self):
        # Setup table columns
        ob = self.query_one("#ob-table", DataTable)
        ob.add_columns("매도잔량", "가격", "매수잔량")
        ob.cursor_type = "row"
        inv = self.query_one("#inv-table", DataTable)
        inv.add_columns("날짜", "개인", "외국인", "기관")
        inv.cursor_type = "row"
        # Load all data in parallel
        self.load_detail()
        self.load_company_news()
        self.load_order_book()
        self.load_investor_trends()

    def action_go_back(self):
        self.dismiss()

    def action_refresh(self):
        self.query_one("#detail-status", Static).update("Refreshing...")
        self._ob_loaded = False
        self._inv_loaded = False
        self.load_detail()
        self.load_company_news()
        self.load_order_book()
        self.load_investor_trends()

    def action_next_period(self):
        self.query_one("#chart-panel", RichChart).next_period()

    def action_next_period_arrow(self):
        self.query_one("#chart-panel", RichChart).next_period()

    def action_prev_period(self):
        self.query_one("#chart-panel", RichChart).prev_period()

    def action_period_1w(self):
        self.query_one("#chart-panel", RichChart).set_period("1W")

    def action_period_1m(self):
        self.query_one("#chart-panel", RichChart).set_period("1M")

    def action_period_3m(self):
        self.query_one("#chart-panel", RichChart).set_period("3M")

    def action_period_1y(self):
        self.query_one("#chart-panel", RichChart).set_period("1Y")

    @work(exclusive=True, group="detail-refresh", exit_on_error=False)
    async def load_detail(self):
        # Phase 1: fast data (price, chart, basic info)
        if self._market == "US":
            from services.us_stocks import fetch_us_stock_detail
            detail = await asyncio.to_thread(fetch_us_stock_detail, self._symbol)
        else:
            from services.kr_stocks import fetch_kr_stock_detail
            detail = await asyncio.to_thread(fetch_kr_stock_detail, self._symbol)

        if detail is None:
            self.query_one("#detail-status", Static).update("Failed to load. Press R to retry.")
            return
        self._detail = detail
        self._apply_detail(detail)

        # Phase 2: fundamentals (PE/EPS/Div/Beta/MarketCap) — background
        self.load_fundamentals()

    @work(exclusive=True, group="fundamentals", exit_on_error=False)
    async def load_fundamentals(self):
        """Load PE/EPS/Div/Beta with retry on rate limit."""
        for attempt in range(4):
            if attempt > 0:
                await asyncio.sleep(5 * attempt)  # 5s, 10s, 15s backoff

            if self._market == "US":
                from services.us_stocks import fetch_us_fundamentals
                data = await asyncio.to_thread(fetch_us_fundamentals, self._symbol)
            else:
                from services.kr_stocks import fetch_kr_fundamentals
                data = await asyncio.to_thread(fetch_kr_fundamentals, self._symbol)

            if data and self._detail:
                d = self._detail
                if "market_cap" in data:
                    d.market_cap = data["market_cap"]
                if "pe_ratio" in data:
                    d.pe_ratio = data["pe_ratio"]
                if "eps" in data:
                    d.eps = data["eps"]
                if "beta" in data:
                    d.beta = data["beta"]
                self._apply_fundamentals(d)
                return  # Success

        # All retries failed — show N/A
        if self._detail:
            self._apply_fundamentals(self._detail)

    @work(exclusive=True, group="company-news", exit_on_error=False)
    async def load_company_news(self):
        from services.news import fetch_company_news
        name = self._symbol
        if self._detail:
            name = self._detail.name
        news = await asyncio.to_thread(fetch_company_news, self._symbol, name, self._market, 8)
        self._news = news
        lv = self.query_one("#company-news", ListView)
        lv.clear()
        for item in news:
            lv.append(NewsListItem(item))

    @work(exclusive=True, group="order-book", exit_on_error=False)
    async def load_order_book(self):
        entries = await asyncio.to_thread(fetch_order_book, self._symbol, self._market)
        self._order_book = entries
        self._ob_loaded = True
        self._apply_order_book(entries)

    @work(exclusive=True, group="investor-trends", exit_on_error=False)
    async def load_investor_trends(self):
        rows = await asyncio.to_thread(fetch_investor_trends, self._symbol, self._market, 10)
        self._investor_rows = rows
        self._inv_loaded = True
        self._apply_investor_trends(rows)

    def _apply_order_book(self, entries: List[OrderBookEntry]):
        table = self.query_one("#ob-table", DataTable)
        table.clear()
        status = self.query_one("#ob-status", Static)

        if not entries:
            status.update("호가 데이터를 불러올 수 없습니다.")
            return
        status.update("")

        asks = sorted([e for e in entries if not e.is_bid], key=lambda e: e.price)
        bids = sorted([e for e in entries if e.is_bid], key=lambda e: -e.price)

        is_krw = self._market == "KR"
        fmt = ",.0f" if is_krw else ",.2f"

        # Ask rows (sell) - highest first
        for e in reversed(asks):
            vol_bar = "█" * min(20, max(1, e.volume // 100))
            table.add_row(
                Text(f"{vol_bar} {e.volume:,}", style="#3182F6"),
                Text(f"{e.price:{fmt}}", style="#3182F6 bold"),
                Text(""),
            )

        # Bid rows (buy) - highest first
        for e in bids:
            vol_bar = "█" * min(20, max(1, e.volume // 100))
            table.add_row(
                Text(""),
                Text(f"{e.price:{fmt}}", style="#F04452 bold"),
                Text(f"{e.volume:,} {vol_bar}", style="#F04452"),
            )

    def _apply_investor_trends(self, rows: List[InvestorRow]):
        table = self.query_one("#inv-table", DataTable)
        table.clear()
        status = self.query_one("#inv-status", Static)

        if not rows:
            status.update("투자자 데이터를 불러올 수 없습니다.")
            return
        status.update("")

        def _colored_vol(v: int) -> Text:
            if v > 0:
                return Text(f"+{v:,}", style="#F04452 bold")
            elif v < 0:
                return Text(f"{v:,}", style="#3182F6 bold")
            return Text("0", style="dim")

        for r in rows:
            table.add_row(r.date, _colored_vol(r.individual), _colored_vol(r.foreign), _colored_vol(r.institution))

    def action_toggle_ai(self):
        """Toggle AI stock analysis."""
        from services.bedrock import is_bedrock_available, _DISABLED_MSG
        if not is_bedrock_available():
            self.query_one("#ai-analysis", Static).update(_DISABLED_MSG)
            return
        if self._ai_loading:
            return
        if self._ai_visible and self._ai_result:
            # Hide
            self._ai_visible = False
            self.query_one("#ai-analysis", Static).update("")
            return
        if self._ai_result:
            # Show cached result
            self._ai_visible = True
            self._show_ai_result()
            return
        # Load from Bedrock
        self._ai_loading = True
        self.query_one("#ai-analysis", Static).update(" AI 종목 분석 로딩중...")
        self.load_ai_analysis()

    @work(exclusive=True, group="ai-analysis", exit_on_error=False)
    async def load_ai_analysis(self):
        from services.bedrock import analyze_stock
        d = self._detail
        if not d:
            self._ai_loading = False
            return
        news_titles = [n.title for n in self._news[:5]]
        result = await asyncio.to_thread(
            analyze_stock,
            symbol=d.symbol,
            name=d.name,
            price=d.price,
            change_pct=d.change_pct,
            pe_ratio=d.pe_ratio,
            week52_high=d.week52_high,
            week52_low=d.week52_low,
            sector=d.sector,
            market=d.market,
            news_titles=news_titles,
        )
        self._ai_result = result
        self._ai_loading = False
        self._ai_visible = True
        self._show_ai_result()

    def _show_ai_result(self):
        text = Text()
        text.append("\n AI 종목 분석  ", style="bold #FFD700")
        text.append("[A] 토글\n", style="dim")
        text.append(self._ai_result, style="")
        self.query_one("#ai-analysis", Static).update(text)

    def on_list_view_selected(self, event: ListView.Selected):
        if isinstance(event.item, NewsListItem):
            from screens.article import ArticleScreen
            self.app.push_screen(ArticleScreen(event.item.news_item))

    def _apply_detail(self, d: StockDetail):
        color = "#F04452" if d.is_positive else "#3182F6"
        sign = "+" if d.change >= 0 else ""
        fmt = ",.0f" if d.currency == "KRW" else ",.2f"
        pfx = "" if d.currency == "KRW" else "$"
        sfx = "원" if d.currency == "KRW" else ""
        arrow = "▲" if d.change > 0 else "▼" if d.change < 0 else "-"

        title = Text()
        title.append(f"  {d.symbol}", style="bold")
        title.append(f"  {d.name}", style="")
        self.query_one("#detail-title", Static).update(title)

        header = Text()
        header.append(f"  {pfx}{d.price:{fmt}}{sfx} ", style=f"bold {color}")
        header.append(f" {arrow} {sign}{d.change:{fmt}} ({sign}{d.change_pct:.2f}%)", style=color)
        header.append(f"   Vol: {self._fmt_vol(d.volume)}", style="bold")
        if d.avg_volume and d.avg_volume > 0:
            ratio = d.volume / d.avg_volume
            vol_color = "#F04452" if ratio >= 1.5 else "#FFD700" if ratio >= 1.0 else "dim"
            header.append(f" ({ratio:.1f}x avg)", style=vol_color)
        self.query_one("#price-header", Static).update(header)

        sub = Text()
        if d.sector:
            sub.append(f"  Sector: {d.sector}", style="dim")
        sub.append(f"  |  Market: {'NYSE/NASDAQ' if d.market == 'US' else 'KRX'}", style="dim")
        self.query_one("#price-sub", Static).update(sub)

        self._apply_fundamentals(d)

        chart = self.query_one("#chart-panel", RichChart)
        chart.set_all_data(
            d.history_7d, d.history_30d, d.history_90d, d.history_1y,
            d.history_dates_7d, d.history_dates_30d, d.history_dates_90d, d.history_dates_1y,
        )

        self.query_one("#info-open", InfoCard).set_info("Open", f"{pfx}{d.open_price:{fmt}}")
        self.query_one("#info-high", InfoCard).set_info("High", f"{pfx}{d.high:{fmt}}", "#F04452")
        self.query_one("#info-low", InfoCard).set_info("Low", f"{pfx}{d.low:{fmt}}", "#3182F6")
        self.query_one("#info-prev", InfoCard).set_info("Prev Close", f"{pfx}{d.prev_close:{fmt}}")
        self.query_one("#info-volume", InfoCard).set_info("Volume", self._fmt_vol(d.volume))
        self.query_one("#info-avg-vol", InfoCard).set_info("Avg Vol", self._fmt_vol(d.avg_volume))
        self.query_one("#info-day-range", InfoCard).set_info("Day Range", f"{pfx}{d.low:{fmt}} - {pfx}{d.high:{fmt}}")
        self.query_one("#info-sector", InfoCard).set_info("Sector", d.sector or "N/A")

        self.query_one("#w52-range", Week52Bar).update_range(d.week52_low, d.week52_high, d.price, d.currency)

        # Period returns
        self._apply_returns(d)
        # Related indicators
        self._apply_related_indicators(d)

        now = datetime.now().strftime("%H:%M:%S")
        self.query_one("#detail-status", Static).update(
            f"Updated: {now} | [1]1W [2]1M [3]3M [4]1Y [<>]Period | [Enter]News AI | [B]Back"
        )

    def _apply_returns(self, d: StockDetail):
        """Show period returns: 1W, 1M, 3M, 1Y."""
        text = Text()
        text.append("  수익률: ", style="bold")

        periods = [
            ("1W", d.history_7d),
            ("1M", d.history_30d),
            ("3M", d.history_90d),
            ("1Y", d.history_1y),
        ]
        for label, hist in periods:
            if hist and len(hist) >= 2:
                ret = (d.price - hist[0]) / hist[0] * 100 if hist[0] else 0
                sign = "+" if ret >= 0 else ""
                color = "#F04452" if ret >= 0 else "#3182F6"
                text.append(f"{label} ", style="dim")
                text.append(f"{sign}{ret:.1f}%", style=f"bold {color}")
                text.append("  |  ", style="dim")
            else:
                text.append(f"{label} ", style="dim")
                text.append("N/A", style="dim")
                text.append("  |  ", style="dim")

        self.query_one("#period-returns", Static).update(text)

    def _apply_related_indicators(self, d: StockDetail):
        """Show related economic indicators based on sector."""
        sector = d.sector
        if not sector:
            return

        indicator_symbols = SECTOR_INDICATOR_MAP.get(sector, [])
        if not indicator_symbols:
            return

        # Try to get indicator data from dashboard's cached data
        cached_indicators = []
        try:
            from screens.dashboard import DashboardScreen
            for screen in self.app.screen_stack:
                if isinstance(screen, DashboardScreen):
                    cached_indicators = getattr(screen, "_last_indicators", [])
                    break
        except Exception:
            pass

        if not cached_indicators:
            return

        # Build lookup by symbol
        ind_map = {ind.symbol: ind for ind in cached_indicators}

        text = Text()
        text.append("\n 관련 지표  ", style="bold")

        found_any = False
        for sym in indicator_symbols:
            ind = ind_map.get(sym)
            if ind:
                found_any = True
                color = "#F04452" if ind.is_positive else "#3182F6"
                sign = "+" if ind.change_pct >= 0 else ""
                text.append(f"{ind.name} ", style="bold")
                text.append(f"{ind.formatted_value} ", style="")
                text.append(f"({sign}{ind.change_pct:.2f}%)", style=color)
                text.append("  |  ", style="dim")

        # Also try to look up by name from INDICATORS config
        if not found_any:
            # Try matching by indicator config names
            name_map = {name: sym for sym, (name, _) in INDICATORS.items()}
            for sym in indicator_symbols:
                ind_name = INDICATORS.get(sym, (None, None))[0]
                if ind_name:
                    for cached in cached_indicators:
                        if cached.name == ind_name:
                            found_any = True
                            color = "#F04452" if cached.is_positive else "#3182F6"
                            sign = "+" if cached.change_pct >= 0 else ""
                            text.append(f"{cached.name} ", style="bold")
                            text.append(f"{cached.formatted_value} ", style="")
                            text.append(f"({sign}{cached.change_pct:.2f}%)", style=color)
                            text.append("  |  ", style="dim")

        if found_any:
            self.query_one("#related-indicators", Static).update(text)

    def _apply_fundamentals(self, d: StockDetail):
        """Update the metrics row with fundamental data."""
        self.query_one("#m-mktcap", InfoCard).set_info("Market Cap", d.formatted_market_cap)
        self.query_one("#m-per", InfoCard).set_info("PER", f"{d.pe_ratio:.2f}" if d.pe_ratio else "N/A")
        self.query_one("#m-eps", InfoCard).set_info("EPS", f"{d.eps:.2f}" if d.eps else "N/A")
        label = "PBR" if d.market == "KR" else "Beta"
        self.query_one("#m-beta", InfoCard).set_info(
            label, f"{d.beta:.2f}" if d.beta else "N/A")

        # Volume metrics
        vol_color = ""
        if d.avg_volume and d.avg_volume > 0:
            ratio = d.volume / d.avg_volume
            vol_color = "#F04452" if ratio >= 1.5 else "#FFD700" if ratio >= 1.0 else ""
        self.query_one("#m-vol", InfoCard).set_info("Volume", self._fmt_vol(d.volume), vol_color)
        self.query_one("#m-avgvol", InfoCard).set_info("Avg Vol", self._fmt_vol(d.avg_volume))

    @staticmethod
    def _fmt_vol(v: int) -> str:
        if v >= 1e9: return f"{v/1e9:.2f}B"
        if v >= 1e6: return f"{v/1e6:.1f}M"
        if v >= 1e3: return f"{v/1e3:.0f}K"
        return str(v)
