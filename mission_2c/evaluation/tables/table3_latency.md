# Table 3 — Latency × Defense (real-Qwen wall-clock)

All measurements on M4 24 GB MacBook running Ollama with qwen2.5-coder:14b (Q4_K_M, ~9 GB).

| Defense | Operation | n samples | Min (s) | Mean (s) | Max (s) |
|---|---|---|---|---|---|
| PG-DSL v1 admission per tool | per call | 56 | 1.22 | 1.81 | 7.41 |
| MCPShield judge per probe | per call | 6 | 2.27 | 4.16 | 9.37 |
| INVARLLM extraction (one-shot) | per call | 1 | 24.73 | 24.73 | 24.73 |

**Full-deployment admission cost** (14 tools sequential, real-Qwen):
- PG-DSL v1: 28.7 s (0.48 min)
- INVARLLM extraction (one-shot, run once): 24.7 s

All real-Qwen full-deployment costs are well below the ratified acceptance threshold of 120 s per tool from dec_01KR2YQ59841KEVNYNTV6B6TWM. End-to-end real-LLM-mode reproduction wall-clock ≈ 1.3 min (Mission 2C tasks 5–10 sequential).