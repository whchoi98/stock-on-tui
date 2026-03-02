from __future__ import annotations

from typing import List

from rich.text import Text
from textual.widgets import Static

from models.stock import StockQuote


class MarketSummary(Static):
    """Market summary widget showing up/down counts, top movers, and volume leaders."""

    DEFAULT_CSS = """
    MarketSummary {
        height: auto;
        min-height: 4;
        margin: 0 2;
        padding: 1 2;
        border: solid $surface-lighten-2;
    }
    """

    def __init__(self, **kwargs):
        super().__init__("", **kwargs)

    def update_data(self, us_quotes: List[StockQuote], kr_quotes: List[StockQuote]) -> None:
        text = Text()

        # ── Line 1: Market breadth ──
        us_up = sum(1 for q in us_quotes if q.change > 0)
        us_down = sum(1 for q in us_quotes if q.change < 0)
        kr_up = sum(1 for q in kr_quotes if q.change > 0)
        kr_down = sum(1 for q in kr_quotes if q.change < 0)

        text.append(" 시장 요약  ", style="bold")
        text.append("US: 상승 ", style="dim")
        text.append(f"{us_up}", style="bold #F04452")
        text.append(" 하락 ", style="dim")
        text.append(f"{us_down}", style="bold #3182F6")
        text.append("  |  KR: 상승 ", style="dim")
        text.append(f"{kr_up}", style="bold #F04452")
        text.append(" 하락 ", style="dim")
        text.append(f"{kr_down}", style="bold #3182F6")

        # ── US Top movers ──
        us_sorted_up = sorted(us_quotes, key=lambda q: q.change_pct, reverse=True)
        us_sorted_down = sorted(us_quotes, key=lambda q: q.change_pct)

        text.append("\n 🇺🇸 Top▲ ", style="bold #F04452")
        for q in us_sorted_up[:3]:
            text.append(f"{q.name}({q.symbol}) ", style="bold")
            text.append(f"+{q.change_pct:.2f}% ", style="#F04452")
            text.append(f"[{self._fmt_vol(q.volume)}]  ", style="dim")

        text.append("  Top▼ ", style="bold #3182F6")
        for q in us_sorted_down[:3]:
            text.append(f"{q.name}({q.symbol}) ", style="bold")
            text.append(f"{q.change_pct:.2f}% ", style="#3182F6")
            text.append(f"[{self._fmt_vol(q.volume)}]  ", style="dim")

        # ── KR Top movers ──
        kr_sorted_up = sorted(kr_quotes, key=lambda q: q.change_pct, reverse=True)
        kr_sorted_down = sorted(kr_quotes, key=lambda q: q.change_pct)

        text.append("\n 🇰🇷 Top▲ ", style="bold #F04452")
        for q in kr_sorted_up[:3]:
            text.append(f"{q.name}({q.symbol}) ", style="bold")
            text.append(f"+{q.change_pct:.2f}% ", style="#F04452")
            text.append(f"[{self._fmt_vol(q.volume)}]  ", style="dim")

        text.append("  Top▼ ", style="bold #3182F6")
        for q in kr_sorted_down[:3]:
            text.append(f"{q.name}({q.symbol}) ", style="bold")
            text.append(f"{q.change_pct:.2f}% ", style="#3182F6")
            text.append(f"[{self._fmt_vol(q.volume)}]  ", style="dim")

        # ── Volume leaders by market ──
        us_vol = sorted(us_quotes, key=lambda q: q.volume, reverse=True)
        kr_vol = sorted(kr_quotes, key=lambda q: q.volume, reverse=True)

        text.append("\n ⚡ 거래량 US: ", style="bold")
        for q in us_vol[:3]:
            text.append(f"{q.name}({q.symbol}) ", style="bold")
            text.append(f"{self._fmt_vol(q.volume)}  ", style="dim")

        text.append("  KR: ", style="bold")
        for q in kr_vol[:3]:
            text.append(f"{q.name}({q.symbol}) ", style="bold")
            text.append(f"{self._fmt_vol(q.volume)}  ", style="dim")

        self.update(text)

    @staticmethod
    def _fmt_vol(v: int) -> str:
        if v >= 1e9:
            return f"{v / 1e9:.1f}B"
        if v >= 1e6:
            return f"{v / 1e6:.1f}M"
        if v >= 1e3:
            return f"{v / 1e3:.0f}K"
        return str(v)
