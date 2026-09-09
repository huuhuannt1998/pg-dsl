#!/usr/bin/env bash
# PG-DSL artifact installer (ACSAC 2026, paper #151).
#
#   ./install.sh            # deps + the required model (qwen3:14b, 9.3 GB)
#   ./install.sh --no-model # deps only; enough for the 5-minute stub-lifter path
#   ./install.sh --all-models  # + the six cross-family models (~25 GB total)
#
# Installs nothing outside pip and the local Ollama model store.
set -euo pipefail

WANT_MODEL=1
WANT_ALL=0
for a in "$@"; do
  case "$a" in
    --no-model) WANT_MODEL=0 ;;
    --all-models) WANT_ALL=1 ;;
    -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
    *) echo "unknown option: $a" >&2; exit 2 ;;
  esac
done

cd "$(dirname "$0")"
PY=${PYTHON:-python3}

echo "==> Python"
"$PY" - <<'EOF'
import sys
if sys.version_info < (3, 11):
    sys.exit(f"need Python >= 3.11, found {sys.version.split()[0]}")
print(f"    {sys.version.split()[0]} at {sys.executable}")
EOF

echo "==> Dependencies"
"$PY" -m pip install --quiet -r requirements.txt
"$PY" -c 'import numpy, matplotlib, ollama, mcp, lark; print("    numpy, matplotlib, ollama, mcp, lark OK")'

if [ "$WANT_MODEL" -eq 1 ] || [ "$WANT_ALL" -eq 1 ]; then
  echo "==> Ollama"
  if ! command -v ollama >/dev/null 2>&1; then
    echo "    ollama not found. Install it from https://ollama.com, start it, and re-run." >&2
    echo "    (Or run ./install.sh --no-model for the model-free path.)" >&2
    exit 1
  fi
  ollama list >/dev/null 2>&1 || { echo "    ollama is installed but not running; start it and re-run." >&2; exit 1; }

  models=(qwen3:14b)
  [ "$WANT_ALL" -eq 1 ] && models+=(mistral:7b llama3.1:8b gemma2:9b mistral-nemo:12b granite3.1-dense:8b phi4-mini)
  for m in "${models[@]}"; do
    if ollama list | awk '{print $1}' | grep -qx "$m"; then
      echo "    $m already present"
    else
      echo "    pulling $m"
      ollama pull "$m"
    fi
  done
fi

echo
echo "==> Smoke test (no model needed)"
"$PY" mission_2a/admission_layer/pgdsl_admission_layer.py | tail -3

echo
echo "Done. Next: see ARTIFACT.md for the 5-minute, 1-hour and full evaluation paths."
