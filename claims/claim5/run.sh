#!/usr/bin/env bash
# Claim 5 - see claim.txt. Runtime <1 min (deterministic, no model needed).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PY="${PYTHON:-python3}"
cd "$ROOT"

echo "== claim 5 =="
echo "  -> rebuttal_experiments/e11_mutation.py"
"$PY" "$ROOT/rebuttal_experiments/e11_mutation.py"

echo
"$PY" claims/_check.py "$ROOT/claims/claim5"
