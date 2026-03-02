# 미국 주식 데이터 서비스 모듈 / US stock data service module
# yfinance를 사용하여 미국 주식 시세, 지수, 상세 정보, 펀더멘털 데이터를 조회합니다
# Fetches US stock quotes, indices, details, and fundamentals using yfinance

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

from models.stock import StockQuote, MarketIndex, StockDetail
from config import US_STOCK_NAMES, US_STOCK_SECTORS, US_INDICES

import math

logger = logging.getLogger(__name__)


# --- 유틸리티 함수들 / Utility functions ---

def _isnan(v) -> bool:
    # 값이 NaN인지 안전하게 확인 / Safely check if a value is NaN
    try:
        return math.isnan(v)
    except (TypeError, ValueError):
        return False


def _safe_float(v, default=0.0) -> float:
    # 안전하게 float로 변환 (NaN이면 기본값 반환) / Safely convert to float (returns default if NaN)
    try:
        f = float(v)
        return default if math.isnan(f) else f
    except (TypeError, ValueError):
        return default


def _safe_int(v, default=0) -> int:
    # 안전하게 int로 변환 (NaN이면 기본값 반환) / Safely convert to int (returns default if NaN)
    try:
        f = float(v)
        return default if math.isnan(f) else int(f)
    except (TypeError, ValueError):
        return default


def fetch_us_indices() -> List[MarketIndex]:
    # 미국 주요 지수(S&P 500, 나스닥, 다우 등) 조회 / Fetch major US indices (S&P 500, Nasdaq, Dow, etc.)
    # 반환: MarketIndex 리스트 / Returns: list of MarketIndex
    try:
        import yfinance as yf

        symbols = list(US_INDICES.keys())
        # yfinance로 2일치 데이터 일괄 다운로드 / Batch download 2 days of data via yfinance
        df = yf.download(symbols, period="2d", group_by="ticker", threads=False, progress=False)
        indices = []
        for sym in symbols:
            try:
                # 멀티 티커 DataFrame에서 개별 종목 데이터 추출 / Extract individual ticker data from multi-ticker DataFrame
                if len(symbols) > 1 and sym in df.columns.get_level_values(0):
                    sub = df[sym]
                elif len(symbols) == 1:
                    sub = df
                else:
                    continue
                if sub.empty:
                    continue
                # 최신 종가와 전일 종가로 등락 계산 / Calculate change from latest and previous close prices
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
    # 심볼 묶음을 yfinance로 일괄 다운로드 / Download a chunk of symbols via yfinance in batch
    # 매개변수: symbols(종목 리스트), period(조회 기간) / Parameters: symbols(ticker list), period(query period)
    """Download a chunk of symbols."""
    import yfinance as yf
    return yf.download(symbols, period=period, group_by="ticker", threads=False, progress=False)


