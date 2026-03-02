# 섹터별 등락률 바 차트 모듈 — US/KR 시장 섹터별 평균 변동률을 시각적으로 표시
# Sector performance bar chart module — visually displays average change % per sector for US/KR markets
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Tuple

from rich.text import Text
from textual.widgets import Static

from models.stock import StockQuote
from config import US_STOCK_SECTORS, KR_STOCK_SECTORS


# 섹터 바 위젯 클래스 — 시장별 섹터 평균 등락률을 막대 형태로 보여주는 정적 위젯
# Sector bar widget class — static widget showing per-sector average change as bar indicators
class SectorBar(Static):
    """Sector performance bar showing average change % per sector, split by market."""

    # 위젯 기본 CSS 스타일 정의 / Default CSS style definition for the widget
    DEFAULT_CSS = """
    SectorBar {
        height: auto;
        min-height: 2;
        margin: 0 2;
        padding: 0 2;
        border: solid $surface-lighten-2;
    }
    """

    # 생성자: 빈 문자열로 초기화 / Constructor: initialize with empty string
    def __init__(self, **kwargs):
        super().__init__("", **kwargs)

    # 데이터 갱신 메서드: US/KR 주식 데이터를 받아 섹터별 평균 등락률을 계산하고 표시
    # Data update method: receives US/KR stock data, calculates and displays per-sector average changes
    def update_data(self, us_quotes: List[StockQuote], kr_quotes: List[StockQuote]) -> None:
        text = Text()

        # ── US 섹터별 평균 등락률 계산 및 표시 / Calculate and display US sector averages ──
        us_avgs = self._calc_sector_avgs(us_quotes, US_STOCK_SECTORS)
        text.append(" 🇺🇸 섹터  ", style="bold")
        # 상위 8개 섹터만 출력 / Only display top 8 sectors
        for sector, avg in us_avgs[:8]:
            self._append_sector(text, sector, avg)

        # ── KR 섹터별 평균 등락률 계산 및 표시 / Calculate and display KR sector averages ──
        kr_avgs = self._calc_sector_avgs(kr_quotes, KR_STOCK_SECTORS)
        text.append("\n 🇰🇷 섹터  ", style="bold")
        # 상위 8개 섹터만 출력 / Only display top 8 sectors
        for sector, avg in kr_avgs[:8]:
            self._append_sector(text, sector, avg)

        # 최종 텍스트로 위젯 업데이트 / Update the widget with the final composed text
        self.update(text)

    # 섹터별 평균 등락률 계산: 종목을 섹터별로 그룹핑하고 평균을 구한 뒤 절대값 기준 내림차순 정렬
    # Calculate sector averages: group stocks by sector, compute averages, sort descending by absolute value
    @staticmethod
    def _calc_sector_avgs(
        quotes: List[StockQuote], sector_map: Dict[str, str]
    ) -> List[Tuple[str, float]]:
        # 섹터별 변동률 리스트를 수집하는 딕셔너리 / Dictionary collecting change % lists per sector
        pcts: Dict[str, List[float]] = defaultdict(list)
        for q in quotes:
            # 종목 심볼로 섹터 매핑 조회 / Look up sector mapping by stock symbol
            sector = sector_map.get(q.symbol, "")
            if sector:
                pcts[sector].append(q.change_pct)

        # 섹터별 평균 계산 / Calculate average per sector
        avgs = []
        for sector, vals in pcts.items():
            avg = sum(vals) / len(vals) if vals else 0
            avgs.append((sector, avg))
        # 절대값이 큰 순서로 정렬 (변동이 큰 섹터가 먼저) / Sort by absolute value descending (most volatile first)
        avgs.sort(key=lambda x: abs(x[1]), reverse=True)
        return avgs

    # 개별 섹터 항목을 텍스트에 추가: 섹터명, 등락률, 막대 그래프 렌더링
    # Append a single sector entry to text: sector name, change %, bar graph rendering
    @staticmethod
    def _append_sector(text: Text, sector: str, avg: float) -> None:
        # 상승이면 빨간색, 하락이면 파란색 / Red for positive, blue for negative
        color = "#F04452" if avg >= 0 else "#3182F6"
        # 양수이면 + 부호 추가 / Add + sign for positive values
        sign = "+" if avg >= 0 else ""
        # 등락률에 비례하는 막대 길이 계산 (최소 1, 최대 8) / Calculate bar length proportional to change (min 1, max 8)
        bar_len = min(8, max(1, int(abs(avg) * 4)))
        bar = "█" * bar_len

        # 섹터명 출력 / Render sector name
        text.append(f"{sector} ", style="bold")
        # 등락률 퍼센트 출력 / Render change percentage
        text.append(f"{sign}{avg:.1f}% ", style=color)
        # 막대 그래프 출력 / Render bar graph
        text.append(f"{bar}  ", style=color)
