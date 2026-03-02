# ADR-001: 인사이트 기능 7개 통합 구현

## Status
Accepted / Implemented

## Context
기존 앱은 주가 테이블, 차트, 호가, 투자자 동향만 제공.
시장 흐름을 한눈에 파악할 수 있는 인사이트가 부족했음.
이미 sector, history, AI(Bedrock) 등 활용 가능한 데이터/서비스가 존재.

## Decision
7개 인사이트 기능을 추가:

1. **시장 요약 + Top 상승/하락** — Dashboard, US/KR 분리, 종목명+거래량 표시
2. **섹터별 등락률 바** — Dashboard, US/KR 분리
3. **이동평균선 MA5/MA20** — Detail 차트 stats에 골든/데드크로스 표시
4. **AI 종목 분석** — Detail, Bedrock Claude, `A` 키 토글
5. **거래량 이상 감지** — Dashboard 시장 요약에 거래량 Top 포함
6. **52주 위치 + 기간별 수익률** — Detail, 1W/1M/3M/1Y 수익률
7. **경제지표 ↔ 종목 상관관계** — Detail, 섹터 기반 관련 지표 매핑

## Consequences
- 추가 API 호출 없음 (기존 데이터 활용)
- AI 분석만 Bedrock 호출 추가 (사용자 트리거, `A` 키)
- 새 파일 2개: `market_summary.py`, `sector_bar.py`
- 기존 파일 6개 수정: config, dashboard, detail, rich_chart, bedrock, app.tcss
