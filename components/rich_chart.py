from __future__ import annotations

from typing import List

from rich.text import Text
from textual.widgets import Static, Sparkline
from textual.containers import Vertical, Horizontal


class RichChart(Vertical):
    """Price chart with period selection, Y-axis labels, and stats."""

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

    PERIODS = ["1W", "1M", "3M", "1Y"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._data = {}
        self._dates = {}
        self._current = "1W"

    def compose(self):
        yield Static("Price Chart  [1]W [2]M [3]3M [4]Y [Left/Right]", classes="chart-title-row")
        with Horizontal(classes="period-bar"):
            for p in self.PERIODS:
                cls = "pbtn active" if p == "1W" else "pbtn"
                yield Static(f" {p} ", classes=cls, id=f"pb-{p}")

        # Y-axis high label + sparkline
        yield Static("", classes="y-label y-label-high", id="y-high")
        with Horizontal(classes="y-axis-row"):
            yield Sparkline([], id="detail-spark", classes="spark-wrap")
        yield Static("", classes="y-label y-label-low", id="y-low")

        # Date labels
        yield Static("", classes="chart-dates", id="chart-dates")

        # Stats
        yield Static("", classes="chart-stats", id="chart-stats")

    def set_all_data(self, d7, d30, d90, d1y, dt7, dt30, dt90, dt1y):
        self._data = {"1W": d7, "1M": d30, "3M": d90, "1Y": d1y}
        self._dates = {"1W": dt7, "1M": dt30, "3M": dt90, "1Y": dt1y}
        self._apply()

    def set_period(self, period: str):
        if period in self.PERIODS:
            self._current = period
            self._apply()

    def next_period(self):
        idx = self.PERIODS.index(self._current)
        self._current = self.PERIODS[(idx + 1) % len(self.PERIODS)]
        self._apply()

    def prev_period(self):
        idx = self.PERIODS.index(self._current)
        self._current = self.PERIODS[(idx - 1) % len(self.PERIODS)]
        self._apply()

    def _apply(self):
        for p in self.PERIODS:
            btn = self.query_one(f"#pb-{p}", Static)
            if p == self._current:
                btn.add_class("active")
            else:
                btn.remove_class("active")

        data = self._data.get(self._current, [])
        dates = self._dates.get(self._current, [])

        # Sparkline
        spark = self.query_one("#detail-spark", Sparkline)
        spark.data = data if data else []

        if not data:
            return

        mn, mx = min(data), max(data)
        cur = data[-1]
        first = data[0]
        chg = cur - first
        pct = (chg / first * 100) if first else 0
        sign = "+" if chg >= 0 else ""
        color = "#F04452" if chg >= 0 else "#3182F6"

        # Y-axis labels
        fmt = ",.0f" if mx >= 1000 else ",.2f"
        self.query_one("#y-high", Static).update(f"  High {mx:{fmt}}")
        self.query_one("#y-low", Static).update(f"  Low  {mn:{fmt}}")

        # Date labels
        if dates:
            parts = []
            positions = [0, len(dates)//4, len(dates)//2, 3*len(dates)//4, len(dates)-1]
            for pos in positions:
                if pos < len(dates):
                    parts.append(dates[pos])
            self.query_one("#chart-dates", Static).update("    ".join(parts))

        # MA5 / MA20 calculation
        ma5 = sum(data[-5:]) / min(5, len(data)) if len(data) >= 1 else None
        ma20 = sum(data[-20:]) / min(20, len(data)) if len(data) >= 5 else None

        # Stats line
        stats = Text()
        stats.append(f"  Period: {self._current}  ", style="bold")
        stats.append(f"Open: {first:{fmt}}  ", style="dim")
        stats.append(f"Current: {cur:{fmt}}  ", style=f"bold {color}")
        stats.append(f"Change: {sign}{chg:{fmt}} ({sign}{pct:.2f}%)  ", style=color)
        stats.append(f"\n  Low: {mn:{fmt}}  High: {mx:{fmt}}  ", style="dim")
        date_range = f"{dates[0]} ~ {dates[-1]}" if dates else ""
        stats.append(f"Range: {date_range}", style="dim")

        # MA line
        if ma5 is not None:
            stats.append(f"\n  MA5: {ma5:{fmt}}  ", style="bold #FFD700")
        if ma20 is not None:
            stats.append(f"MA20: {ma20:{fmt}}  ", style="bold #FF8C00")
        if ma5 is not None and ma20 is not None:
            if ma5 > ma20:
                stats.append("▲ Golden Cross", style="bold #F04452")
            elif ma5 < ma20:
                stats.append("▼ Dead Cross", style="bold #3182F6")

        self.query_one("#chart-stats", Static).update(stats)
