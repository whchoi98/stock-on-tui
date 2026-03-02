# 종목 상세 화면 모듈: 차트, 호가, 투자자 동향, 재무 지표, AI 분석을 표시
# Stock detail screen module: displays chart, order book, investor trends, fundamentals, and AI analysis

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


# 정보 카드 위젯: 라벨-값 쌍을 표시하는 간단한 정보 표시 위젯
# Info card widget: simple widget that displays a label-value pair
class InfoCard(Static):
    DEFAULT_CSS = "InfoCard { width: 1fr; height: 2; padding: 0 2; }"

    # 라벨과 값을 설정하고 색상 적용 / Set label and value with optional color
    def set_info(self, label: str, value: str, color: str = "") -> None:
        text = Text()
        text.append(f"{label}: ", style="dim")
        text.append(value, style=f"bold {color}" if color else "bold")
        self.update(text)


# 뉴스 목록 항목 위젯: 개별 뉴스 기사를 리스트 항목으로 표시 (한국어=파란색, 영어=빨간색)
# News list item widget: displays individual news article as a list item (Korean=blue, English=red)
class NewsListItem(ListItem):
    DEFAULT_CSS = "NewsListItem { height: 2; padding: 0 2; }"

    # 뉴스 항목 초기화 / Initialize with news item
    def __init__(self, item: NewsItem, **kwargs):
        super().__init__(**kwargs)
        self.news_item = item

    # 뉴스 항목 렌더링: 출처 뱃지 + 제목 표시 / Render news item: source badge + title
    def compose(self):
        text = Text()
        # 한국어 뉴스는 파란색, 영어 뉴스는 빨간색 뱃지 / Korean news gets blue badge, English gets red
        color = "#3182F6" if self.news_item.is_korean else "#F04452"
        text.append(f"[{self.news_item.source}] ", style=f"bold {color}")
        text.append(self.news_item.title[:80], style="")
        yield Static(text)


# 52주 가격 범위 바 위젯: 현재가가 52주 최저/최고 사이 어디에 있는지 시각화
# 52-week price range bar widget: visualizes where current price sits between 52-week low/high
class Week52Bar(Vertical):
    DEFAULT_CSS = """
    Week52Bar { height: auto; padding: 1 2; border: solid $surface-lighten-2; margin: 0 2; }
    Week52Bar ProgressBar { height: 1; margin: 0 1; }
    Week52Bar .range-labels { height: 1; }
    """

    # 52주 범위 바 UI 구성 / Compose 52-week range bar UI
    def compose(self):
        yield Static("52 Week Range", classes="range-title")
        with Horizontal(classes="range-labels"):
            yield Static("", id="w52-low")
            yield Static("", id="w52-high")
        yield ProgressBar(total=100, show_eta=False, show_percentage=False, id="w52-bar")

    # 52주 범위 업데이트: 최저가, 최고가, 현재가 기준 진행률 계산
    # Update 52-week range: calculate progress based on low, high, and current price
    def update_range(self, low, high, current, currency="USD"):
        # 통화에 따른 포맷 설정 (KRW=정수, USD=소수점 2자리)
        # Format based on currency (KRW=integer, USD=2 decimal places)
        fmt = ",.0f" if currency == "KRW" else ",.2f"
        pfx = "" if currency == "KRW" else "$"
        self.query_one("#w52-low", Static).update(f"Low {pfx}{low:{fmt}}")
        self.query_one("#w52-high", Static).update(f"High {pfx}{high:{fmt}}")
        # 현재가의 52주 범위 내 위치를 백분율로 계산 / Calculate current price position as percentage
        pct = ((current - low) / (high - low) * 100) if high > low else 50
        self.query_one("#w52-bar", ProgressBar).update(progress=pct)


