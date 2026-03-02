# 주식 상세 데이터 서비스 모듈 / Stock detail data service module
# 차트 데이터, 호가(오더북), 투자자별 매매동향을 조회합니다
# Fetches chart data, order book (bid/ask), and investor trading trends

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


# 차트 데이터 클래스 / Chart data class
@dataclass
class ChartData:
    prices: List[float] = field(default_factory=list)    # 종가 리스트 / Close price list
    dates: List[str] = field(default_factory=list)        # 날짜 문자열 리스트 / Date string list
    volumes: List[int] = field(default_factory=list)      # 거래량 리스트 / Volume list
    highs: List[float] = field(default_factory=list)      # 고가 리스트 / High price list
    lows: List[float] = field(default_factory=list)       # 저가 리스트 / Low price list


# 호가(오더북) 항목 클래스 / Order book entry class
@dataclass
class OrderBookEntry:
    price: float       # 호가 가격 / Bid/Ask price
    volume: int        # 호가 수량 / Bid/Ask volume
    is_bid: bool       # True=매수(bid), False=매도(ask) / True=bid(buy), False=ask(sell)


# 투자자별 매매동향 행 클래스 / Investor trading trend row class
@dataclass
class InvestorRow:
    date: str                 # 날짜 / Date
    individual: int = 0       # 개인 순매수량 / Individual net purchase volume
    foreign: int = 0          # 외국인 순매수량 / Foreign net purchase volume
    institution: int = 0      # 기관 순매수량 / Institutional net purchase volume


def fetch_chart_data(symbol: str, market: str, period: str) -> ChartData:
    # 다양한 기간의 차트 데이터 조회 / Fetch chart data for various periods
    # 매개변수: symbol(종목코드), market(시장: US/KR), period(기간: 1min/day/week/month/year)
    # Parameters: symbol(ticker), market(market: US/KR), period(period: 1min/day/week/month/year)
    # 반환: ChartData 객체 / Returns: ChartData object
    """Fetch chart data for various periods."""
    try:
        import yfinance as yf

        # 한국 주식은 .KS 접미사 추가 / Add .KS suffix for Korean stocks
        yf_sym = f"{symbol}.KS" if market == "KR" else symbol

        # 기간별 yfinance 파라미터 매핑 (조회기간, 인터벌) / Map period to yfinance parameters (query period, interval)
        period_map = {
            "1min": ("1d", "1m"),      # 1분봉: 1일치 / 1-min candles: 1 day
            "day": ("3mo", "1d"),       # 일봉: 3개월치 / Daily candles: 3 months
            "week": ("1y", "1wk"),      # 주봉: 1년치 / Weekly candles: 1 year
            "month": ("5y", "1mo"),     # 월봉: 5년치 / Monthly candles: 5 years
            "year": ("max", "3mo"),     # 분기봉: 전체 / Quarterly candles: all
        }
        yf_period, yf_interval = period_map.get(period, ("3mo", "1d"))
        # yfinance로 히스토리 데이터 조회 / Fetch history data via yfinance
        t = yf.Ticker(yf_sym)
        h = t.history(period=yf_period, interval=yf_interval)

        if h.empty:
            return ChartData()

        closes = h["Close"].dropna()
        # 기간에 따른 날짜 포맷 설정 / Set date format based on period
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
    # 호가(오더북) 데이터 시뮬레이션 조회 / Fetch simulated order book (bid/ask) data
    # 실제 호가 데이터가 아닌 현재가 기반 시뮬레이션 / Simulated from current price, not real order book data
    # 매개변수: symbol(종목코드), market(시장: US/KR) / Parameters: symbol(ticker), market(market: US/KR)
    # 반환: OrderBookEntry 리스트 (매도 10단계 + 매수 10단계) / Returns: list of OrderBookEntry (10 ask levels + 10 bid levels)
    """Fetch bid/ask data to simulate order book."""
    try:
        import yfinance as yf

        # 한국 주식은 .KS 접미사 추가 / Add .KS suffix for Korean stocks
        yf_sym = f"{symbol}.KS" if market == "KR" else symbol
        t = yf.Ticker(yf_sym)
        info = t.fast_info
        price = getattr(info, "last_price", 0) or 0

        if price <= 0:
            return []

        # 매수/매도 기준가 설정 (현재가의 ±0.1%) / Set bid/ask base prices (current price +/- 0.1%)
        bid = price * 0.999
        ask = price * 1.001

        # 시장 및 가격대에 따른 호가 단위(틱) 설정 / Set tick size based on market and price level
        is_krw = market == "KR"
        tick = 500 if is_krw and price > 50000 else 100 if is_krw else 0.01 if price < 10 else 0.05 if price < 50 else 0.10

        entries = []
        # 가격 기반 시드로 일관된 랜덤 수량 생성 / Seed random with price for consistent simulated volumes
        import random
        random.seed(int(price * 100))

        # 매도 호가 10단계 생성 (ask 위쪽) / Generate 10 ask levels (above ask price)
        for i in range(10):
            p = ask + tick * i
            vol = int(100 * random.uniform(0.3, 3.0))
            entries.append(OrderBookEntry(price=p, volume=vol, is_bid=False))

        # 매수 호가 10단계 생성 (bid 아래쪽) / Generate 10 bid levels (below bid price)
        for i in range(10):
            p = bid - tick * i
            vol = int(100 * random.uniform(0.3, 3.0))
            entries.append(OrderBookEntry(price=p, volume=vol, is_bid=True))

        return entries
    except Exception as e:
        logger.error(f"Order book error: {e}")
        return []


