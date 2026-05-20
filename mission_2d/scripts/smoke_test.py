"""Mission 2D smoke test — 5-step benign run of the real-MCP agent against
the Mission 1B server. Confirms Python MCP SDK + qwen3:14b plumbing end-to-end."""
from __future__ import annotations
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
M2D = HERE.parent
ROOT = M2D.parent
M1B = ROOT / "mission_1b"
sys.path.insert(0, str(M2D))
sys.path.insert(0, str(M2D / "baselines"))

from real_mcp_agent import run_agent_sync


def main() -> int:
    server_env = {
        "SWAT_PLANT_STEP_S": "10",
        "SWAT_SNAPSHOT_PATH": str(M2D / "traces" / "smoke_snapshot.jsonl"),
    }
    out_path = M2D / "traces" / "smoke_trace.json"

    print("Running 5-step benign smoke test...", file=sys.stderr)
    trace = run_agent_sync(
        server_cwd=str(M1B),
        server_env=server_env,
        n_steps=5,
        out_path=out_path,
    )
    print(f"\nTrace written: {out_path}")
    print(f"  protocol={trace['meta'].get('protocol_version')}")
    print(f"  tools_seen={trace['meta']['n_tools']}")
    n_calls = sum(1 for h in trace['history'] if h['parsed_tool'] is not None)
    n_ok = sum(1 for h in trace['history'] if h['tool_call_ok'])
    print(f"  steps={len(trace['history'])}, tool_calls={n_calls}, ok={n_ok}")
    print(f"  per-step actions:")
    for h in trace['history']:
        act = f"{h['parsed_tool']}({h['parsed_args']})" if h['parsed_tool'] else "(no-op)"
        print(f"    step {h['step_idx']:02d} {act}")
    print(f"\nServer-side snapshot log: {server_env['SWAT_SNAPSHOT_PATH']}")
    snaps = [json.loads(l) for l in open(server_env['SWAT_SNAPSHOT_PATH'])]
    print(f"  {len(snaps)} snapshot rows")
    if snaps:
        first, last = snaps[0]['snapshot'], snaps[-1]['snapshot']
        print(f"  initial LIT101={first.get('LIT101'):.2f}, AIT201={first.get('AIT201'):.2f}")
        print(f"  final   LIT101={last.get('LIT101'):.2f}, AIT201={last.get('AIT201'):.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
