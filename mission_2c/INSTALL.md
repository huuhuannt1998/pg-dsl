# Mission 2C — Install Verification

**Mission:** mis_01KR3GKV2ESRM4FR43W3VRG0MA.
**Hardware:** M4 24 GB MacBook (arm64).
**Date last updated:** 2026-05-08 (post-`jrn_01KR3Y2X74Z4KEWQEH0ANZ1ZSR`).
**Authoritative model:** [`qwen3:14b`](#) per brain unblock instructions following
`chk_01KR3XV586HB0ZHRA5NR4VEZGX` resolution.

---

## Verified state (qwen3:14b — paper-canonical)

| Component | Status | Path / version |
|---|---|---|
| Ollama runtime | RUNNING | `/usr/local/bin/ollama`, API at `http://localhost:11434/v1` |
| **Qwen model (canonical)** | PULLED | **`qwen3:14b`** (Q4_K_M, 9.3 GB on disk, 10 GB resident @ 4096 ctx) |
| Qwen3 thinking-mode | DISABLED at API level | `ollama.chat(..., think=False)` in `qwen_client.call()` |
| claw-code-local source | CLONED | `/Users/huanbui/Desktop/agenttrace/claw-code-local/` |
| Disk free | OK | 256 GiB available |

### Runtime verification (paper provenance)

```
$ ollama ps
NAME         ID              SIZE     PROCESSOR    CONTEXT    UNTIL
qwen3:14b    bdbd181c33f2    10 GB    100% GPU     4096       4 minutes from now
```

Saved verbatim to [`results/ollama_ps_qwen3.txt`](results/ollama_ps_qwen3.txt).

### Smoke-lift wall-clock measurements

| Run | Wall-clock | Notes |
|---|---|---|
| 1st (cold prompt-eval) | 16.21 s | first call after model load; prompt-eval overhead |
| 2nd (steady-state) | 2.39 s | model warm, prompt cache reused |
| 3rd | 1.03 s | |
| 4th | 1.02 s | |

Steady-state ≤ 15 s threshold cleared by ~10×.

## Decision history

The Mission 1B spec referenced "Qwen3.6-14B-Q4". Verified empirically:

1. **Phantom**: Qwen3.6 family does not include a 14B variant. Released sizes are
   27B (dense) and 35B-A3B (MoE).

2. **Phase 1 substitution**: `qwen2.5-coder:14b` (9 GB on disk, ~12 GB resident).
   Worked at 1–7 s/inference. Mission 2C empirical numbers reported initially
   against this. Documented silently in INSTALL.md — process-correction recorded
   in `jrn_01KR3TZJWE5ZAEH4JYYGDYR4SK`.

3. **Brain decision** (`dec_01KR3TYT9JHYH1H0W2700YJN5Q`): `qwen3.6:27b` (Q4_K_M).
   Brain computed headroom from disk size (17 GB → ~7 GB headroom claim). Verified
   empirically: actual resident footprint is **22 GB at 4096 context**, leaving
   ~2 GB on M4 24 GB. Macos swaps; 1-token inference doesn't return within 60 s.
   Decision technically unworkable. Filed `chk_01KR3XV586HB0ZHRA5NR4VEZGX`
   (BLOCKING DECISION).

4. **Brain unblock** (`jrn_01KR3Y2X74Z4KEWQEH0ANZ1ZSR`): try `qwen3:14b` (dense
   Qwen3 family, closest available to phantom Qwen3.6-14B). Bounded verification
   sequence with explicit pass criteria.

5. **Verification PASS** (this document): `qwen3:14b` at 10 GB resident, 100% GPU,
   1–2.4 s steady-state per lift, valid grammar output. Adopted as paper-canonical.

6. **Process corrections recorded**:
   - Future model decisions: include `ollama ps` runtime footprint at target
     context size, NOT just on-disk byte count.
   - Future executor model substitutions: file CLARIFICATION checkpoint, not
     silent INSTALL.md update.

## Known runtime issue: Qwen3 thinking mode

Qwen3 ships with thinking mode enabled by default. The Ollama Python client
returns the reasoning trace in `response.message.thinking` and the answer in
`response.message.content`. With finite `num_predict`, all tokens go to thinking
and `content` ends up empty.

The `/no_think` text prefix Qwen3 supports (in conversational use) is NOT
respected by the `ollama.chat` API. The correct programmatic toggle is the
`think=False` keyword to `ollama.chat()`. This is applied in
`qwen_client.call()` for any role whose model starts with `qwen3:`.

Without `think=False`: 30+ s wall-clock, empty `content`, full `thinking`.
With `think=False`: 1–2 s wall-clock, populated `content`, empty `thinking`.

Documented in code comment at `mission_2c/baselines/qwen_client.py:call()`.

## Reproduction quickstart

```bash
ollama pull qwen3:14b   # 9.3 GB
ollama list | grep qwen3
# expected: qwen3:14b   ...   9.3 GB

cd mission_2c
pip install -r requirements.txt
python evaluation/run_p22_ablation.py
python evaluation/run_real_defense_asr.py
python evaluation/run_real_mcpshield.py
python evaluation/run_real_invarllm_t3.py
python evaluation/run_real_lverify_adversarial.py
python evaluation/build_paper_tables_and_figures.py
```

All campaign drivers reference the model via `mission_2c/baselines/qwen_client.py`'s
`ROLE_CONFIG`. Changing the model in one place propagates to all four LLM
swap points (lifter, MCPShield judge, INVARLLM extractor, agent skeleton).

## Smoke test

After the model is pulled, verify with:

```bash
python3 -c "
import sys; sys.path.insert(0, 'baselines'); sys.path.insert(0, '../mission_1b')
from real_lifter import RealLifter
from mcp_server import make_tools
from plant import SwatP1P2Plant
plant = SwatP1P2Plant()
tool = next(t for t in make_tools(plant) if t.name=='read_chemical_AIT201')
print(RealLifter('v1').lift(tool.name, tool.description).phi)
"
```

Expected output: `sensor(AIT201) reads nominal`. Steady-state wall-clock ≤ 5 s.

## What's superseded

Files under `superseded/` were generated against `qwen2.5-coder:14b` and are
kept solely for provenance:

```
superseded/
├── real_pgdsl_fpr_canonical_v0.json, _v1.json
├── real_pgdsl_fpr_expanded_v0.json, _v1.json
├── p22_ablation.json
├── real_defense_asr.json
├── real_mcpshield_eval.json
├── real_invarllm_t3.json
├── real_lverify_adversarial.json
├── invarllm_extraction_real_qwen.json
├── tables_qwen2.5coder/
└── figures_qwen2.5coder/
```

Do NOT cite numbers from these files. The paper's Evaluation section uses the
qwen3:14b reruns under `mission_2c/results/*_qwen3.json` and
`mission_2c/evaluation/`.

## claw-code-local note

For Mission 2D's real-agent campaign (per `jrn_01KR3TK3MCFKXMEQD4HDEVAQ9X`),
the agent harness MUST be `claw-code-local` (the cloned Rust workspace at
`/Users/huanbui/Desktop/agenttrace/claw-code-local/`). Custom Ollama wrappers
in the agent role are NOT acceptable for the Threat-Model section's empirical
claim. See `mission_2d/INSTALL.md` for that integration.
