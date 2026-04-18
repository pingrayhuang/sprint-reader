#!/usr/bin/env bash
# Sprint Reader — one-click launcher
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "[setup] creating venv..."
  python3 -m venv .venv
fi
source .venv/bin/activate

echo "[setup] installing deps..."
pip install -q -r requirements.txt

if [ ! -f "data/sprint.db" ]; then
  echo "[setup] initializing DB..."
  python init_db.py
fi

echo "[run] FastAPI on http://localhost:8000"
echo "[run] open frontend: http://localhost:8000/ui/"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
