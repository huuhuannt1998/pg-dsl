#!/usr/bin/env bash
# Claim 2 - see claim.txt. Runtime ~1 mins (needs qwen3:14b).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PY="${PYTHON:-python3}"
cd "$ROOT"

if ! command -v ollama >/dev/null 2>&1 || ! ollama list 2>/dev/null | grep -q "^qwen3:14b"; then
  echo "  qwen3:14b not available. Run ./install.sh, or see ARTIFACT.md section 3(a)." >&2
  exit 1
fi

echo "== claim 2 =="
echo "  -> mission_3b/experiments/run_canonical_defense_asr_qwen3.py"
"$PY" "$ROOT/mission_3b/experiments/run_canonical_defense_asr_qwen3.py"

echo
"$PY" claims/_check.py "$ROOT/claims/claim2"
