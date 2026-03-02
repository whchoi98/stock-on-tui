#!/bin/bash
# 전체 프로젝트 검증 스크립트

echo "=== Syntax Check ==="
python3 -c "
import ast, glob
files = glob.glob('**/*.py', recursive=True)
errors = 0
for f in files:
    if '__pycache__' in f:
        continue
    try:
        ast.parse(open(f).read())
        print(f'  OK: {f}')
    except SyntaxError as e:
        print(f'  FAIL: {f}: {e}')
        errors += 1
print(f'\nTotal: {len(files)} files, {errors} errors')
"

echo ""
echo "=== Import Check ==="
python3 -c "
from screens.dashboard import DashboardScreen
from screens.detail import DetailScreen
from components.market_summary import MarketSummary
from components.sector_bar import SectorBar
from components.rich_chart import RichChart
from services.bedrock import analyze_stock, analyze_article
from config import SECTOR_INDICATOR_MAP
print('All imports OK')
"
