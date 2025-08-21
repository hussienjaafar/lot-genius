#!/usr/bin/env bash
set -euo pipefail
violations=$(rg -n '\.\.\.' --glob '!**/*.md' --glob '!**/.git/**' || true)
if [[ -n "$violations" ]]; then
echo "❌ Ellipses found in source files:"
echo "$violations"
exit 1
fi
echo "✅ No ellipses found."
