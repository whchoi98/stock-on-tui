#!/bin/bash
set -e

# ============================================================
#  Stock-on-TUI Installer
#  Supports: Amazon Linux 2023, macOS
# ============================================================

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$APP_DIR/.venv"
ENV_FILE="$APP_DIR/.env"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

print_banner() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║       Stock-on-TUI Installer             ║${NC}"
    echo -e "${CYAN}║       US & KR Markets Monitor            ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
    echo ""
}

detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        if [[ "$ID" == "amzn" ]]; then
            echo "amzn"
            return
        fi
    fi
    case "$(uname -s)" in
        Darwin*) echo "mac" ;;
        Linux*)  echo "linux" ;;
        *)       echo "unknown" ;;
    esac
}

# ── Step 1: OS Detection ──
print_banner
OS=$(detect_os)
echo -e "${GREEN}[1/5] OS 감지: ${OS}${NC}"

# ── Step 2: System Dependencies ──
echo -e "${GREEN}[2/5] 시스템 의존성 설치${NC}"

case "$OS" in
    amzn)
        echo "  → Amazon Linux 2023 감지"
        sudo dnf install -y python3.11 python3.11-pip python3.11-devel gcc 2>/dev/null || \
        sudo dnf install -y python3 python3-pip python3-devel gcc 2>/dev/null
        PYTHON=$(command -v python3.11 || command -v python3)
        ;;
    mac)
        echo "  → macOS 감지"
        if ! command -v brew &>/dev/null; then
            echo -e "${YELLOW}  Homebrew가 필요합니다. 설치합니다...${NC}"
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        if ! command -v python3 &>/dev/null; then
            echo "  → Python 3 설치"
            brew install python@3.11
        fi
        PYTHON=$(command -v python3)
        ;;
    *)
        echo -e "${RED}지원하지 않는 OS입니다. Amazon Linux 2023 또는 macOS가 필요합니다.${NC}"
        exit 1
        ;;
esac

PY_VER=$($PYTHON --version 2>&1)
echo -e "  → Python: ${PY_VER}"

# ── Step 3: Virtual Environment + Dependencies ──
echo -e "${GREEN}[3/5] 가상환경 생성 및 패키지 설치${NC}"

if [[ -d "$VENV_DIR" ]]; then
    echo -e "${YELLOW}  기존 가상환경 발견 — 재사용합니다.${NC}"
else
    $PYTHON -m venv "$VENV_DIR"
    echo "  → 가상환경 생성: $VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
pip install --upgrade pip -q
pip install -r "$APP_DIR/requirements.txt" -q
echo "  → 패키지 설치 완료"

# ── Step 4: AWS Bedrock Configuration ──
echo ""
echo -e "${GREEN}[4/5] AWS Bedrock 설정 (AI 분석 기능)${NC}"
echo ""
echo -e "  Bedrock AI 기능을 사용하면 다음을 이용할 수 있습니다:"
echo -e "    - 뉴스 기사 AI 분석 및 영한 번역"
echo -e "    - AI 종목 분석 (기술적 분석/투자 포인트/리스크)"
echo ""
echo -e "${YELLOW}  AWS credentials를 입력하세요.${NC}"
echo -e "  (건너뛰려면 Enter를 누르세요)${NC}"
echo ""

read -rp "  AWS Access Key ID: " AWS_AK
read -rp "  AWS Secret Access Key: " AWS_SK
read -rp "  Bedrock Region [us-east-1]: " AWS_REGION
AWS_REGION=${AWS_REGION:-us-east-1}

BEDROCK_CONFIGURED=false

if [[ -n "$AWS_AK" && -n "$AWS_SK" ]]; then
    # Write .env file
    cat > "$ENV_FILE" <<ENVEOF
AWS_ACCESS_KEY_ID=${AWS_AK}
AWS_SECRET_ACCESS_KEY=${AWS_SK}
AWS_DEFAULT_REGION=${AWS_REGION}
BEDROCK_REGION=${AWS_REGION}
ENVEOF
    chmod 600 "$ENV_FILE"
    BEDROCK_CONFIGURED=true
    echo ""
    echo -e "  ${GREEN}✓ Bedrock 설정 완료 (.env 저장됨)${NC}"
else
    # Empty .env
    cat > "$ENV_FILE" <<ENVEOF
# AWS Bedrock not configured
# To enable AI features, fill in the following and restart:
# AWS_ACCESS_KEY_ID=
# AWS_SECRET_ACCESS_KEY=
# AWS_DEFAULT_REGION=us-east-1
# BEDROCK_REGION=us-east-1
ENVEOF
    echo ""
    echo -e "  ${YELLOW}⚠ Bedrock 미설정 — AI 기능이 비활성화됩니다.${NC}"
    echo -e "  ${YELLOW}  - 뉴스 기사 AI 분석 / 영한 번역이 제공되지 않습니다.${NC}"
    echo -e "  ${YELLOW}  - AI 종목 분석 기능이 제공되지 않습니다.${NC}"
    echo -e "  ${YELLOW}  (나중에 .env 파일을 수정하거나 install.sh를 재실행하세요)${NC}"
fi

# ── Step 5: Create run script ──
echo ""
echo -e "${GREEN}[5/5] 실행 스크립트 생성${NC}"

cat > "$APP_DIR/run.sh" <<'RUNEOF'
#!/bin/bash
APP_DIR="$(cd "$(dirname "$0")" && pwd)"

# Load .env if exists
if [[ -f "$APP_DIR/.env" ]]; then
    set -a
    source "$APP_DIR/.env"
    set +a
fi

# Activate venv
source "$APP_DIR/.venv/bin/activate"

# Run app
cd "$APP_DIR"
python3 app.py "$@"
RUNEOF
chmod +x "$APP_DIR/run.sh"

# ── Done ──
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║          설치 완료!                       ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
echo ""
echo -e "  실행: ${GREEN}./run.sh${NC}"
echo ""
if [[ "$BEDROCK_CONFIGURED" == "false" ]]; then
    echo -e "  ${YELLOW}⚠ AI 기능 비활성 상태${NC}"
    echo -e "  ${YELLOW}  Bedrock 설정: .env 파일 수정 후 ./run.sh 재실행${NC}"
    echo ""
fi
echo -e "  단축키: Q(종료) R(새로고침) Tab(섹션이동) A(AI분석)"
echo ""