def _parse_df(df, symbols: List[str]) -> List[StockQuote]:
    # 다운로드된 DataFrame을 StockQuote 리스트로 파싱 / Parse a downloaded DataFrame into StockQuote list
    # 매개변수: df(yfinance DataFrame), symbols(종목코드 리스트) / Parameters: df(yfinance DataFrame), symbols(ticker list)
    """Parse a downloaded DataFrame into StockQuote list."""
    quotes = []
    # 멀티 티커 여부 확인 / Check if multi-ticker download
    multi = len(symbols) > 1
    # 멀티 티커 DataFrame의 첫 번째 레벨 컬럼 추출 / Extract first-level columns from multi-ticker DataFrame
    level0 = set(df.columns.get_level_values(0)) if multi and hasattr(df.columns, 'get_level_values') else set()
    for sym in symbols:
        try:
            # 멀티/싱글 티커에 따라 서브 DataFrame 추출 / Extract sub-DataFrame based on multi/single ticker
            if multi:
                if sym not in level0:
                    continue
                sub = df[sym]
            else:
                sub = df
            if sub.empty:
                continue
            # 최신 행과 전일 행에서 가격 추출 / Extract prices from latest and previous rows
            latest = sub.iloc[-1]
            prev = sub.iloc[-2] if len(sub) > 1 else latest
            price = _safe_float(latest["Close"])
            prev_close = _safe_float(prev["Close"])
            if price == 0:
                continue
            # 등락금액 및 등락률 계산 / Calculate price change and change percentage
            change = price - prev_close
            pct = (change / prev_close * 100) if prev_close else 0.0
            # NaN 제거한 종가 히스토리 (7일 스파크라인용) / Close price history with NaN removed (for 7-day sparkline)
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
    # 미국 주식 시가총액을 yfinance fast_info로 병렬 조회 / Fetch US stock market caps via yfinance fast_info in parallel
    # 매개변수: symbols(종목코드 리스트) / Parameters: symbols(ticker list)
    # 반환: {종목코드: 시가총액} 딕셔너리 / Returns: {symbol: market_cap} dictionary
    """Fetch market caps for US stocks via yfinance fast_info."""
    import yfinance as yf
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _get_cap(sym):
        # 개별 종목 시가총액 조회 / Fetch market cap for a single stock
        try:
            return sym, yf.Ticker(sym).fast_info.market_cap or 0
        except Exception:
            return sym, 0

    result = {}
    # 10개 스레드로 병렬 조회 (타임아웃 20초) / Parallel fetch with 10 threads (timeout 20s)
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
    # 미국 주식 시세를 청크 단위 병렬 다운로드로 조회 (시가총액 제외 - API 제한 절약) / Fetch US stock quotes using chunked parallel download (no market cap - saves rate limit)
    # 매개변수: symbols(종목코드 리스트) / Parameters: symbols(ticker list)
    # 반환: StockQuote 리스트 / Returns: list of StockQuote
    """Fetch US stock quotes using chunked parallel download (no market cap — saves rate limit)."""
    try:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        # 10개씩 청크로 분할 / Split into chunks of 10
        chunk_size = 10
        chunks = [symbols[i:i + chunk_size] for i in range(0, len(symbols), chunk_size)]

        # 각 청크를 병렬로 다운로드 / Download each chunk in parallel
        dfs = {}
        with ThreadPoolExecutor(max_workers=len(chunks)) as pool:
            chunk_futures = {pool.submit(_download_chunk, c): i for i, c in enumerate(chunks)}
            for f in as_completed(chunk_futures, timeout=25):
                idx = chunk_futures[f]
                try:
                    dfs[idx] = f.result()
                except Exception as e:
                    logger.warning(f"Chunk {idx} download failed: {e}")

        # 다운로드된 DataFrame들을 순서대로 파싱 / Parse downloaded DataFrames in order
        quotes = []
        for i, chunk_syms in enumerate(chunks):
            if i in dfs:
                quotes.extend(_parse_df(dfs[i], chunk_syms))
        return quotes
    except Exception as e:
        logger.error(f"Failed to fetch US quotes: {e}")
        return []


