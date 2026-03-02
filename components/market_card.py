# 시장 지수 카드 위젯 모듈 — 개별 시장 지수(예: S&P 500, KOSPI)의 현재값과 변동률을 카드 형태로 표시
# Market index card widget module — displays individual market index (e.g., S&P 500, KOSPI) value and change as a card
from __future__ import annotations

from rich.text import Text
from textual.widgets import Static

from models.stock import MarketIndex


# 시장 지수 카드 클래스 — 단일 시장 지수의 이름, 현재가, 등락률을 카드 레이아웃으로 보여주는 위젯
# Market index card class — widget showing a single market index's name, current value, and change in a card layout
class MarketCard(Static):
    """A card widget displaying a market index value with change."""

    # 위젯 기본 CSS 스타일 정의 / Default CSS style definition for the widget
    DEFAULT_CSS = """
    MarketCard {
        width: 1fr;
        min-width: 16;
        height: 3;
        padding: 0 1;
        margin: 0 1;
        border: solid $surface-lighten-2;
        content-align: center middle;
    }
    """

    # 데이터 갱신 메서드: 시장 지수 데이터를 받아 카드 내용을 업데이트
    # Data update method: receives market index data and updates card content
    def update_data(self, index: MarketIndex) -> None:
        # 등락 방향 화살표 결정: 상승 ▲, 하락 ▼, 변동 없음 - / Determine direction arrow: up ▲, down ▼, unchanged -
        arrow = "▲" if index.change > 0 else "▼" if index.change < 0 else "-"
        # 상승이면 빨간색, 하락이면 파란색 / Red for positive, blue for negative
        color = "#F04452" if index.is_positive else "#3182F6"

        # Rich Text로 카드 내용 구성: 지수명, 현재값, 등락률 / Build card content with Rich Text: index name, value, change %
        text = Text()
        # 지수 이름 (볼드) / Index name (bold)
        text.append(f"{index.name} ", style="bold")
        # 현재 지수 값 (등락 색상 적용) / Current index value (with change color)
        text.append(f"{index.formatted_value} ", style=f"bold {color}")
        # 등락 화살표와 변동률 / Direction arrow and change percentage
        text.append(f"{arrow}{index.formatted_change_pct}", style=color)

        # 위젯 텍스트 업데이트 / Update widget text
        self.update(text)
        # 기존 positive/negative CSS 클래스 제거 후 현재 상태에 맞게 재적용
        # Remove existing positive/negative CSS classes and re-apply based on current state
        self.remove_class("positive", "negative")
        self.add_class("positive" if index.is_positive else "negative")
