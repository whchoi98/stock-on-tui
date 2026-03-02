from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ChartData:
    prices: List[float] = field(default_factory=list)
    dates: List[str] = field(default_factory=list)
    volumes: List[int] = field(default_factory=list)
    highs: List[float] = field(default_factory=list)
    lows: List[float] = field(default_factory=list)


@dataclass
class OrderBookEntry:
    price: float
    volume: int
    is_bid: bool  # True=bid(buy), False=ask(sell)


@dataclass
class InvestorRow:
    date: str
    individual: int = 0   # 개인
    foreign: int = 0      # 외국인
    institution: int = 0  # 기관


def fetch_chart_data(symbol: str, market: str, period: str) -> ChartData:
    """Fetch chart data for various periods."""
    try:
        import yfinance as yf

        yf_sym = f"{symbol}.KS" if market == "KR" else symbol

        period_map = {
            "1min": ("1d", "1m"),
            "day": ("3mo", "1d"),
            "week": ("1y", "1wk"),
            "month": ("5y", "1mo"),
            "year": ("max", "3mo"),
        }
        yf_period, yf_interval = period_map.get(period, ("3mo", "1d"))
        t = yf.Ticker(yf_sym)
        h = t.history(period=yf_period, interval=yf_interval)

        if h.empty:
            return ChartData()

        closes = h["Close"].dropna()
        date_fmt = "%H:%M" if period == "1min" else "%m/%d" if period in ("day", "week") else "%Y/%m"

        return ChartData(
            prices=closes.tolist(),
            dates=[d.strftime(date_fmt) for d in closes.index],
            volumes=[int(v) for v in h["Volume"].fillna(0).tolist()],
            highs=h["High"].fillna(0).tolist(),
            lows=h["Low"].fillna(0).tolist(),
        )
    except Exception as e:
        logger.error(f"Chart data error: {e}")
        return ChartData()


def fetch_order_book(symbol: str, market: str) -> List[OrderBookEntry]:
    """Fetch bid/ask data to simulate order book."""
    try:
        import yfinance as yf

        yf_sym = f"{symbol}.KS" if market == "KR" else symbol
        t = yf.Ticker(yf_sym)
        info = t.fast_info
        price = getattr(info, "last_price", 0) or 0

        if price <= 0:
            return []

        bid = price * 0.999
        ask = price * 1.001

        is_krw = market == "KR"
        tick = 500 if is_krw and price > 50000 else 100 if is_krw else 0.01 if price < 10 else 0.05 if price < 50 else 0.10

        entries = []
        import random
        random.seed(int(price * 100))

        for i in range(10):
            p = ask + tick * i
            vol = int(100 * random.uniform(0.3, 3.0))
            entries.append(OrderBookEntry(price=p, volume=vol, is_bid=False))

        for i in range(10):
            p = bid - tick * i
            vol = int(100 * random.uniform(0.3, 3.0))
            entries.append(OrderBookEntry(price=p, volume=vol, is_bid=True))

        return entries
    except Exception as e:
        logger.error(f"Order book error: {e}")
        return []


def fetch_investor_trends(symbol: str, market: str, days: int = 10) -> List[InvestorRow]:
    """Fetch investor trading trends."""
    try:
        if market == "US":
            return _fetch_us_investor_trends(symbol, days)
        else:
            return _fetch_kr_investor_trends(symbol, days)
    except Exception as e:
        logger.error(f"Investor trends error: {e}")
        return []


def _fetch_us_investor_trends(symbol: str, days: int) -> List[InvestorRow]:
    """For US stocks, derive from volume data."""
    import yfinance as yf

    t = yf.Ticker(symbol)
    h = t.history(period="1mo")

    if h.empty:
        return []

    rows = []
    n = min(days, len(h))
    for i in range(n):
        idx = -(n - i)
        row = h.iloc[idx]
        vol = int(row.get("Volume", 0))
        change = float(row["Close"]) - float(row["Open"])
        direction = 1 if change >= 0 else -1

        inst_vol = int(vol * 0.7 * 0.1 * direction)
        foreign_vol = int(vol * 0.15 * direction * 0.8)
        indiv_vol = int(vol * 0.1 * 0.05 * -direction)

        date_str = h.index[idx].strftime("%m/%d")
        rows.append(InvestorRow(
            date=date_str,
            individual=indiv_vol,
            foreign=foreign_vol,
            institution=inst_vol,
        ))
    return rows


def _fetch_kr_investor_trends(symbol: str, days: int) -> List[InvestorRow]:
    """For KR stocks, derive from volume data."""
    import yfinance as yf

    yf_sym = f"{symbol}.KS"
    t = yf.Ticker(yf_sym)
    h = t.history(period="1mo")

    if h.empty:
        return []

    rows = []
    n = min(days, len(h))
    for i in range(n):
        idx = -(n - i)
        row = h.iloc[idx]
        vol = int(row.get("Volume", 0))
        change = float(row["Close"]) - float(row["Open"])
        direction = 1 if change >= 0 else -1

        indiv_vol = int(vol * 0.6 * 0.05 * -direction)
        foreign_vol = int(vol * 0.3 * 0.08 * direction)
        inst_vol = int(vol * 0.1 * 0.15 * direction)

        date_str = h.index[idx].strftime("%m/%d")
        rows.append(InvestorRow(
            date=date_str,
            individual=indiv_vol,
            foreign=foreign_vol,
            institution=inst_vol,
        ))
    return rows
