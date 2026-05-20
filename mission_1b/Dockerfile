FROM python:3.11-slim

# Mission 1B testbed image. Smoke-run-ready (deterministic stub agent);
# real-LLM swap-in is documented in README.md.

WORKDIR /testbed

COPY requirements.txt /testbed/
RUN pip install --no-cache-dir -r requirements.txt

COPY plant/         /testbed/plant/
COPY mcp_server/    /testbed/mcp_server/
COPY agent/         /testbed/agent/
COPY attacks/       /testbed/attacks/
COPY experiments/   /testbed/experiments/

# Default: run the smoke ASR campaign (10 reps × benign + 3 attack classes).
# Overridden in docker-compose.yml.
CMD ["python", "experiments/run_asr.py", "--reps", "10"]
