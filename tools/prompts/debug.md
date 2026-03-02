# Prompt: 디버깅

## Template
버그를 진단할 때 다음 절차를 따르세요:

1. **에러 로그 확인**: `cat app_errors.log`
2. **문법 검증**: 해당 파일 `ast.parse()` 수행
3. **import 체인 추적**: 에러 파일의 import를 하나씩 검증
4. **데이터 흐름 추적**:
   - services/ → models/ → screens/ → components/ 순서로 확인
   - `_last_*` 캐시 변수에 데이터가 채워지는지 확인
5. **위젯 ID 확인**: `query_one("#id")` 에서 ID가 compose()에 존재하는지
6. **Work Group 충돌**: 같은 group에 여러 worker가 동시 실행되는지

## Common Issues
- `NoMatches` → compose()에 해당 위젯 ID 없음
- `AttributeError` → 데이터 로드 전 접근
- `ConnectionError` → 네트워크 또는 API rate limit
