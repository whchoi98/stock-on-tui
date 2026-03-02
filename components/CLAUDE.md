# Components Layer

Textual 위젯으로 구성된 재사용 가능한 UI 컴포넌트.

## 파일별 역할
- `market_summary.py` — 시장 요약 (상승/하락, Top 종목, 거래량 Top) US/KR 분리
- `sector_bar.py` — 섹터 등락률 바 차트 US/KR 분리
- `rich_chart.py` — Sparkline 차트 + MA5/MA20 + 골든/데드크로스
- `stock_table.py` — 주식 DataTable (Symbol, Name, Price, Change, %, Cap, Vol)
- `market_card.py` — 시장 지수 카드
- `indicators.py` — 경제지표 수평 바
- `news_feed.py` — 뉴스 피드 ListView

## 규칙
- 위젯 스타일은 `DEFAULT_CSS` 또는 `styles/app.tcss`에 정의
- `update_data()` / `update_*()` 패턴으로 데이터 갱신
- 색상: 상승 `#F04452`, 하락 `#3182F6`, 강조 `#FFD700`
