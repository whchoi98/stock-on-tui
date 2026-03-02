from __future__ import annotations

import logging
from datetime import datetime, date, timedelta
from typing import List, Optional

from models.stock import StockQuote, MarketIndex, StockDetail
from config import KR_STOCK_NAMES, KR_STOCK_SECTORS, KR_INDICES

import math

logger = logging.getLogger(__name__)


def _safe_float(v, default=0.0) -> float:
    try:
        f = float(v)
        return default if math.isnan(f) else f
    except (TypeError, ValueError):
        return default


def _get_recent_trading_day() -> str:
    """Get the most recent likely trading day as YYYYMMDD string."""
    today = date.today()
    # Go back up to 7 days to find a weekday
    for i in range(7):
        d = today - timedelta(days=i)
        if d.weekday() < 5:  # Mon-Fri
            return d.strftime("%Y%m%d")
    return today.strftime("%Y%m%d")


def _get_prev_trading_day(ref_date: str) -> str:
    """Get the trading day before ref_date."""
    d = datetime.strptime(ref_date, "%Y%m%d").date()
    for i in range(1, 10):
        prev = d - timedelta(days=i)
        if prev.weekday() < 5:
            return prev.strftime("%Y%m%d")
    return (d - timedelta(days=1)).strftime("%Y%m%d")


def fetch_kr_indices() -> List[MarketIndex]:
    try:
        import yfinance as yf

        symbols = list(KR_INDICES.keys())
        df = yf.download(symbols, period="2d", group_by="ticker", threads=False, progress=False)
        indices = []

        for sym in symbols:
            try:
                if len(symbols) > 1 and sym in df.columns.get_level_values(0):
                    sub = df[sym]
                elif len(symbols) == 1:
                    sub = df
                else:
                    continue
                if sub.empty:
                    continue
                latest_val = _safe_float(sub.iloc[-1]["Close"])
                prev_val = _safe_float(sub.iloc[-2]["Close"]) if len(sub) > 1 else latest_val
                if latest_val == 0:
                    continue
                change = latest_val - prev_val
                pct = (change / prev_val * 100) if prev_val else 0
                indices.append(MarketIndex(
                    symbol=sym,
                    name=KR_INDICES[sym],
                    value=latest_val,
                    change=change,
                    change_pct=pct,
                    last_updated=datetime.now(),
                ))
            except Exception as e:
                logger.warning(f"Failed to parse KR index {sym}: {e}")

        return indices
    except Exception as e:
        logger.error(f"Failed to fetch KR indices: {e}")
        return []


def _fetch_kr_single(sym: str, today: str, prev: str):
    """Fetch OHLCV for a single KR stock (no market cap — saves rate limit)."""
    from pykrx import stock
    try:
        df = stock.get_market_ohlcv_by_date(prev, today, sym)
        if df.empty:
            return None
        latest = df.iloc[-1]
        prev_row = df.iloc[-2] if len(df) > 1 else latest
        price = float(latest["종가"])
        if price == 0:
            return None
        prev_close = float(prev_row["종가"])
        if prev_close == 0:
            prev_close = price

        return {
            "symbol": sym, "price": price,
            "prev_close": prev_close, "volume": int(latest["거래량"]),
            "market_cap": 0,
        }
    except Exception:
        return None


def fetch_kr_quotes(symbols: List[str]) -> List[StockQuote]:
    try:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        today = _get_recent_trading_day()
        prev = _get_prev_trading_day(today)

        # Fetch all KR stocks in parallel (10 threads)
        results = {}
        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = {pool.submit(_fetch_kr_single, sym, today, prev): sym for sym in symbols}
            for future in as_completed(futures, timeout=45):
                sym = futures[future]
                try:
                    results[sym] = future.result()
                except Exception:
                    results[sym] = None

        quotes = []
        for sym in symbols:
            data = results.get(sym)
            if data is None:
                continue
            change = data["price"] - data["prev_close"]
            pct = (change / data["prev_close"] * 100) if data["prev_close"] else 0

            quotes.append(StockQuote(
                symbol=sym,
                name=KR_STOCK_NAMES.get(sym, sym),
                price=data["price"],
                change=change,
                change_pct=pct,
                volume=data["volume"],
                market="KR",
                currency="KRW",
                sector=KR_STOCK_SECTORS.get(sym, ""),
                market_cap=data["market_cap"],
                last_updated=datetime.now(),
            ))

        return quotes
    except Exception as e:
        logger.error(f"Failed to fetch KR quotes: {e}")
        return []