def fetch_us_stock_detail(symbol: str) -> Optional[StockDetail]:
    # 미국 주식 상세 정보 조회 (1단계: fast_info + 가격 히스토리) / Fetch US stock detail (Phase 1: fast_info + price history)
    # 빠른 응답을 위해 fast_info와 1년 히스토리만 사용 / Uses only fast_info and 1-year history for quick response
    # 매개변수: symbol(종목코드) / Parameters: symbol(ticker)
    # 반환: StockDetail 또는 None / Returns: StockDetail or None
    """Phase 1: fast_info + history — returns quickly."""
    try:
        import yfinance as yf

        ticker = yf.Ticker(symbol)

        # fast_info에서 기본 가격 정보 추출 / Extract basic price info from fast_info
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

        # 등락금액 및 등락률 계산 / Calculate price change and change percentage
        change = price - prev_close if prev_close else 0
        pct = (change / prev_close * 100) if prev_close else 0

        # 1년 히스토리를 가져와서 7일/30일/90일/1년 구간으로 분할 / Fetch 1-year history and split into 7d/30d/90d/1y periods
        hist_1y = ticker.history(period="1y")
        hist_90d = hist_1y.tail(90) if len(hist_1y) >= 90 else hist_1y
        hist_30d = hist_1y.tail(30) if len(hist_1y) >= 30 else hist_1y
        hist_7d = hist_1y.tail(7) if len(hist_1y) >= 7 else hist_1y
        # 최근 10일 평균 거래량 계산 / Calculate average volume over last 10 days
        avg_volume = int(hist_1y["Volume"].tail(10).mean()) if len(hist_1y) >= 10 else 0

        def _extract(df):
            # DataFrame에서 종가 리스트와 날짜 문자열 리스트 추출 / Extract close price list and date string list from DataFrame
            closes = df["Close"].dropna()
            return closes.tolist(), [d.strftime("%m/%d") for d in closes.index]

        # 각 기간별 종가 및 날짜 추출 / Extract close prices and dates for each period
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
    # Yahoo Finance 페이지에서 PER/EPS/배당수익률/베타를 스크래핑 (crumb 불필요) / Scrape PE/EPS/Div/Beta from Yahoo Finance page (no crumb needed)
    # 매개변수: url(Yahoo Finance 종목 페이지 URL) / Parameters: url(Yahoo Finance quote page URL)
    # 반환: 펀더멘털 데이터 딕셔너리 / Returns: fundamentals data dictionary
    """Scrape PE/EPS/Div/Beta from Yahoo Finance quote page (no crumb needed)."""
    import httpx
    import re

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    # Yahoo Finance 페이지 HTTP 요청 / HTTP request to Yahoo Finance page
    r = httpx.get(url, headers=headers, timeout=15, follow_redirects=True)
    if r.status_code != 200:
        return {}

    text = r.text
    result = {}

    # HTML에서 PER(주가수익비율) 추출 / Extract PE ratio (Price-to-Earnings) from HTML
    # PE from HTML: data-field="trailingPE" ...>33.44<
    m = re.search(r'trailingPE"[^>]*>([\d.]+)', text)
    if m:
        result["pe_ratio"] = float(m.group(1))

    # HTML에서 EPS(주당순이익) 추출 / Extract EPS (Earnings Per Share) from HTML
    # EPS from HTML: EPS (TTM)">...</span>...<fin-streamer ...>7.90</fin-streamer>
    m = re.search(r'EPS \(TTM\).*?data-value="([\d.-]+)"', text, re.DOTALL)
    if not m:
        m = re.search(r'epsTrailingTwelveMonths"[^>]*data-value="([\d.-]+)"', text)
    if m:
        result["eps"] = float(m.group(1))

    # 페이지 내장 JSON에서 배당수익률 추출 / Extract dividend yield from JSON embedded in page
    # Dividend yield from JSON embedded in page
    m = re.search(r'"dividendYield":\{"raw":([\d.]+)', text)
    if m:
        result["dividend_yield"] = float(m.group(1))

    # HTML에서 베타(5년 월간) 추출 / Extract Beta (5Y Monthly) from HTML
    # Beta from HTML: Beta (5Y Monthly)">...</span><span class="value ...>1.11</span>
    m = re.search(r'Beta \(5Y Monthly\).*?class="value[^"]*">([\d.]+)<', text, re.DOTALL)
    if m:
        result["beta"] = float(m.group(1))

    # 페이지 내장 JSON에서 시가총액 추출 / Extract market cap from JSON embedded in page
    # Market cap from JSON
    m = re.search(r'"marketCap":\{"raw":(\d+)', text)
    if m:
        result["market_cap"] = float(m.group(1))

    return result


def fetch_us_fundamentals(symbol: str) -> dict:
    # 미국 주식 펀더멘털 조회 (2단계: Yahoo Finance 스크래핑으로 API 제한 우회) / Fetch US stock fundamentals (Phase 2: scraping Yahoo Finance to bypass rate limit)
    # 매개변수: symbol(종목코드) / Parameters: symbol(ticker)
    # 반환: PER/EPS/배당수익률/베타 딕셔너리 / Returns: PE/EPS/dividend yield/beta dictionary
    """Phase 2: fetch PE/EPS/Div/Beta by scraping Yahoo Finance (bypasses rate limit)."""
    try:
        # Yahoo Finance 종목 페이지를 스크래핑하여 펀더멘털 데이터 추출 / Scrape Yahoo Finance quote page to extract fundamentals
        return _scrape_fundamentals(f"https://finance.yahoo.com/quote/{symbol}/")
    except Exception as e:
        logger.warning(f"Fundamentals scrape failed for {symbol}: {e}")
        return {}
