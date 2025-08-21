#!/usr/bin/env bash
set -euo pipefail
VIOL=$(rg -n '\.\.\.' --glob '!**/*.md' --glob '!**/.git/**' --glob '!**/node_modules/**' --glob '!**/__pycache__/**' --glob '!**/.pytest_cache/**' --glob '!**/*.egg-info/**' || true)
if [[ -n "$VIOL" ]]; then
  echo "❌ Ellipses found (placeholders) in code:"
  echo "$VIOL"
  exit 1
fi
echo "✅ No placeholder ellipses found."
