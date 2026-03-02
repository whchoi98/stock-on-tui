# Skill: Refactor

## Description
Stock-on-TUI 코드 리팩터링을 수행합니다.

## Instructions
1. 리팩터링 대상 파일과 범위를 파악
2. 기존 동작을 변경하지 않으면서 코드 품질을 개선
3. 리팩터링 원칙:
   - 중복 코드 → 공통 유틸리티/메서드 추출
   - 긴 메서드 → 의미 단위로 분리
   - 하드코딩 값 → config.py로 이동
   - 타입 힌트 보강 (기존 패턴 유지: `Optional`, `List`)
4. 변경 전후 문법 검증 수행
5. 기존 위젯 ID, CSS 선택자, Binding 키는 변경 금지 (의존성 파급 큼)
6. 변경 사항 요약 보고
