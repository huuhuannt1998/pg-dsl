"""Cross-model T3 validation: re-run the canonical pipeline (per-style benign
FPR + canonical defense ASR + T3 partition) under llama3.1:8b as the lifter,
holding everything else (matcher, DT, MCPShield/INVARLLM baselines) constant.

Mission: P3.2 of the ACSAC revision pass — extend the T3 invariance claim
from "two models in the Qwen family" (qwen2.5-coder:14b, qwen3:14b) to
"three models across two families" by adding llama3.1:8b (Meta).

Implementation: invoke each canonical-pipeline script as a subprocess with
PG_DSL_LIFTER_MODEL=llama3.1:8b in the environment. Each subprocess writes
to its usual qwen3-suffixed output path; we then mv those outputs to a
llama3-suffixed name so the qwen3 (paper-canonical) results are untouched.
The qwen_client.py override picks up the env var BEFORE the lifter loads.

Output:
  mission_3b/results/per_style_canonical_llama3.json
  mission_3b/results/defense_asr_canonical_llama3.json
  mission_3b/results/t3_partition_canonical_llama3.json
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
M3B = HERE.parent
ROOT = M3B.parent
RESULTS = M3B / "results"

# (script_path, qwen3_output_filename, llama3_output_filename)
PIPELINES = [
    (HERE / "run_canonical_per_style_qwen3.py",
     "per_style_canonical_qwen3.json",
     "per_style_canonical_llama3.json"),
    (HERE / "run_canonical_defense_asr_qwen3.py",
     "defense_asr_canonical_qwen3.json",
     "defense_asr_canonical_llama3.json"),
    (HERE / "run_canonical_t3_partition_qwen3.py",
     "t3_partition_canonical.json",
     "t3_partition_canonical_llama3.json"),
]


def _backup_qwen3_output(path: Path) -> Path | None:
    """Move the qwen3 output to a temp location so it is not clobbered."""
    if not path.exists():
        return None
    backup = path.with_suffix(path.suffix + ".qwen3-backup")
    shutil.move(str(path), str(backup))
    return backup


def _restore_qwen3_output(backup: Path | None, original: Path) -> None:
    if backup is not None:
        shutil.move(str(backup), str(original))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--model", default="llama3.1:8b",
                        help="Lifter model to use for the cross-model run")
    parser.add_argument("--skip", nargs="*", default=[],
                        choices=["per_style", "defense_asr", "t3_partition"],
                        help="Skip one or more pipelines (e.g., already run)")
    args = parser.parse_args()

    env = {**os.environ, "PG_DSL_LIFTER_MODEL": args.model}

    print("=" * 78)
    print(f"CROSS-MODEL T3 VALIDATION via {args.model}")
    print("=" * 78)
    print(f"Override env: PG_DSL_LIFTER_MODEL={args.model}")
    print(f"Pipelines: {[p[0].name for p in PIPELINES]}")
    print()

    summary: dict[str, dict] = {"model": args.model, "pipelines": {}}
    t_start = time.time()

    for script_path, qwen3_name, llama3_name in PIPELINES:
        kind = script_path.stem.replace("run_canonical_", "").replace("_qwen3", "")
        if kind in args.skip:
            print(f"[SKIP] {kind}")
            continue
        print(f"[RUN ] {script_path.name}")
        qwen3_path = RESULTS / qwen3_name
        llama3_path = RESULTS / llama3_name

        # Move the existing qwen3 output aside so the subprocess doesn't
        # clobber paper-canonical data.
        backup = _backup_qwen3_output(qwen3_path)
        try:
            t0 = time.time()
            r = subprocess.run(
                ["python3", str(script_path)],
                env=env, cwd=str(ROOT),
                capture_output=True, text=True,
            )
            elapsed = time.time() - t0
            print(f"  ran in {elapsed:.1f}s; rc={r.returncode}")
            if r.returncode != 0:
                tail = r.stdout[-1000:] + "\n--STDERR--\n" + r.stderr[-1000:]
                print(f"  ERROR — last 1000 chars of output:\n{tail}")
                summary["pipelines"][kind] = {"ok": False,
                                              "elapsed_s": elapsed,
                                              "rc": r.returncode}
                continue

            # Move the just-written qwen3-named output to llama3 name.
            if qwen3_path.exists():
                shutil.move(str(qwen3_path), str(llama3_path))
                print(f"  -> {llama3_path.name}")
                summary["pipelines"][kind] = {
                    "ok": True, "elapsed_s": elapsed,
                    "output_file": str(llama3_path),
                }
            else:
                print(f"  WARNING: subprocess did not create {qwen3_path}")
                summary["pipelines"][kind] = {"ok": False,
                                              "elapsed_s": elapsed,
                                              "error": "no output file"}
        finally:
            # Always put the qwen3-canonical file back where it belongs.
            _restore_qwen3_output(backup, qwen3_path)

    summary["wall_clock_s_total"] = time.time() - t_start

    # Stitch a small comparison summary alongside the qwen3 partition.
    qwen3_partition = RESULTS / "t3_partition_canonical.json"
    llama3_partition = RESULTS / "t3_partition_canonical_llama3.json"
    if qwen3_partition.exists() and llama3_partition.exists():
        q = json.loads(qwen3_partition.read_text()).get("lanes", {})
        l_ = json.loads(llama3_partition.read_text()).get("lanes", {})
        partition_match = {
            k: (sorted(q.get(k, [])) == sorted(l_.get(k, [])))
            for k in ("intersection", "canonical_only", "invarllm_only", "missed")
        }
        summary["partition_match"] = partition_match
        summary["qwen3_lanes"] = q
        summary["llama3_lanes"] = l_
        all_match = all(partition_match.values())
        print()
        print("Cross-model T3 partition match (qwen3 vs llama3.1):")
        for lane, match in partition_match.items():
            print(f"  {lane:<20} {'MATCH' if match else 'DIFF '}: "
                  f"qwen3={sorted(q.get(lane, []))} | llama3={sorted(l_.get(lane, []))}")
        print(f"\n{'PASS' if all_match else 'FAIL'} — partition shape "
              f"{'invariant' if all_match else 'DIVERGED'} under model substitution.")

    out = RESULTS / "cross_model_t3_summary.json"
    out.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nSummary -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
