# 경제지표 바 위젯 모듈 — 주요 경제지표(금리, 환율, 원자재 등)를 수평 한 줄로 표시
# Economic indicator bar widget module — displays key economic indicators (rates, FX, commodities, etc.) in a single horizontal line
from __future__ import annotations

from typing import List

from rich.text import Text
from textual.widgets import Static

from models.stock import EconomicIndicator


# 경제지표 바 클래스 — 경제지표 목록을 파이프(|) 구분자로 나열하여 보여주는 정적 위젯
# Indicator bar class — static widget displaying economic indicators separated by pipe (|) delimiters
class IndicatorBar(Static):
    """Single-line scrollable economic indicators display."""

    # 위젯 기본 CSS 스타일 정의 / Default CSS style definition for the widget
    DEFAULT_CSS = """
    IndicatorBar {
        height: 3;
        padding: 0 2;
        margin: 0 2;
        border: solid $surface-lighten-2;
        content-align: left middle;
    }
    """

    # 생성자: 불필요한 'count' 키워드 인자를 제거하고 초기화
    # Constructor: remove unnecessary 'count' kwarg and initialize
    def __init__(self, **kwargs) -> None:
        # 외부에서 전달될 수 있는 count 인자를 안전하게 제거 / Safely remove count arg that may be passed externally
        kwargs.pop("count", None)
        super().__init__(**kwargs)

    # 경제지표 갱신 메서드: 지표 리스트를 받아 이름, 값, 등락 화살표, 변동률을 텍스트로 구성
    # Update indicators method: receives indicator list and builds text with name, value, arrow, change %
    def update_indicators(self, indicators: List[EconomicIndicator]) -> None:
        text = Text()
        for i, ind in enumerate(indicators):
            # 첫 번째 항목이 아니면 구분자 추가 / Add delimiter if not the first item
            if i > 0:
                text.append("  |  ", style="dim")
            # 상승이면 빨간색, 하락이면 파란색 / Red for positive, blue for negative
            color = "#F04452" if ind.is_positive else "#3182F6"
            # 등락 방향 화살표 결정 / Determine direction arrow
            arrow = "▲" if ind.change > 0 else "▼" if ind.change < 0 else "-"
            # 지표 이름 (볼드) / Indicator name (bold)
            text.append(f"{ind.name} ", style="bold")
            # 지표 현재값 (등락 색상 적용) / Indicator current value (with change color)
            text.append(f"{ind.formatted_value} ", style=f"{color}")
            # 등락 화살표와 변동률 (흐리게 처리) / Direction arrow and change % (dimmed)
            text.append(f"{arrow}{ind.formatted_change_pct}", style=f"dim {color}")
        # 위젯 텍스트 업데이트 / Update widget text
        self.update(text)
