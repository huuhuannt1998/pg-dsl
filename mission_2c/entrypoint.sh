#!/bin/bash
# Mission 2C dual-mode entrypoint.
set -e

cd /pgdsl

if [ "$MODE" = "real-llm" ]; then
    echo "==[ MISSION 2C — REAL-LLM MODE ]=="
    echo "Connecting to Ollama at $OLLAMA_HOST"
    echo "Expected wall-clock: ~5-10 minutes on M4 24 GB"
    echo
    cd /pgdsl/mission_2c
    python evaluation/run_p22_ablation.py
    python evaluation/run_real_defense_asr.py
    python evaluation/run_real_mcpshield.py
    python evaluation/run_real_invarllm_t3.py
    python evaluation/run_real_lverify_adversarial.py
    python evaluation/build_paper_tables_and_figures.py
    echo "==[ Real-LLM evaluation complete ]=="
    echo "Tables : /pgdsl/mission_2c/evaluation/tables/"
    echo "Figures: /pgdsl/mission_2c/evaluation/figures/"
else
    echo "==[ MISSION 2C — STUB MODE (Mission 2B pipelines) ]=="
    echo "Wall-clock: ~10 seconds"
    cd /pgdsl/mission_2b
    python evaluation/run_pgdsl_fpr_expanded.py
    python evaluation/run_t3_composition.py
    python evaluation/run_mcpshield_eval.py
    python evaluation/run_lverify_adversarial.py
    python evaluation/build_tables_and_figures.py
    echo "==[ Stub-mode evaluation complete ]=="
    echo "Tables : /pgdsl/mission_2b/evaluation/tables/"
    echo "Figures: /pgdsl/mission_2b/evaluation/figures/"
fi
