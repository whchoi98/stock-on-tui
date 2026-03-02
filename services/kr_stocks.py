# 한국 주식 데이터 서비스 모듈 / Korean stock data service module
# pykrx 및 yfinance를 사용하여 한국 주식 시세, 지수, 상세 정보, 펀더멘털 데이터를 조회합니다
# Fetches Korean stock quotes, indices, details, and fundamentals using pykrx and yfinance

from __future__ import annotations

import logging
from datetime import datetime, date, timedelta
from typing import List, Optional

from models.stock import StockQuote, MarketIndex, StockDetail
from config import KR_STOCK_NAMES, KR_STOCK_SECTORS, KR_INDICES

import math

logger = logging.getLogger(__name__)


# --- 유틸리티 함수들 / Utility functions ---

def _safe_float(v, default=0.0) -> float:
    # 안전하게 float로 변환 (NaN이면 기본값 반환) / Safely convert to float (returns default if NaN)
    try:
        f = float(v)
        return default if math.isnan(f) else f
    except (TypeError, ValueError):
        return default


def _get_recent_trading_day() -> str:
    # 가장 최근 거래일을 YYYYMMDD 문자열로 반환 / Get the most recent likely trading day as YYYYMMDD string
    # 주말을 건너뛰고 평일을 찾음 / Skips weekends to find a weekday
    """Get the most recent likely trading day as YYYYMMDD string."""
    today = date.today()
    # 최대 7일 전까지 탐색하여 평일 찾기 / Go back up to 7 days to find a weekday
    for i in range(7):
        d = today - timedelta(days=i)
        if d.weekday() < 5:  # 월~금 / Mon-Fri
            return d.strftime("%Y%m%d")
    return today.strftime("%Y%m%d")


def _get_prev_trading_day(ref_date: str) -> str:
    # 기준일 이전의 거래일 반환 / Get the trading day before ref_date
    # 매개변수: ref_date(기준일, YYYYMMDD 형식) / Parameters: ref_date(reference date, YYYYMMDD format)
    """Get the trading day before ref_date."""
    d = datetime.strptime(ref_date, "%Y%m%d").date()
    # 최대 10일 전까지 탐색하여 평일 찾기 / Search up to 10 days back to find a weekday
    for i in range(1, 10):
        prev = d - timedelta(days=i)
        if prev.weekday() < 5:
            return prev.strftime("%Y%m%d")
    return (d - timedelta(days=1)).strftime("%Y%m%d")


