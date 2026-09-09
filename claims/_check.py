#!/usr/bin/env python3
"""Compare a claim's result JSON against the expected values recorded beside it.

Usage:  python3 claims/_check.py <claims/claimN>

Reads <dir>/expected/reference.json, whose "assertions" list gives a dotted
path into a result JSON, the expected value, and an optional numeric
tolerance. Prints one line per assertion and exits non-zero if any fail, so a
reviewer gets a mechanical PASS/FAIL rather than having to eyeball a JSON.

Deterministic claims should match exactly. Claims routed through the LLM
lifter can differ if the Ollama version or model quantisation differs; the
tolerance field, and ARTIFACT.md section 5, say where that is expected.
"""
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def dig(obj, path):
    for part in path.split("."):
        if isinstance(obj, list):
            obj = obj[int(part)]
        else:
            obj = obj[part]
    return obj


def main(argv):
    if len(argv) != 2:
        print(__doc__.strip())
        return 2
    d = pathlib.Path(argv[1]).resolve()
    ref = json.loads((d / "expected" / "reference.json").read_text())

    print(f"  checking {d.name}: {ref['claim']}")
    cache, ok, bad = {}, 0, 0
    for a in ref["assertions"]:
        rp = a["result_json"]
        if rp not in cache:
            f = ROOT / rp
            if not f.exists():
                print(f"    MISSING  {rp} — run this claim's run.sh first")
                return 1
            cache[rp] = json.loads(f.read_text())
        try:
            got = dig(cache[rp], a["path"])
        except (KeyError, IndexError, TypeError) as e:
            print(f"    FAIL     {a['path']}: not found ({e})")
            bad += 1
            continue
        want, tol = a["expected"], a.get("tolerance")
        if tol is not None and isinstance(got, (int, float)):
            passed = abs(float(got) - float(want)) <= float(tol)
        else:
            passed = got == want
        print(f"    {'PASS' if passed else 'FAIL'}     {a['path']} = {got!r}"
              + ("" if passed else f"   expected {want!r}"))
        ok, bad = ok + passed, bad + (not passed)

    print(f"  {ok} passed, {bad} failed")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
