from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class StockQuote:
    symbol: str
    name: str
    price: float
    change: float = 0.0
    change_pct: float = 0.0
    volume: int = 0
    market: str = "US"
    currency: str = "USD"
    sector: str = ""
    market_cap: float = 0.0
    history_7d: List[float] = field(default_factory=list)
    last_updated: Optional[datetime] = None

    @property
    def is_positive(self) -> bool:
        return self.change >= 0

    @property
    def arrow(self) -> str:
        return "▲" if self.change > 0 else "▼" if self.change < 0 else "-"

    @property
    def formatted_price(self) -> str:
        if self.currency == "KRW":
            return f"{self.price:,.0f}"
        return f"{self.price:,.2f}"

    @property
    def formatted_change(self) -> str:
        sign = "+" if self.change >= 0 else ""
        if self.currency == "KRW":
            return f"{sign}{self.change:,.0f}"
        return f"{sign}{self.change:,.2f}"

    @property
    def formatted_change_pct(self) -> str:
        sign = "+" if self.change_pct >= 0 else ""
        return f"{sign}{self.change_pct:.2f}%"

    @property
    def formatted_market_cap(self) -> str:
        if self.market_cap <= 0:
            return "—"
        if self.currency == "KRW":
            if self.market_cap >= 1e16:
                return f"{self.market_cap / 1e16:.0f}경"
            if self.market_cap >= 1e12:
                return f"{self.market_cap / 1e12:.0f}조"
            if self.market_cap >= 1e8:
                return f"{self.market_cap / 1e8:.0f}억"
            return f"{self.market_cap:,.0f}"
        if self.market_cap >= 1e12:
            return f"${self.market_cap / 1e12:.2f}T"
        if self.market_cap >= 1e9:
            return f"${self.market_cap / 1e9:.1f}B"
        if self.market_cap >= 1e6:
            return f"${self.market_cap / 1e6:.0f}M"
        return f"${self.market_cap:,.0f}"


@dataclass
class MarketIndex:
    symbol: str
    name: str
    value: float
    change: float = 0.0
    change_pct: float = 0.0
    last_updated: Optional[datetime] = None

    @property
    def is_positive(self) -> bool:
        return self.change >= 0

    @property
    def formatted_value(self) -> str:
        return f"{self.value:,.2f}"

    @property
    def formatted_change_pct(self) -> str:
        sign = "+" if self.change_pct >= 0 else ""
        return f"{sign}{self.change_pct:.2f}%"


@dataclass
class EconomicIndicator:
    symbol: str
    name: str
    value: float
    change: float = 0.0
    change_pct: float = 0.0
    unit: str = ""
    last_updated: Optional[datetime] = None

    @property
    def is_positive(self) -> bool:
        return self.change >= 0

    @property
    def formatted_value(self) -> str:
        if self.unit == "%":
            return f"{self.value:.2f}%"
        elif self.unit == "$":
            return f"${self.value:,.2f}"
        elif self.unit == "W":
            return f"{self.value:,.0f}"
        return f"{self.value:,.2f}"

    @property
    def formatted_change_pct(self) -> str:
        sign = "+" if self.change_pct >= 0 else ""
        return f"{sign}{self.change_pct:.2f}%"


@dataclass
class StockDetail:
    symbol: str
    name: str
    market: str = "US"
    currency: str = "USD"
    price: float = 0.0
    change: float = 0.0
    change_pct: float = 0.0
    open_price: float = 0.0
    high: float = 0.0
    low: float = 0.0
    prev_close: float = 0.0
    volume: int = 0
    avg_volume: int = 0
    market_cap: float = 0.0
    pe_ratio: Optional[float] = None
    week52_high: float = 0.0
    week52_low: float = 0.0
    history_7d: List[float] = field(default_factory=list)
    history_30d: List[float] = field(default_factory=list)
    history_90d: List[float] = field(default_factory=list)
    history_1y: List[float] = field(default_factory=list)
    history_dates_7d: List[str] = field(default_factory=list)
    history_dates_30d: List[str] = field(default_factory=list)
    history_dates_90d: List[str] = field(default_factory=list)
    history_dates_1y: List[str] = field(default_factory=list)
    day_change: float = 0.0
    day_change_pct: float = 0.0
    eps: Optional[float] = None
    dividend_yield: Optional[float] = None
    beta: Optional[float] = None
    sector: str = ""
    last_updated: Optional[datetime] = None

    @property
    def is_positive(self) -> bool:
        return self.change >= 0

    @property
    def formatted_price(self) -> str:
        if self.currency == "KRW":
            return f"{self.price:,.0f}"
        return f"{self.price:,.2f}"

    @property
    def formatted_market_cap(self) -> str:
        if self.market_cap >= 1e12:
            return f"${self.market_cap / 1e12:.2f}T"
        elif self.market_cap >= 1e8:
            return f"${self.market_cap / 1e8:.1f}B" if self.currency == "USD" else f"{self.market_cap / 1e8:.0f}억"
        return f"{self.market_cap:,.0f}"

    @property
    def week52_position(self) -> float:
        if self.week52_high == self.week52_low:
            return 0.5
        return (self.price - self.week52_low) / (self.week52_high - self.week52_low)
