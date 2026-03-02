# Changelog

All notable changes to Stock-on-TUI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [1.0.0] - 2026-03-02

첫 정식 릴리스. 미국 50종목 + 한국 50종목 실시간 모니터링 TUI 앱.

### Added

#### Dashboard (메인 화면)
- 경제지표 바: WTI, Gold, Silver, Copper, EUR/USD, USD/KRW, USD/JPY, USD/CNY, US 10Y, Bitcoin, Ethereum (11개)
- 시장 지수 카드: S&P 500, NASDAQ, DOW, KOSPI, KOSDAQ
- 시장 요약 위젯: US/KR 상승·하락 종목수, Top 3 상승/하락 (종목명+심볼+등락률+거래량), 거래량 Top 3
- 섹터 등락 바: US/KR 시장별 섹터 평균 등락률 막대 그래프
- 주식 테이블: US 50종목 / KR 50종목 탭 전환 (Symbol, Name, Price, Change, %, Mkt Cap, Volume)
- 뉴스 피드: Yahoo Finance, 한국경제, 매일경제 RSS 실시간 수집
- 자동 갱신: 주가 45초, 뉴스 120초 주기

#### Detail (종목 상세 화면)
- 가격 헤더: 현재가, 등락률, 거래량 + 평균 대비 배율 (색상 구분)
- 핵심 지표 카드: Market Cap, PER, EPS, Beta/PBR, Volume, Avg Volume + 지표 설명 안내
- Sparkline 차트: 1W/1M/3M/1Y 기간별 전환
- 이동평균선: MA5/MA20 계산 + 골든크로스/데드크로스 신호 표시
- 호가창: 매도 10단계 (파란색) + 매수 10단계 (빨간색)
- 투자자 동향: 개인/외국인/기관 최근 10일간 순매수·순매도 테이블
- 기간별 수익률: 1W, 1M, 3M, 1Y 수익률 계산 표시
- 관련 경제지표: 종목 섹터 기반 자동 매핑 (32개 섹터 → 경제지표)
- AI 종목 분석: `A` 키 토글, Bedrock Claude 기반 기술적 분석·투자 포인트·리스크 요인

#### Article (뉴스 AI 분석 화면)
- 뉴스 기사 본문 자동 추출
- Claude Sonnet 4.6 기반 AI 분석: 요약, 시장 영향, 투자 인사이트, 관련 종목
- 영어 기사 자동 한국어 번역 + 분석

#### Infrastructure
- `install.sh`: Amazon Linux 2023 / macOS 통합 설치 스크립트
  - OS 자동 감지, Python 3.11 설치, 가상환경 생성, 패키지 설치
  - AWS Bedrock credentials 선택적 입력 (미입력 시 AI 기능 비활성 안내)
- `run.sh`: .env 로드 → venv 활성화 → 앱 실행
- `requirements.txt`: textual, yfinance, pykrx, httpx, boto3
- `.gitignore`: 캐시, 로그, credentials, 임시 이미지 제외

#### Documentation
- `CLAUDE.md`: 프로젝트 컨텍스트 (구조, 패턴, 규칙, 명령어)
- `README.md`: 상세 기능 설명, 스크린샷, 아키텍처, 설치 가이드, 키바인딩, 트러블슈팅
- `docs/architecture.md`: 3-레이어 아키텍처, 데이터 플로우, Screen 네비게이션
- `docs/decisions/001-insight-features.md`: 인사이트 7개 기능 ADR
- `docs/decisions/002-sector-indicator-mapping.md`: 섹터-지표 매핑 ADR
- `docs/runbooks/deploy.md`: 배포/실행 가이드
- `docs/runbooks/troubleshooting.md`: 트러블슈팅 가이드
- `.claude/skills/`: code-review, refactor, release 스킬 정의
- `tools/prompts/`: 기능 추가, 디버깅 프롬프트 템플릿
- `tools/scripts/validate.sh`: 전체 프로젝트 검증 스크립트
- 전체 Python 파일 한국어/영문 이중 주석 추가 (19개 파일, 837줄)

### Data Sources
- **미국 주식**: yfinance (Yahoo Finance API)
- **한국 주식**: pykrx (KRX 데이터)
- **경제지표**: yfinance (원자재, 환율, 국채, 암호화폐)
- **뉴스**: RSS (Yahoo Finance, 한국경제, 매일경제)
- **AI 분석**: AWS Bedrock Claude Sonnet 4.6

### Tech Stack
- Python 3.11+ / Textual TUI Framework
- Async data loading with 4-wave strategy
- Rich text rendering with color-coded indicators
- CSS-based dark theme (Toss Invest inspired)
