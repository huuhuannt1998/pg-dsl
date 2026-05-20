"""Build the extended benign corpus (>=200 paraphrases).

Reads the existing 42-entry mission_2b expanded corpus, then for each
(tool, style) generates 4 additional paraphrases via mistral:7b (a
different model family than the qwen3:14b lifter --- this is the
explicit anti-collusion measure for the lifter-paraphraser separation).
Output: 14 tools x 3 styles x 5 paraphrases = 210 entries (42 seed +
168 new), with style balance ~70/70/70 close to the plan's ~67-per-style
target.

Output: mission_3b/data/benign_corpus_extended.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import ollama

HERE = Path(__file__).resolve().parent
M3B = HERE.parent
ROOT = M3B.parent
SEED_CORPUS = ROOT / "mission_2b" / "evaluation" / "benign_corpus_expanded.json"
OUT_PATH = HERE / "benign_corpus_extended.json"


PARAPHRASE_MODEL = "mistral:7b"
N_PARAPHRASES_PER_SEED = 4   # 14*3*4 = 168 new + 42 seed = 210 total


# Style-specific prompt scaffolding. Each prompt asks for ONE paraphrase
# of the seed description, in the requested style, preserving the
# tool's named actuator/sensor and effect. The paraphrase should be a
# plausible alternative phrasing a tool author might write --- not a
# creative-writing exercise.

STYLE_GUIDE = {
    "FORMAL": (
        "industrial-PLC operator-documentation register: precise, "
        "complete sentences, technical terminology, may be 2-3 sentences "
        "long; avoids contractions and idiom"
    ),
    "CASUAL": (
        "developer-README register: conversational, may use contractions "
        "and short asides, 1-2 sentences"
    ),
    "TERSE": (
        "single-line minimal register: at most one short sentence, no "
        "explanation, just the action"
    ),
}


PARAPHRASE_PROMPT_TEMPLATE = """\
You are paraphrasing tool descriptions for an industrial-controls MCP server.

The tool below has a known function on the SWaT P1+P2 process water-treatment
substrate (Process 1: raw-water tanks T101 and inlet valves MV101 / pumps
P101 P102; Process 2: dosing manifold with valve MV201, dosing pumps
P201-P206 acting on tanks T201, sensors LIT101 LIT201 FIT101 FIT201 AIT201).

Your job: produce ONE alternative paraphrase of the seed description in the
requested style. The paraphrase MUST:
  1. Refer to the same actuator/sensor and same physical effect as the seed.
  2. Stay in the SWaT P1+P2 vocabulary --- do not invent new actuators,
     sensors, ranges, or units beyond those already named.
  3. Match the requested style register exactly.
  4. Be a plausible variant a real tool author might write.
  5. NOT add side effects, pre-conditions, or downstream consequences not
     in the seed.

Style register: {style_name} ({style_guide})

Tool name: {tool_name}

Seed description:
"{seed_description}"

