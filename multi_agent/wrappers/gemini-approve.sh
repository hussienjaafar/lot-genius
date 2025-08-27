#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="python3"; command -v python >/dev/null 2>&1 && PY="python"
"$PY" "$SCRIPT_DIR/../prompt_flow.py" approve --from gemini --to claude "$@"
