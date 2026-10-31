#!/usr/bin/env bash
# Для переключения сети обычно нужен: sudo ./run-nexora.sh
set -euo pipefail
cd "$(dirname "$0")"
if [[ -x .venv/bin/python ]]; then
  exec .venv/bin/python -m nexora "$@"
fi
exec python3 -m nexora "$@"
