"""Score the two recovery rules head to head on the items they disagree on. [T-019]

    python3 validation/score_pairs.py [--labels validation/labels.ripple-pairs.claude.txt]

WHAT THIS IS NOT. It is not a precision figure for either rule over the corpus.
The draw is the contested set only - the 4,044 prompts of 38,092 where the
released longest-candidate rule and the restricted one return different
verdicts. On the other 34,048 both rules agree and neither is distinguished.

WHAT IT IS. On a contested prompt exactly one verdict can be right, so one
human letter settles both rules at once:

  `s`  the subject's own name is written out  -> STRICT is right
  `a`  only a variant is there                -> ALIAS is right
  `n`  nothing points at the subject          -> CLEAN is right
  `d`  describable but unnamed                -> CLEAN is right, and the screen
                                                 does not claim to catch it

Counts are reweighted by stratum, because the cells were sampled at wildly
different rates - six of 2,264 in one and one of one in another - so a row from
a small cell stands for one real prompt and a row from a large one stands for
several hundred.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
RIGHT = {"s": "STRICT", "a": "ALIAS", "n": "CLEAN", "d": "CLEAN"}


def _labels(path: pathlib.Path) -> dict[str, str]:
    out = {}
    current = None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^### (\d+)", line)
        if m:
            current = m.group(1)
        m = re.match(r"^label:\s*(\S+)\s*$", line)
        if m and current:
            out[current] = m.group(1).strip().lower()
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", default=str(HERE / "labels.ripple-pairs.claude.txt"))
    ap.add_argument("--sample", default=str(HERE / "sample.ripple-pairs.json"))
    args = ap.parse_args()

    sample = json.loads(pathlib.Path(args.sample).read_text(encoding="utf-8"))
    labels = _labels(pathlib.Path(args.labels))
    assign = sample["assignment"]
    sizes = sample["stratum_sizes"]
    drawn = sample["stratum_drawn"]

    if not labels:
        print("nothing labelled yet")
        return 1

    won: collections.Counter = collections.Counter()
    raw: collections.Counter = collections.Counter()
    per_cell: dict = collections.defaultdict(collections.Counter)

    unknown: list[tuple[str, str]] = []
    for item_id, letter in labels.items():
        row = assign.get(item_id)
        if row is None:
            unknown.append((item_id, "not in this sample"))
            continue
        if letter not in RIGHT:
            # Never skip in silence. A `w` here is a labeller using the other
            # files' fifth letter on a draw that shows no recovered string, and
            # dropping it quietly would shrink the denominator without saying so.
            unknown.append((item_id, f"`{letter}` is not one of {sorted(RIGHT)}"))
            continue
        cell = row["stratum"]
        w = sizes[cell] / drawn[cell]
        truth = RIGHT[letter]
        rel_ok = row["released_verdict"] == truth
        res_ok = row["restricted_verdict"] == truth
        key = ("released" if rel_ok else "restricted" if res_ok else "neither")
        won[key] += w
        raw[key] += 1
        per_cell[cell][key] += 1

    total = sum(won.values())
    if unknown:
        print(f"{len(unknown)} label(s) not scored:")
        for item_id, why in unknown:
            print(f"  {item_id}: {why}")
        print()
    if not total:
        print("nothing scorable")
        return 1
    print(f"labelled {len(labels)} of {len(assign)} drawn "
          f"({pathlib.Path(args.labels).name})\n")
    print(f"Over the {int(round(total)):,} contested prompts, reweighted by stratum:")
    for key in ("released", "restricted", "neither"):
        print(f"  {key:12} right {won[key] / total:7.1%}   "
              f"({raw[key]} of {sum(raw.values())} rows)")
    print("\nPer cell, rows not reweighted")
    print(f"  {'cell':24}{'released':>10}{'restricted':>12}{'neither':>9}")
    for cell in sorted(per_cell):
        c = per_cell[cell]
        print(f"  {cell:24}{c['released']:>10}{c['restricted']:>12}{c['neither']:>9}")
    print("\nThe other 34,048 screened prompts are not in this draw: both rules "
          "agree on them\nand this says nothing about either one's precision there.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
