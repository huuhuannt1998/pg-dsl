FROM python:3.11-slim

# Mission 2C dual-mode evaluation image — supports both stub-mode (Mission 2B
# pipelines, no LLM call) and real-llm-mode (Qwen via Ollama). The Ollama
# server is expected to run on the HOST; this container connects to it via
# OLLAMA_HOST.

WORKDIR /pgdsl

# Mission 1B testbed
COPY ../mission_1b/plant/        /pgdsl/mission_1b/plant/
COPY ../mission_1b/mcp_server/   /pgdsl/mission_1b/mcp_server/
COPY ../mission_1b/agent/        /pgdsl/mission_1b/agent/
COPY ../mission_1b/attacks/      /pgdsl/mission_1b/attacks/
COPY ../mission_1b/results/      /pgdsl/mission_1b/results/

# Mission 1A grammar (locked)
COPY ../mission_1a/grammar/      /pgdsl/mission_1a/grammar/

# Mission 2A pipeline (lifter, DT verifier, matcher, admission layer)
COPY ../mission_2a/lifter/         /pgdsl/mission_2a/lifter/
COPY ../mission_2a/dt_verifier/    /pgdsl/mission_2a/dt_verifier/
COPY ../mission_2a/matcher/        /pgdsl/mission_2a/matcher/
COPY ../mission_2a/admission_layer/ /pgdsl/mission_2a/admission_layer/

# Mission 2B baselines + evaluation
COPY ../mission_2b/baselines/    /pgdsl/mission_2b/baselines/
COPY ../mission_2b/evaluation/   /pgdsl/mission_2b/evaluation/

# Mission 2C — real-LLM swap points + campaigns
COPY mission_2c/baselines/       /pgdsl/mission_2c/baselines/
COPY mission_2c/evaluation/      /pgdsl/mission_2c/evaluation/
COPY mission_2c/results/         /pgdsl/mission_2c/results/
COPY mission_2c/requirements.txt /pgdsl/

ENV PYTHONPATH=/pgdsl/mission_1b:/pgdsl/mission_2a:/pgdsl/mission_2b:/pgdsl/mission_2c:/pgdsl/mission_2c/baselines
ENV OLLAMA_HOST=host.docker.internal:11434

RUN pip install --no-cache-dir -r requirements.txt

# Default = stub-mode (fast, deterministic, ~10 s).
# Override with `MODE=real-llm` to use real Qwen via Ollama.
ENV MODE=stub

# Entry point selects mode.
COPY mission_2c/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
CMD ["/entrypoint.sh"]
