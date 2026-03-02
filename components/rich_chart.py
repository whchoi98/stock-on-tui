# 주가 차트 위젯 모듈 — 기간 선택, Y축 라벨, 이동평균선, 통계 정보를 포함하는 스파크라인 차트
# Price chart widget module — sparkline chart with period selection, Y-axis labels, moving averages, and stats
from __future__ import annotations

from typing import List

from rich.text import Text
from textual.widgets import Static, Sparkline
from textual.containers import Vertical, Horizontal


# 가격 차트 위젯 클래스 — 기간별 주가 데이터를 스파크라인으로 시각화하고 MA5/MA20 교차 신호를 표시
# Price chart widget class — visualizes price data as sparkline by period and displays MA5/MA20 cross signals
class RichChart(Vertical):
    """Price chart with period selection, Y-axis labels, and stats."""

    # 위젯 기본 CSS 스타일 정의 / Default CSS style definition for the widget
    DEFAULT_CSS = """
    RichChart {
        height: auto;
        border: solid $surface-lighten-2;
        margin: 0 2;
        padding: 1 2;
        min-height: 20;
    }
    RichChart .chart-title-row { height: 1; }
    RichChart .period-bar { height: 1; margin: 0 0 1 0; }
    RichChart .pbtn { width: auto; min-width: 6; height: 1; margin: 0 1 0 0; }
    RichChart .pbtn.active { text-style: bold reverse; }
    RichChart .y-axis-row { height: auto; }
    RichChart .y-label { width: 10; height: 1; content-align: right middle; color: $text-muted; }
    RichChart .y-label-high { color: #F04452; }
    RichChart .y-label-low { color: #3182F6; }
    RichChart .spark-wrap { width: 1fr; height: 10; }
    RichChart .spark-wrap Sparkline { height: 10; }
    RichChart .chart-dates { height: 1; margin-left: 10; color: $text-muted; }
    RichChart .chart-stats { height: 4; margin-top: 1; padding: 0; }
    """

    # 지원하는 기간 목록 / Supported period options
    PERIODS = ["1W", "1M", "3M", "1Y"]

    # 생성자: 차트 데이터, 날짜, 현재 기간을 초기화
    # Constructor: initialize chart data, dates, and current period
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 기간별 가격 데이터 저장 딕셔너리 / Dictionary storing price data per period
        self._data = {}
        # 기간별 날짜 라벨 저장 딕셔너리 / Dictionary storing date labels per period
        self._dates = {}
        # 현재 선택된 기간 (기본: 1주) / Currently selected period (default: 1 week)
        self._current = "1W"

    # UI 구성 메서드: 차트 제목, 기간 버튼, 스파크라인, 날짜 라벨, 통계 영역을 배치
    # Compose method: lay out chart title, period buttons, sparkline, date labels, and stats area
    def compose(self):
        # 차트 제목 행 (단축키 안내 포함) / Chart title row (with shortcut key hints)
        yield Static("Price Chart  [1]W [2]M [3]3M [4]Y [Left/Right]", classes="chart-title-row")
        # 기간 선택 버튼 바 / Period selection button bar
        with Horizontal(classes="period-bar"):
            for p in self.PERIODS:
                # 현재 기간이면 active 클래스 적용 / Apply active class if it's the current period
                cls = "pbtn active" if p == "1W" else "pbtn"
                yield Static(f" {p} ", classes=cls, id=f"pb-{p}")

        # Y축 최고가 라벨 + 스파크라인 차트 / Y-axis high price label + sparkline chart
        yield Static("", classes="y-label y-label-high", id="y-high")
        with Horizontal(classes="y-axis-row"):
            yield Sparkline([], id="detail-spark", classes="spark-wrap")
        # Y축 최저가 라벨 / Y-axis low price label
        yield Static("", classes="y-label y-label-low", id="y-low")

        # 날짜 라벨 영역 / Date labels area
        yield Static("", classes="chart-dates", id="chart-dates")

        # 통계 정보 영역 / Statistics info area
        yield Static("", classes="chart-stats", id="chart-stats")

    # 전체 기간 데이터 설정: 1W/1M/3M/1Y 가격 데이터와 날짜를 한 번에 저장하고 차트에 반영
    # Set all period data: store 1W/1M/3M/1Y price data and dates at once, then apply to chart
    def set_all_data(self, d7, d30, d90, d1y, dt7, dt30, dt90, dt1y):
        self._data = {"1W": d7, "1M": d30, "3M": d90, "1Y": d1y}
        self._dates = {"1W": dt7, "1M": dt30, "3M": dt90, "1Y": dt1y}
        self._apply()

    # 기간 직접 설정: 지정된 기간으로 전환하고 차트를 갱신
    # Set period directly: switch to specified period and refresh chart
    def set_period(self, period: str):
        if period in self.PERIODS:
            self._current = period
            self._apply()

    # 다음 기간으로 이동: 순환적으로 다음 기간을 선택하고 차트를 갱신
    # Move to next period: cyclically select next period and refresh chart
    def next_period(self):
        idx = self.PERIODS.index(self._current)
        self._current = self.PERIODS[(idx + 1) % len(self.PERIODS)]
        self._apply()

    # 이전 기간으로 이동: 순환적으로 이전 기간을 선택하고 차트를 갱신
    # Move to previous period: cyclically select previous period and refresh chart
    def prev_period(self):
        idx = self.PERIODS.index(self._current)
        self._current = self.PERIODS[(idx - 1) % len(self.PERIODS)]
        self._apply()

    # 차트 적용 메서드: 현재 기간에 맞는 데이터로 스파크라인, Y축 라벨, 날짜, 통계를 갱신
    # Apply method: update sparkline, Y-axis labels, dates, and stats with current period data
    def _apply(self):
        # 기간 버튼의 활성/비활성 상태 토글 / Toggle active/inactive state of period buttons
        for p in self.PERIODS:
            btn = self.query_one(f"#pb-{p}", Static)
            if p == self._current:
                btn.add_class("active")
            else:
                btn.remove_class("active")

        # 현재 기간에 해당하는 데이터 및 날짜 가져오기 / Fetch data and dates for current period
        data = self._data.get(self._current, [])
        dates = self._dates.get(self._current, [])

        # 스파크라인 차트에 데이터 설정 / Set data on the sparkline chart
        spark = self.query_one("#detail-spark", Sparkline)
        spark.data = data if data else []

        # 데이터가 없으면 나머지 업데이트 건너뜀 / Skip remaining updates if no data
        if not data:
            return

        # 최저가, 최고가, 현재가, 시작가 계산 / Calculate min, max, current, and first price
        mn, mx = min(data), max(data)
        cur = data[-1]
        first = data[0]
        # 가격 변동 및 변동률 계산 / Calculate price change and change percentage
        chg = cur - first
        pct = (chg / first * 100) if first else 0
        sign = "+" if chg >= 0 else ""
        # 상승이면 빨간색, 하락이면 파란색 / Red for positive, blue for negative
        color = "#F04452" if chg >= 0 else "#3182F6"

        # Y축 라벨 포맷 결정: 1000 이상이면 정수, 미만이면 소수점 2자리
        # Determine Y-axis label format: integer for >= 1000, 2 decimals for < 1000
        fmt = ",.0f" if mx >= 1000 else ",.2f"
        self.query_one("#y-high", Static).update(f"  High {mx:{fmt}}")
        self.query_one("#y-low", Static).update(f"  Low  {mn:{fmt}}")

        # 날짜 라벨 업데이트: 5개 지점(시작, 1/4, 중간, 3/4, 끝)의 날짜를 표시
        # Update date labels: show dates at 5 positions (start, 1/4, middle, 3/4, end)
        if dates:
            parts = []
            positions = [0, len(dates)//4, len(dates)//2, 3*len(dates)//4, len(dates)-1]
            for pos in positions:
                if pos < len(dates):
                    parts.append(dates[pos])
            self.query_one("#chart-dates", Static).update("    ".join(parts))

        # MA5 / MA20 이동평균 계산 / Calculate MA5 / MA20 moving averages
        # MA5: 최근 5일 이동평균 (데이터가 1개 이상일 때) / MA5: 5-day moving average (when >= 1 data point)
        ma5 = sum(data[-5:]) / min(5, len(data)) if len(data) >= 1 else None
        # MA20: 최근 20일 이동평균 (데이터가 5개 이상일 때) / MA20: 20-day moving average (when >= 5 data points)
        ma20 = sum(data[-20:]) / min(20, len(data)) if len(data) >= 5 else None

        # 통계 정보 텍스트 구성 / Build statistics info text
        stats = Text()
        # 기간, 시작가, 현재가, 변동 정보 / Period, open price, current price, change info
        stats.append(f"  Period: {self._current}  ", style="bold")
        stats.append(f"Open: {first:{fmt}}  ", style="dim")
        stats.append(f"Current: {cur:{fmt}}  ", style=f"bold {color}")
        stats.append(f"Change: {sign}{chg:{fmt}} ({sign}{pct:.2f}%)  ", style=color)
        # 저가, 고가, 날짜 범위 / Low, high, date range
        stats.append(f"\n  Low: {mn:{fmt}}  High: {mx:{fmt}}  ", style="dim")
        date_range = f"{dates[0]} ~ {dates[-1]}" if dates else ""
        stats.append(f"Range: {date_range}", style="dim")

        # 이동평균선 정보 및 골든/데드 크로스 신호 표시
        # Moving average info and golden/dead cross signal display
        if ma5 is not None:
            stats.append(f"\n  MA5: {ma5:{fmt}}  ", style="bold #FFD700")
        if ma20 is not None:
            stats.append(f"MA20: {ma20:{fmt}}  ", style="bold #FF8C00")
        # MA5가 MA20 위이면 골든크로스(상승 신호), 아래이면 데드크로스(하락 신호)
        # Golden Cross (bullish signal) if MA5 > MA20, Dead Cross (bearish signal) if MA5 < MA20
        if ma5 is not None and ma20 is not None:
            if ma5 > ma20:
                stats.append("▲ Golden Cross", style="bold #F04452")
            elif ma5 < ma20:
                stats.append("▼ Dead Cross", style="bold #3182F6")

        # 통계 위젯 업데이트 / Update the stats widget
        self.query_one("#chart-stats", Static).update(stats)