def fetch_kr_indices() -> List[MarketIndex]:
    # 한국 주요 지수(코스피, 코스닥 등) 조회 / Fetch major Korean indices (KOSPI, KOSDAQ, etc.)
    # 반환: MarketIndex 리스트 / Returns: list of MarketIndex
    try:
        import yfinance as yf

        symbols = list(KR_INDICES.keys())
        # yfinance로 2일치 데이터 일괄 다운로드 / Batch download 2 days of data via yfinance
        df = yf.download(symbols, period="2d", group_by="ticker", threads=False, progress=False)
        indices = []

        for sym in symbols:
            try:
                # 멀티 티커 DataFrame에서 개별 지수 데이터 추출 / Extract individual index data from multi-ticker DataFrame
                if len(symbols) > 1 and sym in df.columns.get_level_values(0):
                    sub = df[sym]
                elif len(symbols) == 1:
                    sub = df
                else:
                    continue
                if sub.empty:
                    continue
                # 최신 종가와 전일 종가로 등락 계산 / Calculate change from latest and previous close prices
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
    # 개별 한국 주식의 OHLCV 데이터 조회 (시가총액 제외 - API 제한 절약) / Fetch OHLCV for a single KR stock (no market cap - saves rate limit)
    # 매개변수: sym(종목코드), today(오늘 날짜), prev(전 거래일) / Parameters: sym(ticker), today(today's date), prev(previous trading day)
    """Fetch OHLCV for a single KR stock (no market cap — saves rate limit)."""
    from pykrx import stock
    try:
        # pykrx로 전일~오늘 OHLCV 데이터 조회 / Fetch OHLCV data from prev to today via pykrx
        df = stock.get_market_ohlcv_by_date(prev, today, sym)
        if df.empty:
            return None
        latest = df.iloc[-1]
        prev_row = df.iloc[-2] if len(df) > 1 else latest
        # 종가(Close)와 전일 종가 추출 / Extract close price and previous close price
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
    # 한국 주식 시세를 병렬로 조회 / Fetch Korean stock quotes in parallel
    # 매개변수: symbols(종목코드 리스트) / Parameters: symbols(ticker list)
    # 반환: StockQuote 리스트 / Returns: list of StockQuote
    try:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        # 최근 거래일과 전 거래일 계산 / Calculate most recent and previous trading days
        today = _get_recent_trading_day()
        prev = _get_prev_trading_day(today)

        # 10개 스레드로 모든 한국 주식 병렬 조회 / Fetch all KR stocks in parallel (10 threads)
        results = {}
        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = {pool.submit(_fetch_kr_single, sym, today, prev): sym for sym in symbols}
            for future in as_completed(futures, timeout=45):
                sym = futures[future]
                try:
                    results[sym] = future.result()
                except Exception:
                    results[sym] = None

        # 결과를 StockQuote 객체로 변환 / Convert results to StockQuote objects
        quotes = []
        for sym in symbols:
            data = results.get(sym)
            if data is None:
                continue
            # 등락금액 및 등락률 계산 / Calculate price change and change percentage
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
    # 한국 주식 상세 정보 조회 (1단계: OHLCV 히스토리) / Fetch Korean stock detail (Phase 1: OHLCV history)
    # 빠른 응답을 위해 pykrx로 약 1년치 OHLCV 데이터만 사용 / Uses only ~1 year of OHLCV data from pykrx for quick response
    # 매개변수: symbol(종목코드) / Parameters: symbol(ticker)
    # 반환: StockDetail 또는 None / Returns: StockDetail or None
    """Phase 1: OHLCV history — returns quickly."""
    try:
        from pykrx import stock

        today = _get_recent_trading_day()
        # 400일 전 날짜 (1년치 데이터 확보용) / 400 days ago (to ensure 1 year of data)
        year_ago = (date.today() - timedelta(days=400)).strftime("%Y%m%d")

        # pykrx로 약 1년치 OHLCV 히스토리 조회 / Fetch ~1 year of OHLCV history via pykrx
        hist = stock.get_market_ohlcv_by_date(year_ago, today, symbol)
        if hist.empty:
            return None

        # 최신 행과 전일 행에서 종가 추출 / Extract close prices from latest and previous rows
        latest = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) > 1 else latest
        price = float(latest["종가"])
        prev_close = float(prev["종가"])
        # 등락금액 및 등락률 계산 / Calculate price change and change percentage
        change = price - prev_close
        pct = (change / prev_close * 100) if prev_close else 0

        closes = hist["종가"].dropna()

        def _slice(n):
            # 종가 데이터에서 최근 n개 항목과 날짜를 추출 / Extract last n items and dates from close price data
            data = closes.tolist()[-n:]
            dates = [d.strftime("%m/%d") for d in closes.index[-n:]]
            return data, dates

        # 각 기간별 종가 및 날짜 추출 / Extract close prices and dates for each period
        history_7d, dates_7d = _slice(7)
        history_30d, dates_30d = _slice(30)
        history_90d, dates_90d = _slice(90)
        history_1y, dates_1y = _slice(250)

        # 52주 최고가/최저가 계산 / Calculate 52-week high/low
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
    # 네이버 금융에서 한국 주식 시가총액을 병렬 스크래핑 (API 제한 없음) / Scrape KR stock market caps from Naver Finance in parallel (no rate limit)
    # 매개변수: symbols(종목코드 리스트) / Parameters: symbols(ticker list)
    # 반환: {종목코드: 시가총액(원)} 딕셔너리 / Returns: {symbol: market_cap(KRW)} dictionary
    """Fetch market caps for KR stocks via Naver Finance (no rate limit)."""
    import httpx
    import re
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _get_cap(sym):
        # 개별 종목의 시가총액을 네이버 금융에서 스크래핑 / Scrape market cap for a single stock from Naver Finance
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            # 네이버 금융 종목 페이지 HTTP 요청 / HTTP request to Naver Finance stock page
            r = httpx.get(
                f"https://finance.naver.com/item/main.naver?code={sym}",
                headers=headers, timeout=8,
            )
            if r.status_code != 200:
                return sym, 0
            # HTML에서 시가총액(억 단위) 정규식 추출 / Regex extract market cap (in 억/100M units) from HTML
            m = re.search(r'시가총액\(억\)</span></th>\s*<td>([\d,]+)</td>', r.text)
            if m:
                return sym, float(m.group(1).replace(",", "")) * 1e8  # 억 → 원 단위 변환 / Convert 억 to KRW
            return sym, 0
        except Exception:
            return sym, 0

    result = {}
    # 10개 스레드로 병렬 조회 (타임아웃 25초) / Parallel fetch with 10 threads (timeout 25s)
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
    # 한국 주식 펀더멘털 조회 (2단계: 네이버 금융 PER/EPS/PBR + yfinance 시가총액) / Fetch KR stock fundamentals (Phase 2: Naver Finance PER/EPS/PBR + yfinance market cap)
    # 매개변수: symbol(종목코드) / Parameters: symbol(ticker)
    # 반환: PER/EPS/PBR/시가총액 딕셔너리 / Returns: PER/EPS/PBR/market_cap dictionary
    """Phase 2: PER/EPS/PBR from Naver Finance + market cap from yfinance."""
    import httpx
    import re

    result = {}

    # 네이버 금융 스크래핑으로 PER/EPS/PBR 조회 (빠르고 API 제한 없음) / Scrape PER/EPS/PBR from Naver Finance (fast, no rate limit)
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        # 네이버 금융 종목 페이지 HTTP 요청 / HTTP request to Naver Finance stock page
        r = httpx.get(
            f"https://finance.naver.com/item/main.naver?code={symbol}",
            headers=headers, timeout=10, follow_redirects=True,
        )
        if r.status_code == 200:
            text = r.text
            # HTML에서 PER(주가수익비율) 추출 / Extract PER (Price-to-Earnings Ratio) from HTML
            m = re.search(r'PER\(배\)</strong></th>\s*<td[^>]*>\s*([\d,.]+)', text)
            if m:
                result["pe_ratio"] = float(m.group(1).replace(",", ""))
            # HTML에서 EPS(주당순이익) 추출 / Extract EPS (Earnings Per Share) from HTML
            m = re.search(r'EPS\(원\)</strong></th>\s*<td[^>]*>\s*([\d,.]+)', text)
            if m:
                result["eps"] = float(m.group(1).replace(",", ""))
            # HTML에서 PBR(주가순자산비율) 추출 (beta 슬롯에 저장) / Extract PBR (Price-to-Book Ratio) from HTML (stored in beta slot)
            m = re.search(r'PBR\(배\)</strong></th>\s*<td[^>]*>\s*([\d,.]+)', text)
            if m:
                result["beta"] = float(m.group(1).replace(",", ""))  # PBR in beta slot
    except Exception as e:
        logger.warning(f"Naver scrape failed for {symbol}: {e}")

    # yfinance fast_info에서 시가총액 조회 / Fetch market cap from yfinance fast_info
    try:
        import yfinance as yf
        # 한국 주식은 .KS 접미사 필요 / Korean stocks require .KS suffix
        fi = yf.Ticker(f"{symbol}.KS").fast_info
        mcap = getattr(fi, 'market_cap', 0)
        if mcap:
            result["market_cap"] = mcap
    except Exception:
        pass

    return result
