from __future__ import annotations

from rich.text import Text
from textual.widgets import Static

from models.stock import MarketIndex


class MarketCard(Static):
    """A card widget displaying a market index value with change."""

    DEFAULT_CSS = """
    MarketCard {
        width: 1fr;
        min-width: 16;
        height: 3;
        padding: 0 1;
        margin: 0 1;
        border: solid $surface-lighten-2;
        content-align: center middle;
    }
    """

    def update_data(self, index: MarketIndex) -> None:
        arrow = "▲" if index.change > 0 else "▼" if index.change < 0 else "-"
        color = "#F04452" if index.is_positive else "#3182F6"

        text = Text()
        text.append(f"{index.name} ", style="bold")
        text.append(f"{index.formatted_value} ", style=f"bold {color}")
        text.append(f"{arrow}{index.formatted_change_pct}", style=color)

        self.update(text)
        self.remove_class("positive", "negative")
        self.add_class("positive" if index.is_positive else "negative")
