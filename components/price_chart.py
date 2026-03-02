from __future__ import annotations

from typing import List

from textual.widgets import Static, Sparkline
from textual.containers import Vertical


class PriceChart(Vertical):
    """7-day price chart using Sparkline."""

    DEFAULT_CSS = """
    PriceChart {
        height: auto;
        padding: 1 2;
        border: solid $surface-lighten-2;
        margin: 0 1;
    }
    PriceChart .chart-title {
        text-style: bold;
        margin-bottom: 1;
    }
    PriceChart Sparkline {
        height: 6;
    }
    """

    def __init__(self, title: str = "Price Chart (7 Days)", **kwargs) -> None:
        super().__init__(**kwargs)
        self._title = title

    def compose(self):
        yield Static(self._title, classes="chart-title")
        yield Sparkline([], id="spark")

    def update_chart(self, data: List[float], color: str = "#F04452") -> None:
        sparkline = self.query_one("#spark", Sparkline)
        sparkline.data = data