def fetch_kr_stock_detail(symbol: str) -> Optional[StockDetail]:
    """Phase 1: OHLCV history — returns quickly."""
    try:
        from pykrx import stock

        today = _get_recent_trading_day()
        year_ago = (date.today() - timedelta(days=400)).strftime("%Y%m%d")

        hist = stock.get_market_ohlcv_by_date(year_ago, today, symbol)
        if hist.empty:
            return None

        latest = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) > 1 else latest
        price = float(latest["종가"])
        prev_close = float(prev["종가"])
        change = price - prev_close
        pct = (change / prev_close * 100) if prev_close else 0

        closes = hist["종가"].dropna()

        def _slice(n):
            data = closes.tolist()[-n:]
            dates = [d.strftime("%m/%d") for d in closes.index[-n:]]
            return data, dates

        history_7d, dates_7d = _slice(7)
        history_30d, dates_30d = _slice(30)
        history_90d, dates_90d = _slice(90)
        history_1y, dates_1y = _slice(250)

        w52_high = float(hist["고가"].max()) if not hist.empty else price
        w52_low = float(hist["저가"].min()) if not hist.empty else price

        return StockDetail(
            symbol=symbol,
            name=KR_STOCK_NAMES.get(symbol, symbol),
            market="KR", currency="KRW",
            price=price, change=change, change_pct=pct,
            open_price=float(latest["시가"]),
            high=float(latest["고가"]),
            low=float(latest["저가"]),
            prev_close=prev_close,
            volume=int(latest["거래량"]),
            avg_volume=int(hist["거래량"].mean()) if len(hist) > 1 else 0,
            week52_high=w52_high, week52_low=w52_low,
            history_7d=history_7d, history_30d=history_30d,
            history_90d=history_90d, history_1y=history_1y,
            history_dates_7d=dates_7d, history_dates_30d=dates_30d,
            history_dates_90d=dates_90d, history_dates_1y=dates_1y,
            sector=KR_STOCK_SECTORS.get(symbol, ""),
            last_updated=datetime.now(),
        )
    except Exception as e:
        logger.error(f"Failed to fetch KR detail for {symbol}: {e}")
        return None


def fetch_kr_market_caps(symbols: List[str]) -> dict:
    """Fetch market caps for KR stocks via Naver Finance (no rate limit)."""
    import httpx
    import re
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _get_cap(sym):
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            r = httpx.get(
                f"https://finance.naver.com/item/main.naver?code={sym}",
                headers=headers, timeout=8,
            )
            if r.status_code != 200:
                return sym, 0
            # 시가총액(억) table: <td>12,816,016</td>
            m = re.search(r'시가총액\(억\)</span></th>\s*<td>([\d,]+)</td>', r.text)
            if m:
                return sym, float(m.group(1).replace(",", "")) * 1e8  # 억 → 원
            return sym, 0
        except Exception:
            return sym, 0

    result = {}
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = [pool.submit(_get_cap, s) for s in symbols]
        for f in as_completed(futures, timeout=25):
            try:
                sym, cap = f.result()
                if cap:
                    result[sym] = cap
            except Exception:
                pass
    return result


def fetch_kr_fundamentals(symbol: str) -> dict:
    """Phase 2: PER/EPS/PBR from Naver Finance + market cap from yfinance."""
    import httpx
    import re

    result = {}

    # Naver Finance scrape (PER/EPS/PBR — fast, no rate limit)
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = httpx.get(
            f"https://finance.naver.com/item/main.naver?code={symbol}",
            headers=headers, timeout=10, follow_redirects=True,
        )
        if r.status_code == 200:
            text = r.text
            m = re.search(r'PER\(배\)</strong></th>\s*<td[^>]*>\s*([\d,.]+)', text)
            if m:
                result["pe_ratio"] = float(m.group(1).replace(",", ""))
            m = re.search(r'EPS\(원\)</strong></th>\s*<td[^>]*>\s*([\d,.]+)', text)
            if m:
                result["eps"] = float(m.group(1).replace(",", ""))
            m = re.search(r'PBR\(배\)</strong></th>\s*<td[^>]*>\s*([\d,.]+)', text)
            if m:
                result["beta"] = float(m.group(1).replace(",", ""))  # PBR in beta slot
    except Exception as e:
        logger.warning(f"Naver scrape failed for {symbol}: {e}")

    # Market cap from yfinance fast_info
    try:
        import yfinance as yf
        fi = yf.Ticker(f"{symbol}.KS").fast_info
        mcap = getattr(fi, 'market_cap', 0)
        if mcap:
            result["market_cap"] = mcap
    except Exception:
        pass

    return result
