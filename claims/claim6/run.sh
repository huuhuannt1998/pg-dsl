#!/usr/bin/env bash
# Claim 6 - see claim.txt. Runtime <1 min (deterministic, no model needed).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PY="${PYTHON:-python3}"
cd "$ROOT"

echo "== claim 6 =="
echo "  -> rebuttal_experiments/n5b_coverage_curve.py"
"$PY" "$ROOT/rebuttal_experiments/n5b_coverage_curve.py"

echo
"$PY" claims/_check.py "$ROOT/claims/claim6"
