from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

from models.stock import StockQuote, MarketIndex, StockDetail
from config import US_STOCK_NAMES, US_STOCK_SECTORS, US_INDICES

import math

logger = logging.getLogger(__name__)


def _isnan(v) -> bool:
    try:
        return math.isnan(v)
    except (TypeError, ValueError):
        return False


def _safe_float(v, default=0.0) -> float:
    try:
        f = float(v)
        return default if math.isnan(f) else f
    except (TypeError, ValueError):
        return default


def _safe_int(v, default=0) -> int:
    try:
        f = float(v)
        return default if math.isnan(f) else int(f)
    except (TypeError, ValueError):
        return default


def fetch_us_indices() -> List[MarketIndex]:
    try:
        import yfinance as yf

        symbols = list(US_INDICES.keys())
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
                latest = sub.iloc[-1]
                prev = sub.iloc[-2] if len(sub) > 1 else latest
                value = _safe_float(latest["Close"])
                prev_close = _safe_float(prev["Close"])
                if value == 0:
                    continue
                change = value - prev_close
                pct = (change / prev_close * 100) if prev_close else 0.0
                indices.append(MarketIndex(
                    symbol=sym,
                    name=US_INDICES[sym],
                    value=value,
                    change=change,
                    change_pct=pct,
                    last_updated=datetime.now(),
                ))
            except Exception as e:
                logger.warning(f"Failed to parse index {sym}: {e}")
        return indices
    except Exception as e:
        logger.error(f"Failed to fetch US indices: {e}")
        return []


def _download_chunk(symbols, period="7d"):
    """Download a chunk of symbols."""
    import yfinance as yf
    return yf.download(symbols, period=period, group_by="ticker", threads=False, progress=False)


def _parse_df(df, symbols: List[str]) -> List[StockQuote]:
    """Parse a downloaded DataFrame into StockQuote list."""
    quotes = []
    multi = len(symbols) > 1
    level0 = set(df.columns.get_level_values(0)) if multi and hasattr(df.columns, 'get_level_values') else set()
    for sym in symbols:
        try:
            if multi:
                if sym not in level0:
                    continue
                sub = df[sym]
            else:
                sub = df
            if sub.empty:
                continue
            latest = sub.iloc[-1]
            prev = sub.iloc[-2] if len(sub) > 1 else latest
            price = _safe_float(latest["Close"])
            prev_close = _safe_float(prev["Close"])
            if price == 0:
                continue
            change = price - prev_close
            pct = (change / prev_close * 100) if prev_close else 0.0
            history = [x for x in sub["Close"].dropna().tolist() if not _isnan(x)]
            quotes.append(StockQuote(
                symbol=sym,
                name=US_STOCK_NAMES.get(sym, sym),
                price=price,
                change=change,
                change_pct=pct,
                volume=_safe_int(latest.get("Volume", 0)),
                market="US",
                currency="USD",
                sector=US_STOCK_SECTORS.get(sym, ""),
                market_cap=0,
                history_7d=history,
                last_updated=datetime.now(),
            ))
        except Exception as e:
            logger.warning(f"Failed to parse {sym}: {e}")
    return quotes


def fetch_us_market_caps(symbols: List[str]) -> dict:
    """Fetch market caps for US stocks via yfinance fast_info."""
    import yfinance as yf
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _get_cap(sym):
        try:
            return sym, yf.Ticker(sym).fast_info.market_cap or 0
        except Exception:
            return sym, 0

    result = {}
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = [pool.submit(_get_cap, s) for s in symbols]
        for f in as_completed(futures, timeout=20):
            try:
                sym, cap = f.result()
                if cap:
                    result[sym] = cap
            except Exception:
                pass
    return result


def fetch_us_quotes(symbols: List[str]) -> List[StockQuote]:
    """Fetch US stock quotes using chunked parallel download (no market cap — saves rate limit)."""
    try:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        chunk_size = 10
        chunks = [symbols[i:i + chunk_size] for i in range(0, len(symbols), chunk_size)]

        dfs = {}
        with ThreadPoolExecutor(max_workers=len(chunks)) as pool:
            chunk_futures = {pool.submit(_download_chunk, c): i for i, c in enumerate(chunks)}
            for f in as_completed(chunk_futures, timeout=25):
                idx = chunk_futures[f]
                try:
                    dfs[idx] = f.result()
                except Exception as e:
                    logger.warning(f"Chunk {idx} download failed: {e}")

        quotes = []
        for i, chunk_syms in enumerate(chunks):
            if i in dfs:
                quotes.extend(_parse_df(dfs[i], chunk_syms))
        return quotes
    except Exception as e:
        logger.error(f"Failed to fetch US quotes: {e}")
        return []


