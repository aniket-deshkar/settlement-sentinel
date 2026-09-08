#!/bin/sh
set -eu

case "${SERVICE_ROLE:-api}" in
  api)
    exec uvicorn sentinel.api:app --host 0.0.0.0 --port "${PORT:-8080}"
    ;;
  policy)
    exec uvicorn sentinel.policy_agent:app --host 0.0.0.0 --port "${PORT:-8080}"
    ;;
  *)
    echo "SERVICE_ROLE must be 'api' or 'policy'" >&2
    exit 64
    ;;
esac
