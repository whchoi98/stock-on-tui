# Runbook: 트러블슈팅

## 자주 발생하는 문제

### 1. yfinance Rate Limit
**증상**: fundamentals(PER/EPS/Beta) 로드 실패, "Too Many Requests"
**해결**: 자동 retry + backoff (5s/10s/15s) 동작. 반복 실패 시 N/A 표시.

### 2. 앱 시작 시 빈 화면
**증상**: Loading... 상태에서 멈춤
**원인**: 네트워크 이슈 또는 yfinance/pykrx 장애
**해결**: `R` 키로 새로고침, 또는 네트워크 확인

### 3. KR 주식 데이터 0원 표시
**증상**: 한국 주식 가격이 0 또는 비정상
**원인**: pykrx는 거래시간 외 이전 종가만 반환
**해결**: 정상 동작 — KRX 장 마감 후에는 종가 데이터

### 4. AI 분석 버튼(`A`) 무반응
**증상**: `A` 키 눌러도 아무 변화 없음
**원인**: AWS credentials 미설정 또는 Bedrock 접근 권한 없음
**해결**:
```bash
aws configure  # credentials 설정
# Bedrock console에서 model access 활성화 확인
```

### 5. 터미널 렌더링 깨짐
**증상**: 박스, 바 차트 등이 깨져 보임
**원인**: 터미널 유니코드/색상 미지원
**해결**: 모던 터미널 사용 (iTerm2, Windows Terminal, Kitty)

## 로그 확인
```bash
cat app_errors.log
```
