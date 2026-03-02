# 경제지표 데이터 서비스 모듈 / Economic indicators data service module
# yfinance를 사용하여 주요 경제지표(환율, 금리, 원자재 등)를 조회합니다
# Fetches key economic indicators (exchange rates, interest rates, commodities, etc.) using yfinance

from __future__ import annotations

import logging
import math
from datetime import datetime
from typing import List

from models.stock import EconomicIndicator
from config import INDICATORS

logger = logging.getLogger(__name__)


def fetch_indicators() -> List[EconomicIndicator]:
    # 경제지표 데이터 조회 / Fetch economic indicators data
    # 개별 심볼 다운로드 대신 일괄 다운로드 사용 (NaN 정렬 문제 방지) / Uses batch download instead of per-symbol to avoid NaN alignment issues
    # 반환: EconomicIndicator 리스트 / Returns: list of EconomicIndicator
    """Fetch economic indicators. Uses per-symbol download to avoid NaN alignment issues."""
    try:
        import yfinance as yf

        results = []
        symbols = list(INDICATORS.keys())

        # 5일치 데이터를 일괄 다운로드 (데이터 가용성 확보를 위해 더 긴 기간 사용) / Batch download 5 days of data (longer period to ensure data availability)
        df = yf.download(symbols, period="5d", group_by="ticker", threads=False, progress=False)

        for sym in symbols:
            try:
                # 설정에서 지표 이름과 단위 가져오기 / Get indicator name and unit from config
                name, unit = INDICATORS[sym]
                # 멀티 티커 DataFrame에서 개별 지표 데이터 추출 / Extract individual indicator data from multi-ticker DataFrame
                if len(symbols) > 1 and sym in df.columns.get_level_values(0):
                    sub = df[sym]
                elif len(symbols) == 1:
                    sub = df
                else:
                    continue
                if sub.empty:
                    continue

                # NaN이 아닌 마지막 종가 값들 가져오기 / Get last non-NaN close values
                closes = sub["Close"].dropna()
                if len(closes) < 1:
                    continue

                value = float(closes.iloc[-1])
                if math.isnan(value):
                    continue

                # 전일 값으로 등락 계산 / Calculate change from previous value
                prev_val = float(closes.iloc[-2]) if len(closes) > 1 else value
                if math.isnan(prev_val):
                    prev_val = value

                change = value - prev_val
                pct = (change / prev_val * 100) if prev_val else 0

                results.append(EconomicIndicator(
                    symbol=sym,
                    name=name,
                    value=value,
                    change=change,
                    change_pct=pct,
                    unit=unit,
                    last_updated=datetime.now(),
                ))
            except Exception as e:
                logger.warning(f"Failed to parse indicator {sym}: {e}")

        return results
    except Exception as e:
        logger.error(f"Failed to fetch indicators: {e}")
        return []
