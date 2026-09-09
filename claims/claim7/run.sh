#!/usr/bin/env bash
# Claim 7 - see claim.txt. Runtime <1 min (deterministic, no model needed).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PY="${PYTHON:-python3}"
cd "$ROOT"

echo "== claim 7 =="
echo "  -> rebuttal_experiments/e7_scale.py"
"$PY" "$ROOT/rebuttal_experiments/e7_scale.py"
echo "  -> rebuttal_experiments/n7b_prefilter_variants.py"
"$PY" "$ROOT/rebuttal_experiments/n7b_prefilter_variants.py"

echo
"$PY" claims/_check.py "$ROOT/claims/claim7"
