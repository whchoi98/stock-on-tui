"""
주식 데이터 모델 정의 - 주식 시세, 시장 지수, 경제 지표, 종목 상세 정보 데이터클래스
Stock data model definitions - dataclasses for stock quotes, market indices, economic indicators, and stock details.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


# 개별 주식 시세 데이터 모델 / Individual stock quote data model
@dataclass
class StockQuote:
    """개별 주식의 실시간 시세 정보를 담는 데이터클래스 / Dataclass holding real-time quote info for an individual stock."""

    symbol: str              # 종목 심볼/코드 / Stock symbol/code
    name: str                # 종목명 / Stock name
    price: float             # 현재가 / Current price
    change: float = 0.0      # 가격 변동 / Price change
    change_pct: float = 0.0  # 변동률 (%) / Change percentage
    volume: int = 0          # 거래량 / Trading volume
    market: str = "US"       # 시장 구분 (US/KR) / Market identifier (US/KR)
    currency: str = "USD"    # 통화 단위 / Currency unit
    sector: str = ""         # 섹터 분류 / Sector classification
    market_cap: float = 0.0  # 시가총액 / Market capitalization
    history_7d: List[float] = field(default_factory=list)  # 최근 7일 가격 이력 / Last 7 days price history
    last_updated: Optional[datetime] = None  # 마지막 업데이트 시각 / Last updated timestamp

    @property
    def is_positive(self) -> bool:
        """변동이 양수인지 확인 / Check if change is positive."""
        return self.change >= 0

    @property
    def arrow(self) -> str:
        """상승/하락/보합 화살표 반환 / Return up/down/flat arrow indicator."""
        return "▲" if self.change > 0 else "▼" if self.change < 0 else "-"

    @property
    def formatted_price(self) -> str:
        """통화에 맞게 포맷된 가격 반환 (KRW: 소수점 없음) / Return formatted price based on currency (KRW: no decimals)."""
        if self.currency == "KRW":
            return f"{self.price:,.0f}"
        return f"{self.price:,.2f}"

    @property
    def formatted_change(self) -> str:
        """부호 포함 포맷된 변동 금액 반환 / Return formatted change amount with sign."""
        sign = "+" if self.change >= 0 else ""
        if self.currency == "KRW":
            return f"{sign}{self.change:,.0f}"
        return f"{sign}{self.change:,.2f}"

    @property
    def formatted_change_pct(self) -> str:
        """부호 포함 포맷된 변동률 반환 / Return formatted change percentage with sign."""
        sign = "+" if self.change_pct >= 0 else ""
        return f"{sign}{self.change_pct:.2f}%"

    @property
    def formatted_market_cap(self) -> str:
        """시가총액을 읽기 쉬운 단위로 포맷 (KRW: 억/조/경, USD: M/B/T) / Format market cap in readable units."""
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


# 시장 지수 데이터 모델 / Market index data model
@dataclass
class MarketIndex:
    """시장 지수 정보를 담는 데이터클래스 (예: S&P 500, KOSPI) / Dataclass for market index data (e.g., S&P 500, KOSPI)."""

    symbol: str              # 지수 심볼 / Index symbol
    name: str                # 지수명 / Index name
    value: float             # 현재 지수값 / Current index value
    change: float = 0.0      # 변동 포인트 / Change in points
    change_pct: float = 0.0  # 변동률 (%) / Change percentage
    last_updated: Optional[datetime] = None  # 마지막 업데이트 시각 / Last updated timestamp

    @property
    def is_positive(self) -> bool:
        """변동이 양수인지 확인 / Check if change is positive."""
        return self.change >= 0

    @property
    def formatted_value(self) -> str:
        """포맷된 지수값 반환 / Return formatted index value."""
        return f"{self.value:,.2f}"

    @property
    def formatted_change_pct(self) -> str:
        """부호 포함 포맷된 변동률 반환 / Return formatted change percentage with sign."""
        sign = "+" if self.change_pct >= 0 else ""
        return f"{sign}{self.change_pct:.2f}%"


# 경제 지표 데이터 모델 / Economic indicator data model
@dataclass
class EconomicIndicator:
    """경제 지표 정보를 담는 데이터클래스 (원유, 금, 환율 등) / Dataclass for economic indicator data (oil, gold, forex, etc.)."""

    symbol: str              # 지표 심볼 / Indicator symbol
    name: str                # 지표명 / Indicator name
    value: float             # 현재값 / Current value
    change: float = 0.0      # 변동값 / Change amount
    change_pct: float = 0.0  # 변동률 (%) / Change percentage
    unit: str = ""           # 단위 ($, %, W 등) / Unit ($, %, W, etc.)
    last_updated: Optional[datetime] = None  # 마지막 업데이트 시각 / Last updated timestamp

    @property
    def is_positive(self) -> bool:
        """변동이 양수인지 확인 / Check if change is positive."""
        return self.change >= 0

    @property
    def formatted_value(self) -> str:
        """단위에 맞게 포맷된 값 반환 (%: 백분율, $: 달러, W: 원) / Return formatted value based on unit type."""
        if self.unit == "%":
            return f"{self.value:.2f}%"
        elif self.unit == "$":
            return f"${self.value:,.2f}"
        elif self.unit == "W":
            return f"{self.value:,.0f}"
        return f"{self.value:,.2f}"

    @property
    def formatted_change_pct(self) -> str:
        """부호 포함 포맷된 변동률 반환 / Return formatted change percentage with sign."""
        sign = "+" if self.change_pct >= 0 else ""
        return f"{sign}{self.change_pct:.2f}%"


# 종목 상세 정보 데이터 모델 / Stock detail data model
@dataclass
class StockDetail:
    """종목 상세 정보를 담는 데이터클래스 (차트, 재무 지표, 기간별 이력 포함) / Dataclass for detailed stock info (charts, financials, historical data)."""

    symbol: str                    # 종목 심볼/코드 / Stock symbol/code
    name: str                      # 종목명 / Stock name
    market: str = "US"             # 시장 구분 (US/KR) / Market identifier (US/KR)
    currency: str = "USD"          # 통화 단위 / Currency unit
    price: float = 0.0             # 현재가 / Current price
    change: float = 0.0            # 가격 변동 / Price change
    change_pct: float = 0.0        # 변동률 (%) / Change percentage
    open_price: float = 0.0        # 시가 / Opening price
    high: float = 0.0              # 고가 / Day high
    low: float = 0.0               # 저가 / Day low
    prev_close: float = 0.0        # 전일 종가 / Previous close
    volume: int = 0                # 거래량 / Trading volume
    avg_volume: int = 0            # 평균 거래량 / Average volume
    market_cap: float = 0.0        # 시가총액 / Market capitalization
    pe_ratio: Optional[float] = None    # PER (주가수익비율) / Price-to-earnings ratio
    week52_high: float = 0.0       # 52주 최고가 / 52-week high
    week52_low: float = 0.0        # 52주 최저가 / 52-week low
    # 기간별 가격 이력 / Price history by period
    history_7d: List[float] = field(default_factory=list)    # 7일 이력 / 7-day history
    history_30d: List[float] = field(default_factory=list)   # 30일 이력 / 30-day history
    history_90d: List[float] = field(default_factory=list)   # 90일 이력 / 90-day history
    history_1y: List[float] = field(default_factory=list)    # 1년 이력 / 1-year history
    # 기간별 날짜 이력 / Date history by period
    history_dates_7d: List[str] = field(default_factory=list)
    history_dates_30d: List[str] = field(default_factory=list)
    history_dates_90d: List[str] = field(default_factory=list)
    history_dates_1y: List[str] = field(default_factory=list)
    day_change: float = 0.0        # 당일 변동 / Day change
    day_change_pct: float = 0.0    # 당일 변동률 / Day change percentage
    eps: Optional[float] = None    # 주당순이익 / Earnings per share
    dividend_yield: Optional[float] = None  # 배당수익률 / Dividend yield
    beta: Optional[float] = None   # 베타 계수 (시장 변동성 대비) / Beta coefficient (vs market volatility)
    sector: str = ""               # 섹터 분류 / Sector classification
    last_updated: Optional[datetime] = None  # 마지막 업데이트 시각 / Last updated timestamp

    @property
    def is_positive(self) -> bool:
        """변동이 양수인지 확인 / Check if change is positive."""
        return self.change >= 0

    @property
    def formatted_price(self) -> str:
        """통화에 맞게 포맷된 가격 반환 (KRW: 소수점 없음) / Return formatted price based on currency (KRW: no decimals)."""
        if self.currency == "KRW":
            return f"{self.price:,.0f}"
        return f"{self.price:,.2f}"

    @property
    def formatted_market_cap(self) -> str:
        """시가총액을 읽기 쉬운 단위로 포맷 (USD: T/B, KRW: 억) / Format market cap in readable units (USD: T/B, KRW: 억)."""
        if self.market_cap >= 1e12:
            return f"${self.market_cap / 1e12:.2f}T"
        elif self.market_cap >= 1e8:
            # 통화에 따라 B(달러) 또는 억(원) 단위 사용 / Use B (dollars) or 억 (won) based on currency
            return f"${self.market_cap / 1e8:.1f}B" if self.currency == "USD" else f"{self.market_cap / 1e8:.0f}억"
        return f"{self.market_cap:,.0f}"

    @property
    def week52_position(self) -> float:
        """52주 최저-최고 범위 내 현재 가격 위치 (0.0~1.0) / Current price position within 52-week low-high range (0.0~1.0)."""
        # 최고가와 최저가가 같으면 중간값 반환 / Return midpoint if high equals low
        if self.week52_high == self.week52_low:
            return 0.5
        return (self.price - self.week52_low) / (self.week52_high - self.week52_low)
