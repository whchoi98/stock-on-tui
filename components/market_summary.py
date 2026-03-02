# 시장 요약 위젯 모듈 — 상승/하락 종목 수, 탑 무버, 거래량 리더를 표시하는 컴포넌트
# Market summary widget module — displays up/down counts, top movers, and volume leaders
from __future__ import annotations

from typing import List

from rich.text import Text
from textual.widgets import Static

from models.stock import StockQuote


# 시장 요약 위젯 클래스 — US/KR 시장의 종합 요약 정보를 한눈에 보여주는 정적 위젯
# Market summary widget class — static widget showing consolidated summary info for US/KR markets
class MarketSummary(Static):
    """Market summary widget showing up/down counts, top movers, and volume leaders."""

    # 위젯 기본 CSS 스타일 정의 / Default CSS style definition for the widget
    DEFAULT_CSS = """
    MarketSummary {
        height: auto;
        min-height: 4;
        margin: 0 2;
        padding: 1 2;
        border: solid $surface-lighten-2;
    }
    """

    # 생성자: 빈 문자열로 초기화 / Constructor: initialize with empty string
    def __init__(self, **kwargs):
        super().__init__("", **kwargs)

    # 데이터 갱신 메서드: US/KR 주식 데이터를 받아 시장 요약 텍스트를 구성하고 표시
    # Data update method: receives US/KR stock data, builds and displays market summary text
    def update_data(self, us_quotes: List[StockQuote], kr_quotes: List[StockQuote]) -> None:
        text = Text()

        # ── 1행: 시장 폭 (상승/하락 종목 수 집계) / Line 1: Market breadth (up/down stock counts) ──
        us_up = sum(1 for q in us_quotes if q.change > 0)
        us_down = sum(1 for q in us_quotes if q.change < 0)
        kr_up = sum(1 for q in kr_quotes if q.change > 0)
        kr_down = sum(1 for q in kr_quotes if q.change < 0)

        # 시장 요약 헤더 라벨 출력 / Render market summary header label
        text.append(" 시장 요약  ", style="bold")
        # US 상승 종목 수 (빨간색) / US up count (red)
        text.append("US: 상승 ", style="dim")
        text.append(f"{us_up}", style="bold #F04452")
        # US 하락 종목 수 (파란색) / US down count (blue)
        text.append(" 하락 ", style="dim")
        text.append(f"{us_down}", style="bold #3182F6")
        # KR 상승 종목 수 (빨간색) / KR up count (red)
        text.append("  |  KR: 상승 ", style="dim")
        text.append(f"{kr_up}", style="bold #F04452")
        # KR 하락 종목 수 (파란색) / KR down count (blue)
        text.append(" 하락 ", style="dim")
        text.append(f"{kr_down}", style="bold #3182F6")

        # ── US 탑 무버: 등락률 기준 상위/하위 3종목 정렬 / US Top movers: sort top/bottom 3 by change % ──
        us_sorted_up = sorted(us_quotes, key=lambda q: q.change_pct, reverse=True)
        us_sorted_down = sorted(us_quotes, key=lambda q: q.change_pct)

        # US 상승 상위 3종목 출력 / Display top 3 US gainers
        text.append("\n 🇺🇸 Top▲ ", style="bold #F04452")
        for q in us_sorted_up[:3]:
            text.append(f"{q.name}({q.symbol}) ", style="bold")
            text.append(f"+{q.change_pct:.2f}% ", style="#F04452")
            # 거래량을 간략한 형식으로 표시 / Display volume in compact format
            text.append(f"[{self._fmt_vol(q.volume)}]  ", style="dim")

        # US 하락 상위 3종목 출력 / Display top 3 US losers
        text.append("  Top▼ ", style="bold #3182F6")
        for q in us_sorted_down[:3]:
            text.append(f"{q.name}({q.symbol}) ", style="bold")
            text.append(f"{q.change_pct:.2f}% ", style="#3182F6")
            text.append(f"[{self._fmt_vol(q.volume)}]  ", style="dim")

        # ── KR 탑 무버: 등락률 기준 상위/하위 3종목 정렬 / KR Top movers: sort top/bottom 3 by change % ──
        kr_sorted_up = sorted(kr_quotes, key=lambda q: q.change_pct, reverse=True)
        kr_sorted_down = sorted(kr_quotes, key=lambda q: q.change_pct)

        # KR 상승 상위 3종목 출력 / Display top 3 KR gainers
        text.append("\n 🇰🇷 Top▲ ", style="bold #F04452")
        for q in kr_sorted_up[:3]:
            text.append(f"{q.name}({q.symbol}) ", style="bold")
            text.append(f"+{q.change_pct:.2f}% ", style="#F04452")
            text.append(f"[{self._fmt_vol(q.volume)}]  ", style="dim")

        # KR 하락 상위 3종목 출력 / Display top 3 KR losers
        text.append("  Top▼ ", style="bold #3182F6")
        for q in kr_sorted_down[:3]:
            text.append(f"{q.name}({q.symbol}) ", style="bold")
            text.append(f"{q.change_pct:.2f}% ", style="#3182F6")
            text.append(f"[{self._fmt_vol(q.volume)}]  ", style="dim")

        # ── 거래량 리더: 거래량 기준 내림차순 정렬 / Volume leaders: sort descending by volume ──
        us_vol = sorted(us_quotes, key=lambda q: q.volume, reverse=True)
        kr_vol = sorted(kr_quotes, key=lambda q: q.volume, reverse=True)

        # US 거래량 상위 3종목 출력 / Display top 3 US volume leaders
        text.append("\n ⚡ 거래량 US: ", style="bold")
        for q in us_vol[:3]:
            text.append(f"{q.name}({q.symbol}) ", style="bold")
            text.append(f"{self._fmt_vol(q.volume)}  ", style="dim")

        # KR 거래량 상위 3종목 출력 / Display top 3 KR volume leaders
        text.append("  KR: ", style="bold")
        for q in kr_vol[:3]:
            text.append(f"{q.name}({q.symbol}) ", style="bold")
            text.append(f"{self._fmt_vol(q.volume)}  ", style="dim")

        # 최종 텍스트로 위젯 업데이트 / Update the widget with the final composed text
        self.update(text)

    # 거래량 포맷터: 큰 숫자를 B/M/K 단위로 축약하여 반환
    # Volume formatter: abbreviate large numbers into B/M/K units
    @staticmethod
    def _fmt_vol(v: int) -> str:
        # 10억 이상이면 B(Billion) 단위 / Use B (Billion) for values >= 1 billion
        if v >= 1e9:
            return f"{v / 1e9:.1f}B"
        # 100만 이상이면 M(Million) 단위 / Use M (Million) for values >= 1 million
        if v >= 1e6:
            return f"{v / 1e6:.1f}M"
        # 1000 이상이면 K(Thousand) 단위 / Use K (Thousand) for values >= 1 thousand
        if v >= 1e3:
            return f"{v / 1e3:.0f}K"
        # 1000 미만이면 원본 숫자 그대로 반환 / Return raw number for values < 1000
        return str(v)
