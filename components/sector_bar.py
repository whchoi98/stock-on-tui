from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Tuple

from rich.text import Text
from textual.widgets import Static

from models.stock import StockQuote
from config import US_STOCK_SECTORS, KR_STOCK_SECTORS


class SectorBar(Static):
    """Sector performance bar showing average change % per sector, split by market."""

    DEFAULT_CSS = """
    SectorBar {
        height: auto;
        min-height: 2;
        margin: 0 2;
        padding: 0 2;
        border: solid $surface-lighten-2;
    }
    """

    def __init__(self, **kwargs):
        super().__init__("", **kwargs)

    def update_data(self, us_quotes: List[StockQuote], kr_quotes: List[StockQuote]) -> None:
        text = Text()

        # ── US Sectors ──
        us_avgs = self._calc_sector_avgs(us_quotes, US_STOCK_SECTORS)
        text.append(" 🇺🇸 섹터  ", style="bold")
        for sector, avg in us_avgs[:8]:
            self._append_sector(text, sector, avg)

        # ── KR Sectors ──
        kr_avgs = self._calc_sector_avgs(kr_quotes, KR_STOCK_SECTORS)
        text.append("\n 🇰🇷 섹터  ", style="bold")
        for sector, avg in kr_avgs[:8]:
            self._append_sector(text, sector, avg)

        self.update(text)

    @staticmethod
    def _calc_sector_avgs(
        quotes: List[StockQuote], sector_map: Dict[str, str]
    ) -> List[Tuple[str, float]]:
        pcts: Dict[str, List[float]] = defaultdict(list)
        for q in quotes:
            sector = sector_map.get(q.symbol, "")
            if sector:
                pcts[sector].append(q.change_pct)

        avgs = []
        for sector, vals in pcts.items():
            avg = sum(vals) / len(vals) if vals else 0
            avgs.append((sector, avg))
        avgs.sort(key=lambda x: abs(x[1]), reverse=True)
        return avgs

    @staticmethod
    def _append_sector(text: Text, sector: str, avg: float) -> None:
        color = "#F04452" if avg >= 0 else "#3182F6"
        sign = "+" if avg >= 0 else ""
        bar_len = min(8, max(1, int(abs(avg) * 4)))
        bar = "█" * bar_len

        text.append(f"{sector} ", style="bold")
        text.append(f"{sign}{avg:.1f}% ", style=color)
        text.append(f"{bar}  ", style=color)
