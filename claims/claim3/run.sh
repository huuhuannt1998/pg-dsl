#!/usr/bin/env bash
# Claim 3 - see claim.txt. Runtime ~2 mins (deterministic, no model needed).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PY="${PYTHON:-python3}"
cd "$ROOT"

echo "== claim 3 =="
echo "  -> rebuttal_experiments/r3_invarllm_recalibrated.py"
"$PY" "$ROOT/rebuttal_experiments/r3_invarllm_recalibrated.py"

echo
"$PY" claims/_check.py "$ROOT/claims/claim3"
