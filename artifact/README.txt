Where the artifact code actually lives
======================================

The ACSAC evaluator guide asks for a top-level artifact/ directory. This
artifact deliberately keeps its code at the repository root instead, and
this file maps one onto the other.

WHY
The camera-ready paper prints reproduction commands with repository-root
paths (Appendix F, "Reproduce every paper number"), for example

    python3 mission_3b/experiments/run_canonical_benign_fpr_qwen3.py

Moving those files under artifact/ would make the published paper's own
instructions wrong, and would break the twelve artifact URLs recorded in
metadata.toml. The paper is fixed; the repository should agree with it.
Everything else the guide asks for — install.sh, claims/, infrastructure/,
README.txt, license.txt, use.txt — is present and in the expected place.

MAP
  guide's artifact/   ->  the repository root, specifically:

    mission_1a/   claim grammar (Lark) for class C
    mission_1b/   SWaT P1+P2 digital twin and the JSON-RPC 2.0 MCP server
                  exposing the 14 canonical tools
    mission_2a/   per-tool admission: lifter, DT verifier, formal matcher,
                  T3 witness constructions
    mission_2b/   MCPShield baseline (LLM judge)
    mission_2c/   INVARLLM baseline and the real-LLM lifter (prompt v1)
    mission_2d/   real-agent harness on the official Python MCP SDK,
                  plus the 80 released agent traces
    mission_3a/   T1v numerical sweep behind Figure 1
    mission_3b/   canonical pipeline: per-tool + composition admission,
                  campaign scripts, result JSONs
    rebuttal_experiments/
                  the 19 revision-pass experiments, the pre-registration
                  registers for all 50 predictions, and every result JSON

ARTIFACT.md at the root gives the claim -> script -> result-JSON mapping.
