#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${PYTHON:=python}"
: "${A2A_HOST:=127.0.0.1}"
: "${A2A_PORT:=8001}"
: "${A2A_URL:=http://${A2A_HOST}:${A2A_PORT}}"
export A2A_HOST A2A_PORT A2A_URL
"$PYTHON" -m uvicorn sentinel.policy_agent:app --host "$A2A_HOST" --port "$A2A_PORT" &
policy_pid=$!
trap 'kill "$policy_pid" 2>/dev/null || true' EXIT INT TERM
"$PYTHON" -m uvicorn sentinel.api:app --host 127.0.0.1 --port 8000
