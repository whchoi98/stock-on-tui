from __future__ import annotations

from typing import Dict, List, Optional

from rich.text import Text
from textual.widgets import DataTable

from models.stock import StockQuote


class StockTable(DataTable):
    """DataTable subclass for displaying stock quotes with color coding."""

    DEFAULT_CSS = """
    StockTable {
        height: 1fr;
        margin: 0 1;
    }
    """

    def __init__(self, market: str = "US", **kwargs) -> None:
        super().__init__(cursor_type="row", zebra_stripes=True, **kwargs)
        self._market = market
        self._stock_data: Dict[str, StockQuote] = {}

    def on_mount(self) -> None:
        self.add_columns("Symbol", "Name", "Price", "Change", "%", "Mkt Cap", "Volume", "")

    def update_stocks(self, stocks: List[StockQuote]) -> None:
        self.clear()
        self._stock_data.clear()

        for stock in stocks:
            color = "#F04452" if stock.is_positive else "#3182F6"

            symbol_text = Text(stock.symbol, style="bold")
            name_text = Text(stock.name)
            price_text = Text(stock.formatted_price, style=f"bold {color}")
            change_text = Text(stock.formatted_change, style=color)
            pct_text = Text(stock.formatted_change_pct, style=color)
            cap_text = Text(stock.formatted_market_cap, style="dim")

            if stock.volume >= 1_000_000:
                vol_str = f"{stock.volume / 1_000_000:.1f}M"
            elif stock.volume >= 1_000:
                vol_str = f"{stock.volume / 1_000:.0f}K"
            else:
                vol_str = str(stock.volume)
            vol_text = Text(vol_str, style="dim")

            arrow_text = Text(stock.arrow, style=f"bold {color}")

            self.add_row(
                symbol_text, name_text, price_text,
                change_text, pct_text, cap_text, vol_text, arrow_text,
                key=stock.symbol,
            )
            self._stock_data[stock.symbol] = stock

    def get_stock_by_key(self, key: str) -> Optional[StockQuote]:
        return self._stock_data.get(key)
