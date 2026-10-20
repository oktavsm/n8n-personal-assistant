#!/usr/bin/env bash
# Sync n8n Workflows from Remote VPS to Local Repository
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${SCRIPT_DIR}/../.venv/bin/python3"

if [ ! -f "$PYTHON_BIN" ]; then
    PYTHON_BIN="python3"
fi

"$PYTHON_BIN" "${SCRIPT_DIR}/sync-workflows.py" "$@"