def fetch_us_stock_detail(symbol: str) -> Optional[StockDetail]:
    """Phase 1: fast_info + history — returns quickly."""
    try:
        import yfinance as yf

        ticker = yf.Ticker(symbol)

        fi = ticker.fast_info
        price = getattr(fi, 'last_price', 0) or 0
        prev_close = getattr(fi, 'previous_close', 0) or 0
        open_price = getattr(fi, 'open', 0) or 0
        day_high = getattr(fi, 'day_high', 0) or 0
        day_low = getattr(fi, 'day_low', 0) or 0
        market_cap = getattr(fi, 'market_cap', 0) or 0
        volume = getattr(fi, 'last_volume', 0) or 0
        w52_high = getattr(fi, 'year_high', 0) or 0
        w52_low = getattr(fi, 'year_low', 0) or 0

        change = price - prev_close if prev_close else 0
        pct = (change / prev_close * 100) if prev_close else 0

        hist_1y = ticker.history(period="1y")
        hist_90d = hist_1y.tail(90) if len(hist_1y) >= 90 else hist_1y
        hist_30d = hist_1y.tail(30) if len(hist_1y) >= 30 else hist_1y
        hist_7d = hist_1y.tail(7) if len(hist_1y) >= 7 else hist_1y
        avg_volume = int(hist_1y["Volume"].tail(10).mean()) if len(hist_1y) >= 10 else 0

        def _extract(df):
            closes = df["Close"].dropna()
            return closes.tolist(), [d.strftime("%m/%d") for d in closes.index]

        history_7d, dates_7d = _extract(hist_7d)
        history_30d, dates_30d = _extract(hist_30d)
        history_90d, dates_90d = _extract(hist_90d)
        history_1y, dates_1y = _extract(hist_1y)

        return StockDetail(
            symbol=symbol,
            name=US_STOCK_NAMES.get(symbol, symbol),
            market="US", currency="USD",
            price=price, change=change, change_pct=pct,
            open_price=open_price, high=day_high, low=day_low,
            prev_close=prev_close, volume=volume, avg_volume=avg_volume,
            market_cap=market_cap,
            week52_high=w52_high, week52_low=w52_low,
            history_7d=history_7d, history_30d=history_30d,
            history_90d=history_90d, history_1y=history_1y,
            history_dates_7d=dates_7d, history_dates_30d=dates_30d,
            history_dates_90d=dates_90d, history_dates_1y=dates_1y,
            sector=US_STOCK_SECTORS.get(symbol, ""),
            last_updated=datetime.now(),
        )
    except Exception as e:
        logger.error(f"Failed to fetch detail for {symbol}: {e}")
        return None


def _scrape_fundamentals(url: str) -> dict:
    """Scrape PE/EPS/Div/Beta from Yahoo Finance quote page (no crumb needed)."""
    import httpx
    import re

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    r = httpx.get(url, headers=headers, timeout=15, follow_redirects=True)
    if r.status_code != 200:
        return {}

    text = r.text
    result = {}

    # PE from HTML: data-field="trailingPE" ...>33.44<
    m = re.search(r'trailingPE"[^>]*>([\d.]+)', text)
    if m:
        result["pe_ratio"] = float(m.group(1))

    # EPS from HTML: EPS (TTM)">...</span>...<fin-streamer ...>7.90</fin-streamer>
    m = re.search(r'EPS \(TTM\).*?data-value="([\d.-]+)"', text, re.DOTALL)
    if not m:
        m = re.search(r'epsTrailingTwelveMonths"[^>]*data-value="([\d.-]+)"', text)
    if m:
        result["eps"] = float(m.group(1))

    # Dividend yield from JSON embedded in page
    m = re.search(r'"dividendYield":\{"raw":([\d.]+)', text)
    if m:
        result["dividend_yield"] = float(m.group(1))

    # Beta from HTML: Beta (5Y Monthly)">...</span><span class="value ...>1.11</span>
    m = re.search(r'Beta \(5Y Monthly\).*?class="value[^"]*">([\d.]+)<', text, re.DOTALL)
    if m:
        result["beta"] = float(m.group(1))

    # Market cap from JSON
    m = re.search(r'"marketCap":\{"raw":(\d+)', text)
    if m:
        result["market_cap"] = float(m.group(1))

    return result


def fetch_us_fundamentals(symbol: str) -> dict:
    """Phase 2: fetch PE/EPS/Div/Beta by scraping Yahoo Finance (bypasses rate limit)."""
    try:
        return _scrape_fundamentals(f"https://finance.yahoo.com/quote/{symbol}/")
    except Exception as e:
        logger.warning(f"Fundamentals scrape failed for {symbol}: {e}")
        return {}
