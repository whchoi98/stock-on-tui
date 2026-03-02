from __future__ import annotations

from typing import List

from rich.text import Text
from textual.widgets import Static

from models.stock import EconomicIndicator


class IndicatorBar(Static):
    """Single-line scrollable economic indicators display."""

    DEFAULT_CSS = """
    IndicatorBar {
        height: 3;
        padding: 0 2;
        margin: 0 2;
        border: solid $surface-lighten-2;
        content-align: left middle;
    }
    """

    def __init__(self, **kwargs) -> None:
        # Remove 'count' kwarg if passed
        kwargs.pop("count", None)
        super().__init__(**kwargs)

    def update_indicators(self, indicators: List[EconomicIndicator]) -> None:
        text = Text()
        for i, ind in enumerate(indicators):
            if i > 0:
                text.append("  |  ", style="dim")
            color = "#F04452" if ind.is_positive else "#3182F6"
            arrow = "▲" if ind.change > 0 else "▼" if ind.change < 0 else "-"
            text.append(f"{ind.name} ", style="bold")
            text.append(f"{ind.formatted_value} ", style=f"{color}")
            text.append(f"{arrow}{ind.formatted_change_pct}", style=f"dim {color}")
        self.update(text)
