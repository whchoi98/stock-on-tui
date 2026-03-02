# Runbook: 배포 및 실행

## 로컬 실행
```bash
cd stock-on-tui
pip install -r requirements.txt
python3 app.py
```

## 의존성 설치
```bash
pip install textual yfinance pykrx httpx boto3
```

## AWS Bedrock 설정 (AI 분석 기능)
```bash
aws configure
# Region: us-east-1
# Bedrock model access 필요: us.anthropic.claude-sonnet-4-6
```

## 문법 검증
```bash
python3 -c "
import ast
files = [
    'app.py', 'config.py',
    'screens/dashboard.py', 'screens/detail.py', 'screens/article.py',
    'components/market_summary.py', 'components/sector_bar.py',
    'components/rich_chart.py', 'components/stock_table.py',
    'services/bedrock.py', 'services/us_stocks.py', 'services/kr_stocks.py',
]
for f in files:
    ast.parse(open(f).read())
    print(f'OK: {f}')
"
```

## 트러블슈팅

### 주식 데이터 안 나옴
- 인터넷 연결 확인
- yfinance 동작 테스트: `python3 -c "import yfinance as yf; print(yf.Ticker('AAPL').info.get('currentPrice'))"`

### 한국 주식 데이터 지연
- pykrx는 KRX 거래시간(평일 09:00-15:30 KST) 외 이전 종가 반환
- 테스트: `python3 -c "from pykrx import stock; print(stock.get_market_ohlcv('20240301', market='KOSPI').head())"`

### AI 분석 실패
- AWS credentials 확인: `aws sts get-caller-identity`
- Bedrock 모델 접근 확인: `aws bedrock list-foundation-models --region us-east-1 | grep claude`
