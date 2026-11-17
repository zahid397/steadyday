#!/usr/bin/env sh
set -eu
cd "$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
export PYTHONPATH="server${PYTHONPATH:+:$PYTHONPATH}"
export STEADYDAY_MODE=local
export DATABASE_URL="${DATABASE_URL:-sqlite:///./steadyday.sqlite3}"
exec "$PYTHON_BIN" -m uvicorn steadyday.main:app --host 127.0.0.1 --port "${PORT:-8000}" --no-access-log
