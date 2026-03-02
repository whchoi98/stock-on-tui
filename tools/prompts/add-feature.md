# Prompt: 새 기능 추가

## Template
새 기능을 추가할 때 다음 절차를 따르세요:

1. **config.py 확인** — 필요한 설정/매핑이 있는지
2. **models/stock.py 확인** — 필요한 데이터 필드가 있는지
3. **services/ 확인** — 데이터 소스가 있는지, 새 서비스 함수 필요 여부
4. **컴포넌트 생성/수정** — components/ 에 위젯 구현
5. **화면 통합** — screens/ 에서 위젯 배치 및 데이터 연결
6. **CSS 추가** — styles/app.tcss 또는 DEFAULT_CSS
7. **문법 검증** — ast.parse로 모든 수정 파일 검증

## Checklist
- [ ] 추가 API 호출 최소화 (기존 데이터 활용 우선)
- [ ] `@work` 데코레이터로 비동기 실행
- [ ] 에러 시 UI가 깨지지 않도록 try/except 처리
- [ ] 색상 규칙 준수 (상승 빨강, 하락 파랑)
