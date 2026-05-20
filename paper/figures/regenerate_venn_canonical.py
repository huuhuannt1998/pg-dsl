"""Regenerate the T3 composition Venn diagram with the canonical 8-attack
partition (canonical PG-DSL ⊕ INVARLLM, includes Z3) for the paper.

Output: paper/figures/t3_composition_venn.png (overwrites the M2C 7-attack
version that the paper-final body needs replaced).
"""

from __future__ import annotations
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
M3B = ROOT / "mission_3b"

partition = json.loads(
    (M3B / "results" / "t3_partition_canonical.json").read_text()
)
lanes = partition["lanes"]
A_static = set(lanes["A_canonical"])
A_runtime = set(lanes["A_runtime"])
only_pg = sorted(A_static - A_runtime)
only_iv = sorted(A_runtime - A_static)
intersect = sorted(A_static & A_runtime)

fig, ax = plt.subplots(figsize=(9, 6.5))
c_pg = Circle((-1.2, 0), 2.4, alpha=0.4, color="#1f77b4",
              label="Canonical PG-DSL (admission)")
c_iv = Circle((1.2, 0), 2.4, alpha=0.4, color="#d62728",
              label="Runtime CPS-IDS")
ax.add_patch(c_pg)
ax.add_patch(c_iv)

ax.text(-2.5, 1.2, r"$A_{\text{static}} \setminus A_{\text{runtime}}$",
        ha="center", va="center", fontsize=11, fontweight="bold")
ax.text(-2.5, 0.4, "\n".join(only_pg) or "(empty)",
        ha="center", va="center", fontsize=14, fontweight="bold",
        color="#0c4a8c")
ax.text(-2.5, -0.4, "magnitude\npoisoning\n(static-only)",
        ha="center", va="center", fontsize=9, style="italic",
        color="#0c4a8c")

ax.text(2.5, 1.2, r"$A_{\text{runtime}} \setminus A_{\text{static}}$",
        ha="center", va="center", fontsize=11, fontweight="bold")
ax.text(2.5, 0.4, "\n".join(only_iv) or "(empty)",
        ha="center", va="center", fontsize=14, fontweight="bold",
        color="#a02020")
ax.text(2.5, -0.4, "stealth +\npost-admission spoof\n(runtime-only)",
        ha="center", va="center", fontsize=9, style="italic",
        color="#a02020")

ax.text(0, 1.2, "intersection",
        ha="center", va="center", fontsize=11, fontweight="bold")
ax.text(0, 0.4, "\n".join(intersect) or "(empty)",
        ha="center", va="center", fontsize=12, fontweight="bold")
ax.text(0, -0.5, "(both layers detect)",
        ha="center", va="center", fontsize=9, style="italic")

ax.set_xlim(-5, 5)
ax.set_ylim(-3.5, 3.5)
ax.set_aspect("equal")
ax.axis("off")
n_total = len(A_static | A_runtime)
ax.set_title(
    f"T3 Strict Composition (canonical pipeline) — {n_total}/8 attack coverage\n"
    f"both set differences non-empty; composed defence = "
    f"{', '.join(sorted(A_static | A_runtime))}",
    fontsize=11,
)
ax.legend(loc="lower center", framealpha=0.9, ncol=2)
fig.tight_layout()

out = HERE / "t3_composition_venn.png"
fig.savefig(out, dpi=150)
plt.close(fig)
print(f"wrote {out}")
print(f"  static_only:    {only_pg}")
print(f"  runtime_only:   {only_iv}")
print(f"  intersection:   {intersect}")
print(f"  composed total: {n_total}/8")
