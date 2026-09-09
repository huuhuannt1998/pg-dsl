#!/usr/bin/env bash
# Claim 4 - see claim.txt. Runtime ~2 mins (deterministic, no model needed).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PY="${PYTHON:-python3}"
cd "$ROOT"

echo "== claim 4 =="
echo "  -> rebuttal_experiments/r2_invarllm_benign.py"
"$PY" "$ROOT/rebuttal_experiments/r2_invarllm_benign.py"

echo
"$PY" claims/_check.py "$ROOT/claims/claim4"