def fetch_investor_trends(symbol: str, market: str, days: int = 10) -> List[InvestorRow]:
    # 투자자별 매매동향 조회 (개인/외국인/기관) / Fetch investor trading trends (individual/foreign/institutional)
    # 시장에 따라 미국/한국 전용 함수 호출 / Dispatches to US or KR specific function based on market
    # 매개변수: symbol(종목코드), market(시장), days(조회 일수) / Parameters: symbol(ticker), market(market), days(number of days)
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
    # 미국 주식 투자자별 매매동향 시뮬레이션 (거래량 데이터 기반) / Simulate US stock investor trends from volume data
    # 실제 투자자별 데이터가 없어 거래량과 가격 방향으로 추정 / Estimated from volume and price direction since actual investor data unavailable
    # 매개변수: symbol(종목코드), days(조회 일수) / Parameters: symbol(ticker), days(number of days)
    """For US stocks, derive from volume data."""
    import yfinance as yf

    t = yf.Ticker(symbol)
    # 1개월 히스토리 조회 / Fetch 1-month history
    h = t.history(period="1mo")

    if h.empty:
        return []

    rows = []
    n = min(days, len(h))
    for i in range(n):
        idx = -(n - i)
        row = h.iloc[idx]
        vol = int(row.get("Volume", 0))
        # 종가-시가 차이로 매수/매도 방향 결정 / Determine buy/sell direction from close-open price difference
        change = float(row["Close"]) - float(row["Open"])
        direction = 1 if change >= 0 else -1

        # 거래량 비율로 투자자별 순매수 추정 (기관 70%, 외국인 15%, 개인 10%) / Estimate investor net purchases from volume ratios (inst 70%, foreign 15%, individual 10%)
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
    # 한국 주식 투자자별 매매동향 시뮬레이션 (거래량 데이터 기반) / Simulate KR stock investor trends from volume data
    # 한국 시장 특성을 반영한 비율 사용 (개인 60%, 외국인 30%, 기관 10%) / Uses ratios reflecting Korean market characteristics (individual 60%, foreign 30%, inst 10%)
    # 매개변수: symbol(종목코드), days(조회 일수) / Parameters: symbol(ticker), days(number of days)
    """For KR stocks, derive from volume data."""
    import yfinance as yf

    # 한국 주식은 .KS 접미사 필요 / Korean stocks require .KS suffix
    yf_sym = f"{symbol}.KS"
    t = yf.Ticker(yf_sym)
    # 1개월 히스토리 조회 / Fetch 1-month history
    h = t.history(period="1mo")

    if h.empty:
        return []

    rows = []
    n = min(days, len(h))
    for i in range(n):
        idx = -(n - i)
        row = h.iloc[idx]
        vol = int(row.get("Volume", 0))
        # 종가-시가 차이로 매수/매도 방향 결정 / Determine buy/sell direction from close-open price difference
        change = float(row["Close"]) - float(row["Open"])
        direction = 1 if change >= 0 else -1

        # 한국 시장 비율로 투자자별 순매수 추정 (개인은 반대 방향) / Estimate investor net purchases with KR market ratios (individuals trade against trend)
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
