"""Thin Ollama client used by every Mission 2C real-LLM swap point.

Centralises model-id selection, decoding parameters, and prompt-call interface
so the four LLM swap points (lifter, MCPShield judge, INVARLLM extractor,
agent) all share the same plumbing.

Per dec_01KR2HNVAFP7JJN3D827W5GMQH: L_verify must be a different model/seed
than the agent. We honour this by:
  - Using `qwen2.5-coder:14b` for L_verify (structured-output coder model).
  - Using a different seed (and optionally different temperature) for the
    agent role when both run.

Model substitution per INSTALL.md: `qwen2.5-coder:14b` substitutes for the
spec'd `Qwen3.6-14B-Q4` (which does not currently exist as a public release).
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Optional  # noqa: F401  (used in chat_kwargs type hint)

import ollama


DEFAULT_MODEL = "qwen3:14b"

# Per jrn_01KR3Y2X74Z4KEWQEH0ANZ1ZSR (revised path) and chk_01KR3XV586HB0ZHRA5NR4VEZGX
# resolution: qwen3:14b (Q4_K_M, ~10 GB resident at 4096 context, 100% GPU on M4).
# Supersedes the qwen3.6:27b decision (runtime-budget infeasible at 22 GB resident
# on M4 24 GB) and the earlier qwen2.5-coder:14b substitution.
# Different seeds per role per dec_01KR2HNVAFP7JJN3D827W5GMQH.
ROLE_CONFIG = {
    "lifter":       {"model": "qwen3:14b", "seed": 42,    "temperature": 0.0},
    "mcpshield":    {"model": "qwen3:14b", "seed": 1337,  "temperature": 0.0},
    "invarllm":     {"model": "qwen3:14b", "seed": 271828, "temperature": 0.0},
    "agent":        {"model": "qwen3:14b", "seed": 314159, "temperature": 0.2},
}

# Cross-model T3 validation hook (paper revision pass): when the env var
# PG_DSL_LIFTER_MODEL is set, override the lifter's model field. Used by
# the cross-model T3 campaign on a second LLM family (llama3.1:8b) to
# verify that the T3 partition shape is invariant under lifter
# substitution. Other roles (mcpshield, invarllm, agent) are unaffected
# so the comparison isolates the lifter swap.
_LIFTER_MODEL_OVERRIDE = os.environ.get("PG_DSL_LIFTER_MODEL")
if _LIFTER_MODEL_OVERRIDE:
    ROLE_CONFIG["lifter"]["model"] = _LIFTER_MODEL_OVERRIDE


def call(role: str, prompt: str,
         system: Optional[str] = None,
         max_tokens: int = 512,
         timeout_s: float = 120.0) -> dict:
    """Send `prompt` to the model configured for `role` and return the
    structured response.

    Returns dict with keys:
      role, model, seed, temperature, prompt, system, response, latency_s,
      ok (bool), error (None on success).
    """
    cfg = ROLE_CONFIG[role]
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    # Qwen3 ships with thinking mode enabled by default. For deterministic
    # structured-output campaigns, thinking burns the token budget and
    # leaves content empty (verified empirically: 300 tokens → all in
    # `thinking` field, `content` empty). Ollama exposes a `think=False`
    # kwarg that disables thinking at the runtime layer. The user-prompt
    # `/no_think` text prefix is NOT respected by ollama — it's a UI
    # feature. Apply think=False on the qwen3 family.
    chat_kwargs: dict[str, Any] = {
        "model": cfg["model"],
        "messages": messages,
        "options": {
            "seed": cfg["seed"],
            "temperature": cfg["temperature"],
            "num_predict": max_tokens,
        },
    }
    if cfg["model"].startswith("qwen3:"):
        chat_kwargs["think"] = False
    # Llama 3.1 / Mistral / non-qwen models do not have a `think` parameter
    # in the Ollama API; passing it through silently is a no-op for those
    # backends, but we omit it explicitly to keep the wire payload minimal.

    t0 = time.time()
    try:
        resp = ollama.chat(**chat_kwargs)
        text = resp.message.content if hasattr(resp, "message") else resp["message"]["content"]
        ok = True
        err = None
    except Exception as e:  # noqa: BLE001
        text = ""
        ok = False
        err = repr(e)
    latency = time.time() - t0
    return {
        "role": role,
        "model": cfg["model"],
        "seed": cfg["seed"],
        "temperature": cfg["temperature"],
        "system": system,
        "prompt": prompt,
        "response": text,
        "latency_s": latency,
        "ok": ok,
        "error": err,
    }


def smoke_test() -> dict:
    """One-shot smoke test: ping the model with a trivial prompt."""
    return call("lifter", "Reply with the single word OK and nothing else.",
                max_tokens=5, timeout_s=30.0)
