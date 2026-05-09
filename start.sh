#!/bin/bash
set -e

if [ ! -f .env ]; then
  echo ".env 파일이 없습니다. .env.example을 참고해 .env를 만들어주세요."
  exit 1
fi

set -a
. ./.env
set +a

API_HOST="${API_HOST:-0.0.0.0}"
API_PORT="${API_PORT:-8001}"
FRONTEND_HOST="${FRONTEND_HOST:-0.0.0.0}"
FRONTEND_PORT="${FRONTEND_PORT:-8002}"

uv sync
uv run uvicorn app.main:app --host "$API_HOST" --port "$API_PORT" --env-file .env &
API_PID=$!

cleanup() {
  kill "$API_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

sleep 3
uv run streamlit run frontend/ui.py \
  --server.port "$FRONTEND_PORT" \
  --server.address "$FRONTEND_HOST" \
  --server.headless true \
  --browser.gatherUsageStats false &
FRONTEND_PID=$!

echo "Backend: http://localhost:$API_PORT | Frontend: http://localhost:$FRONTEND_PORT"
wait
