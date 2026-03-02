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
