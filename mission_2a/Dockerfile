FROM python:3.11-slim

# Mission 2A PG-DSL admission-control pipeline + Mission 1B testbed.
# Layered: Mission 1B's plant + MCP server form the substrate; Mission 2A's
# lifter + DT verifier + matcher + admission layer sit on top.

WORKDIR /pgdsl

# Mission 1B testbed (plant + MCP server + agent stub + attack constructions).
COPY ../mission_1b/plant/         /pgdsl/mission_1b/plant/
COPY ../mission_1b/mcp_server/    /pgdsl/mission_1b/mcp_server/
COPY ../mission_1b/agent/         /pgdsl/mission_1b/agent/
COPY ../mission_1b/attacks/       /pgdsl/mission_1b/attacks/
COPY ../mission_1b/experiments/   /pgdsl/mission_1b/experiments/
ENV PYTHONPATH=/pgdsl/mission_1b:/pgdsl/mission_2a

# Mission 1A grammar (read-only — locked).
COPY ../mission_1a/grammar/       /pgdsl/mission_1a/grammar/

# Mission 2A pipeline.
COPY mission_2a/lifter/           /pgdsl/mission_2a/lifter/
COPY mission_2a/dt_verifier/      /pgdsl/mission_2a/dt_verifier/
COPY mission_2a/matcher/          /pgdsl/mission_2a/matcher/
COPY mission_2a/admission_layer/  /pgdsl/mission_2a/admission_layer/
COPY mission_2a/witnesses/        /pgdsl/mission_2a/witnesses/
COPY mission_2a/experiments/      /pgdsl/mission_2a/experiments/
COPY mission_2a/requirements.txt  /pgdsl/

RUN pip install --no-cache-dir -r requirements.txt

# Default: run the full PG-DSL evaluation campaign.
CMD ["bash", "-c", "cd /pgdsl/mission_2a && \
     python experiments/run_defense_asr.py && \
     python experiments/run_benign_fpr.py"]
