# Table 3 — Latency × Defense

All measurements taken on M4 24 GB MacBook with deterministic stubs. Real-LLM swap-in (Qwen3.6) on PI hardware will increase admission-time latencies by ~1–2 orders of magnitude per tool; runtime invariant check is unchanged (no LLM in the runtime path).

| Defense | Operation | Min | Mean | Max | Note |
|---|---|---|---|---|---|
| PG-DSL | admission decision per tool | 0.41 ms | 0.60 ms | 1.65 ms | 14 tools, 3 initial states each |
| MCPShield | judge per tool | 0.01 ms | 0.04 ms | 0.30 ms | 1 invocation per tool |
| INVARLLM | runtime check (1 trajectory) | 0.98 ms | 1.01 ms | 1.03 ms | 1801-step benign trajectory |

**Full-deployment admission cost** (14 tools sequential):
- PG-DSL: 8.4 ms
- MCPShield: 0.6 ms

**Acceptance criterion:** ≤ 120 s per tool (ratified per dec_01KR2YQ59841KEVNYNTV6B6TWM). Both stubs are 3+ orders of magnitude below the target.