# 종목 상세 화면 클래스: 개별 종목의 차트, 호가, 투자자, 재무, AI 분석 표시
# Stock detail screen class: displays chart, order book, investors, fundamentals, and AI analysis for a stock
class DetailScreen(Screen):
    # 키 바인딩: b/esc=뒤로, r=새로고침, p/1-4/좌우=차트기간, a=AI분석
    # Key bindings: b/esc=back, r=refresh, p/1-4/arrows=chart period, a=AI analysis
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

    # 상세 화면 초기화: 종목 심볼, 시장, 데이터 캐시 변수 설정
    # Initialize detail screen: set stock symbol, market, and data cache variables
    def __init__(self, symbol: str, market: str = "US", **kwargs):
        super().__init__(**kwargs)
        self._symbol = symbol
        self._market = market
        self._detail: Optional[StockDetail] = None
        self._news: List[NewsItem] = []
        self._order_book: List[OrderBookEntry] = []
        self._investor_rows: List[InvestorRow] = []
        # 호가/투자자 데이터 로딩 상태 추적 / Track order book/investor data loading status
        self._ob_loaded = False
        self._inv_loaded = False
        # AI 분석 상태 관리: 결과, 로딩중, 표시중 / AI analysis state: result, loading, visible
        self._ai_result: str = ""
        self._ai_loading = False
        self._ai_visible = False

    # UI 위젯 구성: 종목 상세 화면의 모든 위젯을 배치
    # Compose UI widgets: lay out all widgets for the stock detail screen
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with VerticalScroll():
            # ── 헤더: 종목명, 가격, 보조 정보 / Header: stock name, price, sub info ──
            yield Static("", id="detail-title")
            yield Static("Loading...", id="price-header")
            yield Static("", id="price-sub")
            yield Static(
                "  Market Cap: 시가총액  PER: 주가수익비율  EPS: 주당순이익"
                "  Beta/PBR: 변동성/주가순자산  Vol: 당일거래량  Avg Vol: 평균거래량",
                id="api-notice",
            )

            # ── 주요 재무 지표 카드 행 / Key financial metrics card row ──
            with Horizontal(id="metrics-row"):
                yield InfoCard(id="m-mktcap")
                yield InfoCard(id="m-per")
                yield InfoCard(id="m-eps")
                yield InfoCard(id="m-beta")
                yield InfoCard(id="m-vol")
                yield InfoCard(id="m-avgvol")

            # ── 가격 차트 (1W/1M/3M/1Y 기간 전환 가능) / Price chart (switchable: 1W/1M/3M/1Y) ──
            yield RichChart(id="chart-panel")

            # ── 호가 + 시세/투자자 좌우 배치 / Order book + quote/investor side-by-side layout ──
            with Horizontal(id="mid-row"):
                # 호가 테이블 (왼쪽): 매도/매수 잔량 / Order book table (left): ask/bid volumes
                with Vertical(id="ob-section"):
                    yield Static(" 호가", classes="section-title")
                    yield Static("Loading...", id="ob-status")
                    yield DataTable(id="ob-table")

                # 시세 + 투자자 정보 (오른쪽) / Quote + investor info (right)
                with Vertical(id="quote-inv-section"):
                    # 시세 정보: 시가, 고가, 저가, 전일종가, 거래량 / Price info: open, high, low, prev close, volume
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
                    # 52주 가격 범위 바 / 52-week price range bar
                    yield Week52Bar(id="w52-range")

                    # 기간별 수익률 (1W, 1M, 3M, 1Y) / Period returns (1W, 1M, 3M, 1Y)
                    yield Static("", id="period-returns")

                    # 투자자 동향 테이블: 개인/외국인/기관 / Investor trends table: individual/foreign/institutional
                    yield Static(" 투자자 동향", classes="section-title")
                    yield Static("Loading...", id="inv-status")
                    yield DataTable(id="inv-table")

            # ── 섹터 관련 경제 지표 / Sector-related economic indicators ──
            yield Static("", id="related-indicators")

            # ── AI 종목 분석 결과 영역 / AI stock analysis result area ──
            yield Static("", id="ai-analysis")

            # ── 종목 관련 뉴스 (하단) / Company-related news (bottom) ──
            yield Static(" Company News  [Enter] AI Analysis  [A] AI 종목분석", classes="section-title")
            yield ListView(id="company-news")

            # 상태 표시 바 / Status display bar
            yield Static("Loading...", id="detail-status")
        yield Footer()

    # 화면 마운트 시 테이블 컬럼 설정 및 모든 데이터 병렬 로딩 시작
    # On screen mount: set up table columns and start loading all data in parallel
    def on_mount(self):
        # 호가 테이블 컬럼 설정 / Set up order book table columns
        ob = self.query_one("#ob-table", DataTable)
        ob.add_columns("매도잔량", "가격", "매수잔량")
        ob.cursor_type = "row"
        # 투자자 동향 테이블 컬럼 설정 / Set up investor trends table columns
        inv = self.query_one("#inv-table", DataTable)
        inv.add_columns("날짜", "개인", "외국인", "기관")
        inv.cursor_type = "row"
        # 모든 데이터를 병렬로 로딩 / Load all data in parallel
        self.load_detail()
        self.load_company_news()
        self.load_order_book()
        self.load_investor_trends()

    # 뒤로 가기: 대시보드 화면으로 복귀 / Go back: return to dashboard screen
    def action_go_back(self):
        self.dismiss()

    # 수동 새로고침: 모든 데이터를 다시 로딩 / Manual refresh: reload all data
    def action_refresh(self):
        self.query_one("#detail-status", Static).update("Refreshing...")
        self._ob_loaded = False
        self._inv_loaded = False
        self.load_detail()
        self.load_company_news()
        self.load_order_book()
        self.load_investor_trends()

    # 차트 기간을 다음으로 전환 (P 키) / Switch chart to next period (P key)
    def action_next_period(self):
        self.query_one("#chart-panel", RichChart).next_period()

    # 차트 기간을 다음으로 전환 (오른쪽 화살표) / Switch chart to next period (right arrow)
    def action_next_period_arrow(self):
        self.query_one("#chart-panel", RichChart).next_period()

    # 차트 기간을 이전으로 전환 (왼쪽 화살표) / Switch chart to previous period (left arrow)
    def action_prev_period(self):
        self.query_one("#chart-panel", RichChart).prev_period()

    # 차트 기간 직접 설정: 1주 / Set chart period directly: 1 week
    def action_period_1w(self):
        self.query_one("#chart-panel", RichChart).set_period("1W")

    # 차트 기간 직접 설정: 1개월 / Set chart period directly: 1 month
    def action_period_1m(self):
        self.query_one("#chart-panel", RichChart).set_period("1M")

    # 차트 기간 직접 설정: 3개월 / Set chart period directly: 3 months
    def action_period_3m(self):
        self.query_one("#chart-panel", RichChart).set_period("3M")

    # 차트 기간 직접 설정: 1년 / Set chart period directly: 1 year
    def action_period_1y(self):
        self.query_one("#chart-panel", RichChart).set_period("1Y")

    # 종목 상세 데이터 로딩 (2단계): 빠른 데이터 먼저, 재무 데이터는 백그라운드
    # Load stock detail data (2 phases): fast data first, fundamentals in background
    @work(exclusive=True, group="detail-refresh", exit_on_error=False)
    async def load_detail(self):
        # 1단계: 빠른 데이터 (가격, 차트, 기본 정보) / Phase 1: fast data (price, chart, basic info)
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

        # 2단계: 재무 지표 (PE/EPS/Div/Beta/시가총액) — 백그라운드 로딩
        # Phase 2: fundamentals (PE/EPS/Div/Beta/MarketCap) — background loading
        self.load_fundamentals()

    # 재무 지표 로딩: PE/EPS/Div/Beta를 백오프 재시도 방식으로 로딩
    # Load fundamentals: fetch PE/EPS/Div/Beta with exponential backoff retry
    @work(exclusive=True, group="fundamentals", exit_on_error=False)
    async def load_fundamentals(self):
        """Load PE/EPS/Div/Beta with retry on rate limit."""
        # 최대 4회 시도, 실패 시 점진적 대기 (5초, 10초, 15초)
        # Up to 4 attempts, with progressive backoff (5s, 10s, 15s)
        for attempt in range(4):
            if attempt > 0:
                await asyncio.sleep(5 * attempt)  # 5s, 10s, 15s backoff

            if self._market == "US":
                from services.us_stocks import fetch_us_fundamentals
                data = await asyncio.to_thread(fetch_us_fundamentals, self._symbol)
            else:
                from services.kr_stocks import fetch_kr_fundamentals
                data = await asyncio.to_thread(fetch_kr_fundamentals, self._symbol)

            # 데이터 수신 성공 시 상세 모델에 반영 / On success, merge data into detail model
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
                return  # 성공 / Success

        # 모든 재시도 실패 시 N/A 표시 / Show N/A if all retries failed
        if self._detail:
            self._apply_fundamentals(self._detail)

    # 종목 관련 뉴스 로딩 및 뉴스 리스트 갱신
    # Load company-related news and update news list
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

    # 호가 데이터 비동기 로딩 / Load order book data asynchronously
    @work(exclusive=True, group="order-book", exit_on_error=False)
    async def load_order_book(self):
        entries = await asyncio.to_thread(fetch_order_book, self._symbol, self._market)
        self._order_book = entries
        self._ob_loaded = True
        self._apply_order_book(entries)

    # 투자자 동향 데이터 비동기 로딩 (개인/외국인/기관)
    # Load investor trends data asynchronously (individual/foreign/institutional)
    @work(exclusive=True, group="investor-trends", exit_on_error=False)
    async def load_investor_trends(self):
        rows = await asyncio.to_thread(fetch_investor_trends, self._symbol, self._market, 10)
        self._investor_rows = rows
        self._inv_loaded = True
        self._apply_investor_trends(rows)

    # 호가 데이터를 테이블에 적용: 매도(파란색 상단) / 매수(빨간색 하단)
    # Apply order book data to table: asks (blue, top) / bids (red, bottom)
    def _apply_order_book(self, entries: List[OrderBookEntry]):
        table = self.query_one("#ob-table", DataTable)
        table.clear()
        status = self.query_one("#ob-status", Static)

        if not entries:
            status.update("호가 데이터를 불러올 수 없습니다.")
            return
        status.update("")

        # 매도 호가와 매수 호가 분리 및 정렬 / Separate and sort ask and bid entries
        asks = sorted([e for e in entries if not e.is_bid], key=lambda e: e.price)
        bids = sorted([e for e in entries if e.is_bid], key=lambda e: -e.price)

        is_krw = self._market == "KR"
        fmt = ",.0f" if is_krw else ",.2f"

        # 매도 행 (파란색) - 높은 가격부터 표시 / Ask rows (blue) - highest price first
        for e in reversed(asks):
            vol_bar = "█" * min(20, max(1, e.volume // 100))
            table.add_row(
                Text(f"{vol_bar} {e.volume:,}", style="#3182F6"),
                Text(f"{e.price:{fmt}}", style="#3182F6 bold"),
                Text(""),
            )

        # 매수 행 (빨간색) - 높은 가격부터 표시 / Bid rows (red) - highest price first
        for e in bids:
            vol_bar = "█" * min(20, max(1, e.volume // 100))
            table.add_row(
                Text(""),
                Text(f"{e.price:{fmt}}", style="#F04452 bold"),
                Text(f"{e.volume:,} {vol_bar}", style="#F04452"),
            )

    # 투자자 동향 데이터를 테이블에 적용: 양수=빨간색(매수), 음수=파란색(매도)
    # Apply investor trends to table: positive=red (buy), negative=blue (sell)
    def _apply_investor_trends(self, rows: List[InvestorRow]):
        table = self.query_one("#inv-table", DataTable)
        table.clear()
        status = self.query_one("#inv-status", Static)

        if not rows:
            status.update("투자자 데이터를 불러올 수 없습니다.")
            return
        status.update("")

        # 거래량 색상 처리: 양수=빨간색(순매수), 음수=파란색(순매도)
        # Volume coloring: positive=red (net buy), negative=blue (net sell)
        def _colored_vol(v: int) -> Text:
            if v > 0:
                return Text(f"+{v:,}", style="#F04452 bold")
            elif v < 0:
                return Text(f"{v:,}", style="#3182F6 bold")
            return Text("0", style="dim")

        for r in rows:
            table.add_row(r.date, _colored_vol(r.individual), _colored_vol(r.foreign), _colored_vol(r.institution))

    # AI 종목 분석 토글: 표시/숨김/로딩 상태 관리 (A 키)
    # Toggle AI stock analysis: manage show/hide/loading states (A key)
    def action_toggle_ai(self):
        """Toggle AI stock analysis."""
        from services.bedrock import is_bedrock_available, _DISABLED_MSG
        # Bedrock 사용 불가 시 비활성화 메시지 표시 / Show disabled message if Bedrock unavailable
        if not is_bedrock_available():
            self.query_one("#ai-analysis", Static).update(_DISABLED_MSG)
            return
        # 로딩 중이면 무시 / Ignore if already loading
        if self._ai_loading:
            return
        if self._ai_visible and self._ai_result:
            # 표시 중이면 숨기기 / Hide if currently visible
            self._ai_visible = False
            self.query_one("#ai-analysis", Static).update("")
            return
        if self._ai_result:
            # 캐시된 결과 표시 / Show cached result
            self._ai_visible = True
            self._show_ai_result()
            return
        # Bedrock에서 새로 로딩 / Load fresh from Bedrock
        self._ai_loading = True
        self.query_one("#ai-analysis", Static).update(" AI 종목 분석 로딩중...")
        self.load_ai_analysis()

    # Bedrock을 통한 AI 종목 분석 비동기 로딩
    # Load AI stock analysis asynchronously via Bedrock
    @work(exclusive=True, group="ai-analysis", exit_on_error=False)
    async def load_ai_analysis(self):
        from services.bedrock import analyze_stock
        d = self._detail
        if not d:
            self._ai_loading = False
            return
        # 최근 뉴스 제목 5개를 AI 분석에 포함 / Include top 5 recent news titles in AI analysis
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

    # AI 분석 결과를 화면에 렌더링 / Render AI analysis result on screen
    def _show_ai_result(self):
        text = Text()
        text.append("\n AI 종목 분석  ", style="bold #FFD700")
        text.append("[A] 토글\n", style="dim")
        text.append(self._ai_result, style="")
        self.query_one("#ai-analysis", Static).update(text)

    # 뉴스 목록 항목 선택 시 기사 상세 화면으로 이동
    # Navigate to article detail screen when a news list item is selected
    def on_list_view_selected(self, event: ListView.Selected):
        if isinstance(event.item, NewsListItem):
            from screens.article import ArticleScreen
            self.app.push_screen(ArticleScreen(event.item.news_item))

    # 종목 상세 데이터를 모든 UI 위젯에 적용 (가격, 차트, 정보카드, 52주범위 등)
    # Apply stock detail data to all UI widgets (price, chart, info cards, 52-week range, etc.)
    def _apply_detail(self, d: StockDetail):
        # 가격 변동 방향에 따른 색상 설정: 상승=빨간색, 하락=파란색
        # Set color based on price direction: up=red, down=blue
        color = "#F04452" if d.is_positive else "#3182F6"
        sign = "+" if d.change >= 0 else ""
        # 통화별 포맷 설정 / Format settings per currency
        fmt = ",.0f" if d.currency == "KRW" else ",.2f"
        pfx = "" if d.currency == "KRW" else "$"
        sfx = "원" if d.currency == "KRW" else ""
        arrow = "▲" if d.change > 0 else "▼" if d.change < 0 else "-"

        # 종목 제목 표시: 심볼 + 이름 / Display stock title: symbol + name
        title = Text()
        title.append(f"  {d.symbol}", style="bold")
        title.append(f"  {d.name}", style="")
        self.query_one("#detail-title", Static).update(title)

        # 가격 헤더: 현재가, 변동폭, 거래량 비율 표시
        # Price header: current price, change amount, volume ratio display
        header = Text()
        header.append(f"  {pfx}{d.price:{fmt}}{sfx} ", style=f"bold {color}")
        header.append(f" {arrow} {sign}{d.change:{fmt}} ({sign}{d.change_pct:.2f}%)", style=color)
        header.append(f"   Vol: {self._fmt_vol(d.volume)}", style="bold")
        # 거래량이 평균 대비 1.5배 이상이면 빨간색, 1.0배 이상이면 노란색 강조
        # Highlight volume: red if >= 1.5x avg, yellow if >= 1.0x avg
        if d.avg_volume and d.avg_volume > 0:
            ratio = d.volume / d.avg_volume
            vol_color = "#F04452" if ratio >= 1.5 else "#FFD700" if ratio >= 1.0 else "dim"
            header.append(f" ({ratio:.1f}x avg)", style=vol_color)
        self.query_one("#price-header", Static).update(header)

        # 보조 정보: 섹터, 거래소 / Sub info: sector, exchange
        sub = Text()
        if d.sector:
            sub.append(f"  Sector: {d.sector}", style="dim")
        sub.append(f"  |  Market: {'NYSE/NASDAQ' if d.market == 'US' else 'KRX'}", style="dim")
        self.query_one("#price-sub", Static).update(sub)

        # 재무 지표 카드 갱신 / Update fundamental metrics cards
        self._apply_fundamentals(d)

        # 차트에 모든 기간 히스토리 데이터 설정 / Set all period history data to chart
        chart = self.query_one("#chart-panel", RichChart)
        chart.set_all_data(
            d.history_7d, d.history_30d, d.history_90d, d.history_1y,
            d.history_dates_7d, d.history_dates_30d, d.history_dates_90d, d.history_dates_1y,
        )

        # 시세 정보 카드 갱신 / Update price info cards
        self.query_one("#info-open", InfoCard).set_info("Open", f"{pfx}{d.open_price:{fmt}}")
        self.query_one("#info-high", InfoCard).set_info("High", f"{pfx}{d.high:{fmt}}", "#F04452")
        self.query_one("#info-low", InfoCard).set_info("Low", f"{pfx}{d.low:{fmt}}", "#3182F6")
        self.query_one("#info-prev", InfoCard).set_info("Prev Close", f"{pfx}{d.prev_close:{fmt}}")
        self.query_one("#info-volume", InfoCard).set_info("Volume", self._fmt_vol(d.volume))
        self.query_one("#info-avg-vol", InfoCard).set_info("Avg Vol", self._fmt_vol(d.avg_volume))
        self.query_one("#info-day-range", InfoCard).set_info("Day Range", f"{pfx}{d.low:{fmt}} - {pfx}{d.high:{fmt}}")
        self.query_one("#info-sector", InfoCard).set_info("Sector", d.sector or "N/A")

        # 52주 가격 범위 바 갱신 / Update 52-week price range bar
        self.query_one("#w52-range", Week52Bar).update_range(d.week52_low, d.week52_high, d.price, d.currency)

        # 기간별 수익률 계산 및 표시 / Calculate and display period returns
        self._apply_returns(d)
        # 섹터 관련 경제 지표 표시 / Display sector-related economic indicators
        self._apply_related_indicators(d)

        # 상태 바에 갱신 시간 및 단축키 안내 표시 / Show update time and shortcut guide in status bar
        now = datetime.now().strftime("%H:%M:%S")
        self.query_one("#detail-status", Static).update(
            f"Updated: {now} | [1]1W [2]1M [3]3M [4]1Y [<>]Period | [Enter]News AI | [B]Back"
        )

    # 기간별 수익률 계산 및 표시: 1W, 1M, 3M, 1Y (현재가 vs 기간 시작가)
    # Calculate and display period returns: 1W, 1M, 3M, 1Y (current price vs period start price)
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
                # 수익률 = (현재가 - 기간시작가) / 기간시작가 * 100
                # Return = (current - period_start) / period_start * 100
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

    # 종목 섹터에 관련된 경제 지표를 대시보드 캐시에서 가져와 표시
    # Fetch and display sector-related economic indicators from dashboard cache
    def _apply_related_indicators(self, d: StockDetail):
        """Show related economic indicators based on sector."""
        sector = d.sector
        if not sector:
            return

        # 섹터 -> 관련 지표 심볼 매핑 조회 / Look up sector -> related indicator symbol mapping
        indicator_symbols = SECTOR_INDICATOR_MAP.get(sector, [])
        if not indicator_symbols:
            return

        # 대시보드 화면의 캐시된 지표 데이터 접근 시도
        # Try to access cached indicator data from dashboard screen
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

        # 심볼 기준 빠른 조회를 위한 딕셔너리 생성 / Build dict for fast lookup by symbol
        ind_map = {ind.symbol: ind for ind in cached_indicators}

        text = Text()
        text.append("\n 관련 지표  ", style="bold")

        # 1차: 심볼로 직접 매칭 시도 / First pass: try direct symbol matching
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

        # 2차: 심볼 매칭 실패 시 INDICATORS 설정의 이름으로 매칭 시도
        # Second pass: if symbol matching fails, try matching by name from INDICATORS config
        if not found_any:
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

    # 재무 지표 카드 행 갱신: 시가총액, PER, EPS, Beta/PBR, 거래량
    # Update fundamental metrics card row: market cap, PER, EPS, Beta/PBR, volume
    def _apply_fundamentals(self, d: StockDetail):
        """Update the metrics row with fundamental data."""
        self.query_one("#m-mktcap", InfoCard).set_info("Market Cap", d.formatted_market_cap)
        self.query_one("#m-per", InfoCard).set_info("PER", f"{d.pe_ratio:.2f}" if d.pe_ratio else "N/A")
        self.query_one("#m-eps", InfoCard).set_info("EPS", f"{d.eps:.2f}" if d.eps else "N/A")
        # 한국 시장은 PBR, 미국 시장은 Beta 표시 / Show PBR for KR market, Beta for US market
        label = "PBR" if d.market == "KR" else "Beta"
        self.query_one("#m-beta", InfoCard).set_info(
            label, f"{d.beta:.2f}" if d.beta else "N/A")

        # 거래량 지표: 평균 대비 비율에 따라 색상 강조 / Volume metrics: color by ratio to average
        vol_color = ""
        if d.avg_volume and d.avg_volume > 0:
            ratio = d.volume / d.avg_volume
            vol_color = "#F04452" if ratio >= 1.5 else "#FFD700" if ratio >= 1.0 else ""
        self.query_one("#m-vol", InfoCard).set_info("Volume", self._fmt_vol(d.volume), vol_color)
        self.query_one("#m-avgvol", InfoCard).set_info("Avg Vol", self._fmt_vol(d.avg_volume))

    # 거래량 포맷 헬퍼: 큰 숫자를 B/M/K 단위로 변환
    # Volume format helper: convert large numbers to B/M/K units
    @staticmethod
    def _fmt_vol(v: int) -> str:
        if v >= 1e9: return f"{v/1e9:.2f}B"
        if v >= 1e6: return f"{v/1e6:.1f}M"
        if v >= 1e3: return f"{v/1e3:.0f}K"
        return str(v)