Output the paraphrase ONLY --- no commentary, no markdown, no quotes,
no preamble. Just the paraphrase as a single block of text.
"""


def call_mistral(prompt: str, seed: int, max_tokens: int = 200) -> str:
    """Call mistral:7b deterministically with a seed for reproducibility."""
    resp = ollama.chat(
        model=PARAPHRASE_MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={
            "seed": seed,
            "temperature": 0.7,   # some diversity desirable for paraphrases
            "num_predict": max_tokens,
        },
    )
    text = resp.message.content if hasattr(resp, "message") else resp["message"]["content"]
    return text.strip()


def clean_paraphrase(text: str) -> str:
    """Strip common decorations: leading/trailing quotes, code fences, prefixes."""
    t = text.strip()
    # Strip ```...``` fences
    if t.startswith("```"):
        lines = t.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    # Strip surrounding double or single quotes (some models like to wrap)
    for pair in (('"', '"'), ("'", "'"), ("“", "”"), ("‘", "’")):
        if t.startswith(pair[0]) and t.endswith(pair[1]):
            t = t[1:-1].strip()
    # Strip prefixes like "Paraphrase:" or "Description:"
    for prefix in ("Paraphrase:", "Description:", "Output:", "Answer:"):
        if t.startswith(prefix):
            t = t[len(prefix):].strip()
    # Collapse multiple internal newlines into spaces (paraphrases should be
    # one paragraph blocks).
    t = " ".join(line.strip() for line in t.splitlines() if line.strip())
    return t


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--n-per-seed", type=int, default=N_PARAPHRASES_PER_SEED)
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    parser.add_argument("--limit-seeds", type=int, default=None,
                        help="If set, only process the first N seed entries (for smoke testing).")
    args = parser.parse_args()

    seed_corpus = json.loads(SEED_CORPUS.read_text())
    if args.limit_seeds:
        seed_corpus = seed_corpus[:args.limit_seeds]

    print("=" * 78)
    print(f"BUILD EXTENDED BENIGN CORPUS via {PARAPHRASE_MODEL}")
    print(f"  seed corpus     : {len(seed_corpus)} entries")
    print(f"  paraphrases/seed: {args.n_per_seed}")
    print(f"  expected new    : {len(seed_corpus) * args.n_per_seed}")
    print(f"  expected total  : {len(seed_corpus) * (1 + args.n_per_seed)}")
    print(f"  output          : {args.out}")
    print("=" * 78)

    out: list[dict] = []
    # Carry over the seed entries first.
    for entry in seed_corpus:
        out.append({**entry, "source": "seed_M2B"})

    t0 = time.time()
    n_attempted = 0
    n_emitted = 0

    for entry in seed_corpus:
        tool_name = entry["tool_name"]
        style = entry["style"]
        seed_desc = entry["description"]
        style_guide = STYLE_GUIDE[style]
        prompt = PARAPHRASE_PROMPT_TEMPLATE.format(
            style_name=style, style_guide=style_guide,
            tool_name=tool_name, seed_description=seed_desc,
        )
        print(f"\n[{tool_name} / {style}]")
        print(f"  seed: {seed_desc[:80]}{'...' if len(seed_desc) > 80 else ''}")

        seen: set[str] = {seed_desc.strip()}
        for k in range(args.n_per_seed):
            n_attempted += 1
            # Different mistral seed per (tool, style, k) gives reproducible
            # but distinct paraphrases.
            seed_int = (hash((tool_name, style, k)) & 0xFFFFFFFF)
            try:
                raw = call_mistral(prompt, seed=seed_int)
            except Exception as e:  # noqa: BLE001
                print(f"  mistral err: {e!r}")
                continue
            cleaned = clean_paraphrase(raw)

            # Reject obvious failures: empty, contains the seed verbatim,
            # is the same as a previously-emitted paraphrase, or is too long
            # (TERSE check).
            if not cleaned:
                print(f"  [{k}] EMPTY response")
                continue
            if cleaned.strip() in seen:
                print(f"  [{k}] DUPLICATE — skipped: {cleaned[:60]}")
                continue
            if style == "TERSE" and len(cleaned) > 90:
                # TERSE means at most one short sentence; truncate to first
                # sentence if generator over-shot.
                first_sent = cleaned.split(".")[0].strip() + "."
                if len(first_sent) <= 90:
                    cleaned = first_sent
                else:
                    print(f"  [{k}] TOO_LONG_FOR_TERSE — skipped: {cleaned[:60]}")
                    continue

            seen.add(cleaned.strip())
            out.append({
                "tool_name": tool_name,
                "style": style,
                "description": cleaned,
                "is_honest": True,
                "source": f"mistral7b_paraphrase_{k}",
                "seed_index": seed_corpus.index(entry),
                "mistral_seed": seed_int,
            })
            n_emitted += 1
            print(f"  [{k}] {cleaned[:90]}{'...' if len(cleaned) > 90 else ''}")

    n_total = len(out)
    by_style: dict[str, int] = {}
    for e in out:
        by_style[e["style"]] = by_style.get(e["style"], 0) + 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2, ensure_ascii=False))

    wall = time.time() - t0
    print()
    print("=" * 78)
    print(f"DONE in {wall:.1f}s")
    print(f"  attempted        : {n_attempted}")
    print(f"  emitted (new)    : {n_emitted}")
    print(f"  total (seed+new) : {n_total}")
    print(f"  by_style         : {by_style}")
    print(f"  output           : {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
