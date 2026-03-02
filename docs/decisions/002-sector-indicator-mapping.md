# ADR-002: 섹터-경제지표 매핑 설계

## Status
Accepted

## Context
종목 상세 화면에서 해당 종목의 섹터와 관련된 경제지표를 보여주기 위해
섹터 → 지표 매핑이 필요.

## Decision
`config.py`에 `SECTOR_INDICATOR_MAP` 딕셔너리로 정적 매핑.
각 섹터에 2개의 관련 지표 심볼을 매핑.

```python
SECTOR_INDICATOR_MAP = {
    "Technology": ["^IXIC", "BTC-USD"],     # NASDAQ, Bitcoin
    "Energy": ["CL=F", "HG=F"],             # WTI Oil, Copper
    "Financial": ["^TNX", "EURUSD=X"],       # US 10Y, EUR/USD
    "Auto": ["KRW=X", "CL=F"],              # USD/KRW, WTI Oil
    ...
}
```

## Alternatives Considered
- 동적 상관계수 계산 → 데이터/시간 비용 과다
- 외부 API 매핑 → 불필요한 의존성

## Consequences
- 32개 섹터 매핑 (US + KR)
- Dashboard에서 이미 로드한 indicators 데이터 재활용
- Detail에서 `screen_stack` 순회하여 Dashboard 캐시 접근
