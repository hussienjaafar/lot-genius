#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="python3"; command -v python >/dev/null 2>&1 && PY="python"
latest=$(ls -1 "$SCRIPT_DIR/../prompts/drafts"/*.md 2>/dev/null | tail -n 1 || true)
if [ -z "${latest}" ]; then
  echo "No draft prompts found in prompts/drafts" >&2
  exit 1
fi
pid=$(basename "$latest" | sed -E 's/.*_([0-9a-f]{32})_.*/\1/')
"$PY" "$SCRIPT_DIR/../prompt_flow.py" approve --from gemini --to claude --id "$pid" "$@"
