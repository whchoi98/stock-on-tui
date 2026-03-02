# Skill: Release

## Description
Stock-on-TUI 릴리스 준비 작업을 수행합니다.

## Instructions
1. 전체 파일 문법 검증
   ```bash
   python3 -c "import ast; [ast.parse(open(f).read()) for f in [모든 .py 파일]]"
   ```
2. import 검증 — 모든 모듈이 정상 import 되는지 확인
   ```bash
   python3 -c "from screens.dashboard import DashboardScreen; from screens.detail import DetailScreen; print('OK')"
   ```
3. requirements.txt 의존성 확인
4. README.md 최신 기능 반영 여부 확인
5. CLAUDE.md 프로젝트 구조 최신화
6. 불필요한 디버그 코드/print문 제거
7. 릴리스 체크리스트:
   - [ ] 문법 검증 통과
   - [ ] import 검증 통과
   - [ ] README 업데이트
   - [ ] 스크린샷 최신화
   - [ ] requirements.txt 정확성
