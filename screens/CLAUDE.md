# Screens Layer

Textual Screen으로 구성된 앱 화면.

## 파일별 역할
- `dashboard.py` — 메인 대시보드 (지표, 지수, 시장요약, 섹터, 종목테이블, 뉴스)
- `detail.py` — 종목 상세 (차트, 호가, 투자자, 수익률, 관련지표, AI분석)
- `article.py` — 뉴스 기사 AI 분석

## 규칙
- 데이터 로딩은 `@work(exclusive=True, group="...", exit_on_error=False)` 사용
- `_last_*` 변수에 최신 데이터 캐시 (다른 화면에서 접근 가능)
- compose()에서 위젯 배치, on_mount()에서 데이터 로딩 시작
- 에러 시 status 위젯에 메시지 표시, UI 깨지지 않도록 처리
