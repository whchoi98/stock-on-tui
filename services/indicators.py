from __future__ import annotations

import logging
import math
from datetime import datetime
from typing import List

from models.stock import EconomicIndicator
from config import INDICATORS

logger = logging.getLogger(__name__)


def fetch_indicators() -> List[EconomicIndicator]:
    """Fetch economic indicators. Uses per-symbol download to avoid NaN alignment issues."""
    try:
        import yfinance as yf

        results = []
        symbols = list(INDICATORS.keys())

        # Batch download with longer period to ensure data availability
        df = yf.download(symbols, period="5d", group_by="ticker", threads=False, progress=False)

        for sym in symbols:
            try:
                name, unit = INDICATORS[sym]
                if len(symbols) > 1 and sym in df.columns.get_level_values(0):
                    sub = df[sym]
                elif len(symbols) == 1:
                    sub = df
                else:
                    continue
                if sub.empty:
                    continue

                # Get last non-NaN close values
                closes = sub["Close"].dropna()
                if len(closes) < 1:
                    continue

                value = float(closes.iloc[-1])
                if math.isnan(value):
                    continue

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
