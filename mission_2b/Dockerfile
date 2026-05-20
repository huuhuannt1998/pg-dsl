FROM python:3.11-slim

# Mission 2B evaluation campaign — extends Mission 2A and 1B.
WORKDIR /pgdsl

# Substrate: Mission 1B testbed.
COPY ../mission_1b/plant/         /pgdsl/mission_1b/plant/
COPY ../mission_1b/mcp_server/    /pgdsl/mission_1b/mcp_server/
COPY ../mission_1b/agent/         /pgdsl/mission_1b/agent/
COPY ../mission_1b/attacks/       /pgdsl/mission_1b/attacks/
COPY ../mission_1b/results/       /pgdsl/mission_1b/results/

# Mission 1A grammar (locked).
COPY ../mission_1a/grammar/       /pgdsl/mission_1a/grammar/

# Mission 2A pipeline (lifter, DT verifier, matcher, admission layer).
COPY ../mission_2a/lifter/           /pgdsl/mission_2a/lifter/
COPY ../mission_2a/dt_verifier/      /pgdsl/mission_2a/dt_verifier/
COPY ../mission_2a/matcher/          /pgdsl/mission_2a/matcher/
COPY ../mission_2a/admission_layer/  /pgdsl/mission_2a/admission_layer/
COPY ../mission_2a/results/          /pgdsl/mission_2a/results/

# Mission 2B baselines + evaluation campaigns.
COPY mission_2b/baselines/          /pgdsl/mission_2b/baselines/
COPY mission_2b/evaluation/         /pgdsl/mission_2b/evaluation/
COPY mission_2b/results/            /pgdsl/mission_2b/results/
COPY mission_2b/requirements.txt    /pgdsl/

ENV PYTHONPATH=/pgdsl/mission_1b:/pgdsl/mission_2a:/pgdsl/mission_2b

RUN pip install --no-cache-dir -r requirements.txt

CMD ["bash", "-c", "cd /pgdsl/mission_2b && \
     python evaluation/run_pgdsl_fpr_expanded.py && \
     python evaluation/run_t3_composition.py && \
     python evaluation/run_mcpshield_eval.py && \
     python evaluation/run_lverify_adversarial.py && \
     python evaluation/build_tables_and_figures.py"]
