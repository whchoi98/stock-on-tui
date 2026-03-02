# Skill: Code Review

## Description
Stock-on-TUI 프로젝트의 코드 리뷰를 수행합니다.

## Instructions
1. 변경된 파일을 모두 읽고 기존 코드와의 일관성을 확인
2. 다음 체크리스트를 검증:
   - `from __future__ import annotations` 포함 여부
   - Textual `@work` 데코레이터에 `exclusive=True, group=`, `exit_on_error=False` 설정
   - 서비스 레이어 함수가 `asyncio.to_thread()`로 호출되는지
   - 색상 규칙 준수: 상승 `#F04452`, 하락 `#3182F6`
   - Exception 처리 누락 여부
   - CSS가 `DEFAULT_CSS` 또는 `styles/app.tcss`에 정의되어 있는지
3. 보안 취약점 확인 (API 키 하드코딩, 입력 검증 등)
4. 문법 검증: `python3 -c "import ast; ast.parse(open('파일').read())"`
5. 발견된 이슈를 심각도(Critical/Warning/Info)로 분류하여 보고
