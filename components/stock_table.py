# 주식 테이블 위젯 모듈 — 종목별 시세 정보를 색상 코딩된 DataTable로 표시
# Stock table widget module — displays per-stock quotes in a color-coded DataTable
from __future__ import annotations

from typing import Dict, List, Optional

from rich.text import Text
from textual.widgets import DataTable

from models.stock import StockQuote


# 주식 테이블 클래스 — DataTable을 확장하여 종목 시세를 행 단위로 표시하는 위젯
# Stock table class — widget extending DataTable to display stock quotes row by row
class StockTable(DataTable):
    """DataTable subclass for displaying stock quotes with color coding."""

    # 위젯 기본 CSS 스타일 정의 / Default CSS style definition for the widget
    DEFAULT_CSS = """
    StockTable {
        height: 1fr;
        margin: 0 1;
    }
    """

    # 생성자: 시장 구분(US/KR)과 내부 주식 데이터 딕셔너리를 초기화
    # Constructor: initialize market type (US/KR) and internal stock data dictionary
    def __init__(self, market: str = "US", **kwargs) -> None:
        super().__init__(cursor_type="row", zebra_stripes=True, **kwargs)
        # 시장 구분 (US 또는 KR) / Market identifier (US or KR)
        self._market = market
        # 심볼을 키로 사용하는 주식 데이터 저장소 / Stock data store keyed by symbol
        self._stock_data: Dict[str, StockQuote] = {}

    # 마운트 이벤트 핸들러: 테이블 컬럼 헤더를 추가
    # Mount event handler: add table column headers
    def on_mount(self) -> None:
        self.add_columns("Symbol", "Name", "Price", "Change", "%", "Mkt Cap", "Volume", "")

    # 주식 데이터 갱신 메서드: 기존 데이터를 비우고 새 종목 리스트로 테이블 행을 다시 구성
    # Update stocks method: clear existing data and rebuild table rows with new stock list
    def update_stocks(self, stocks: List[StockQuote]) -> None:
        self.clear()
        self._stock_data.clear()

        for stock in stocks:
            # 상승이면 빨간색, 하락이면 파란색 결정 / Determine red for positive, blue for negative
            color = "#F04452" if stock.is_positive else "#3182F6"

            # 각 컬럼별 Rich Text 객체 생성 / Create Rich Text objects for each column
            symbol_text = Text(stock.symbol, style="bold")
            name_text = Text(stock.name)
            price_text = Text(stock.formatted_price, style=f"bold {color}")
            change_text = Text(stock.formatted_change, style=color)
            pct_text = Text(stock.formatted_change_pct, style=color)
            cap_text = Text(stock.formatted_market_cap, style="dim")

            # 거래량을 M/K 단위로 변환하여 축약 표시 / Convert volume to abbreviated M/K format
            if stock.volume >= 1_000_000:
                vol_str = f"{stock.volume / 1_000_000:.1f}M"
            elif stock.volume >= 1_000:
                vol_str = f"{stock.volume / 1_000:.0f}K"
            else:
                vol_str = str(stock.volume)
            vol_text = Text(vol_str, style="dim")

            # 등락 화살표 아이콘 / Up/down arrow icon
            arrow_text = Text(stock.arrow, style=f"bold {color}")

            # 테이블에 행 추가 (심볼을 키로 사용) / Add row to table (using symbol as key)
            self.add_row(
                symbol_text, name_text, price_text,
                change_text, pct_text, cap_text, vol_text, arrow_text,
                key=stock.symbol,
            )
            # 내부 데이터 저장소에 종목 데이터 보관 / Store stock data in internal data store
            self._stock_data[stock.symbol] = stock

    # 키로 주식 데이터 조회: 심볼 키에 해당하는 StockQuote 객체를 반환 (없으면 None)
    # Get stock by key: return StockQuote object for the given symbol key (None if not found)
    def get_stock_by_key(self, key: str) -> Optional[StockQuote]:
        return self._stock_data.get(key)
