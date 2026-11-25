"""Draw the blind human subset, weighted towards the verdict that carries precision.

    python3 validation/sample_human.py              # both corpora
    python3 validation/sample_human.py --adapter ripple

WHY THE FIRST DRAW WAS REPLACED, 2026-11-24. The original 25-item subsets were a
random slice of the already-labelled items, so they inherited the stratum
proportions of the big draw: mostly CLEAN and ALIAS, and only FOUR items the
matcher had called STRICT on MQuAKE.

A false positive can only appear in an item the matcher called STRICT. So the
headline claim - the strict rule has not been seen to be wrong - would have got
an agreement rate built on four items, while twenty-one items measured agreement
on recall, which nothing in the paper leans on. The labelling hour was the same
either way. This draw spends it on the number that is actually published.

WHAT IS BLIND ABOUT IT. The file carries the item exactly as the first labeller
saw it and no verdict, so a second labeller cannot agree with a decision they
were shown. The verdicts stay in `sample*.json`, and `score.py` rejoins them.

The blocks are copied verbatim out of the first pass's file rather than
re-rendered, so the two labellers are answering about identical text. A
difference in rendering would show up as a difference in judgement.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import random
import re

HERE = pathlib.Path(__file__).resolve().parent
SEED = 20261124
# STRICT first and heaviest: it is the rule every published rate is quoted on.
PLAN = {"STRICT": 15, "ALIAS": 5, "CLEAN": 5}

CORPORA = {
    "mquake": {"sample": "sample.json", "source": "labels.claude.txt",
               "out": "labels.human.txt"},
    "ripple": {"sample": "sample.ripple.json", "source": "labels.ripple.claude.txt",
               "out": "labels.ripple.human.txt"},
}

# The alias draw, added after the first one. Weighting the subsets above towards
# STRICT left five ALIAS items across three RippleEdits subsets, so the alias
# rule came out of that pass still resting on one labeller. These sets buy it a
# second, and they draw from where its published figure actually comes from: the
# MQuAKE HELD-OUT set, which is where the 90.2% is measured, and RippleEdits'
# alias stratum. Items already answered by the second labeller are excluded, so
# this adds evidence rather than re-asking.
#
# THE MQUAKE HALF OF THIS DRAW DOES NOT DO WHAT THE PARAGRAPH ABOVE SAYS, AND
# THE FILE IT PRODUCED IS A TEST-RETEST RATHER THAN A SECOND LABELLER.
# `source` is the file items are drawn from and blanked. For ripple that is
# `labels.ripple.claude.txt`, the MODEL's pass, so blanking it and asking the
# human buys a second labeller. For mquake it is `labels.holdout.txt`, which is
# the HUMAN's own first pass - there is no model pass on the held-out set, so a
# second labeller was never reachable this way. The draw re-asked the same
# person, who changed 5 of 10, every change in the same direction. That is a
# useful measurement and it is not the one the draw claimed. See README,
# "The MQuAKE half did not buy a second labeller".
#
# `exclude` was also wrong here and is now None: it pointed at
# `labels.human.txt`, the human pass over `sample.json`, a DIFFERENT sample
# whose item ids collide with the holdout's. It excluded ten arbitrary items by
# id collision rather than ten already-answered ones.
ALIAS_PLAN = {"ALIAS": 10, "STRICT": 1, "CLEAN": 1}
ALIAS_CORPORA = {
    "mquake": {"sample": "holdout.json", "source": "labels.holdout.txt",
               "out": "labels.alias.human.txt", "exclude": None},
    "ripple": {"sample": "sample.ripple.json", "source": "labels.ripple.claude.txt",
               "out": "labels.ripple-alias.human.txt", "exclude": "labels.ripple.human.txt"},
}


def _blocks(text: str) -> tuple[str, dict[str, str]]:
    parts = text.split("### ")
    return parts[0], {p[:3]: "### " + p for p in parts[1:]}


def _blank(block: str) -> str:
    block = re.sub(r"^label:.*$", "label:", block, flags=re.M)
    return re.sub(r"^note:.*$", "note:", block, flags=re.M)


def draw(name: str, alias: bool = False) -> None:
    spec = (ALIAS_CORPORA if alias else CORPORA)[name]
    plan = ALIAS_PLAN if alias else PLAN
    # A second labeller answering the same item twice adds nothing. The draw
    # skips whatever the first human pass already covered.
    seen: set[str] = set()
    if spec.get("exclude"):
        # Item ids are per-sample and every sample numbers from 001, so an
        # exclude file drawn from a different sample excludes by collision.
        # Refuse rather than silently drop the wrong items.
        ex_blocks = _blocks((HERE / spec["exclude"]).read_text(encoding="utf-8"))[1]
        src_ids = set(_blocks((HERE / spec["source"]).read_text(encoding="utf-8"))[1])
        stray = set(ex_blocks) - src_ids
        if stray:
            raise SystemExit(
                f"{spec['exclude']} holds {len(stray)} item id(s) absent from "
                f"{spec['source']}, so the two are labellings of DIFFERENT samples "
                f"and excluding by id would exclude the wrong items. "
                f"A non-empty overlap is not enough to rule this out: the wrong "
                f"config this guard was written for shared 6 ids out of 25.")
        seen = set(ex_blocks)
    sample = json.loads((HERE / spec["sample"]).read_text(encoding="utf-8"))
    header, blocks = _blocks((HERE / spec["source"]).read_text(encoding="utf-8"))
    assign = sample["assignment"]

    # Group by verdict, then spread each verdict's quota evenly over the files
    # or subsets that carry it, so no single released file dominates the draw.
    by_verdict: dict[str, dict[str, list[str]]] = {}
    for item_id, row in assign.items():
        if item_id not in blocks or item_id in seen:
            continue
        cell = row["stratum"].rsplit("/", 1)[0]
        by_verdict.setdefault(row["verdict"], {}).setdefault(cell, []).append(item_id)

    rng = random.Random(SEED)
    picked: list[str] = []
    for verdict, quota in plan.items():
        cells = sorted(by_verdict.get(verdict, {}))
        if not cells:
            continue
        per, extra = divmod(quota, len(cells))
        for i, cell in enumerate(cells):
            want = per + (1 if i < extra else 0)
            rows = sorted(by_verdict[verdict][cell])
            picked += rng.sample(rows, min(want, len(rows)))
    picked.sort()

    out = [header.rstrip("\n"), "", ""]
    for item_id in picked:
        out.append(_blank(blocks[item_id]).rstrip("\n"))
        out.append("")
    (HERE / spec["out"]).write_text("\n".join(out) + "\n", encoding="utf-8")

    counts: dict[str, int] = {}
    for item_id in picked:
        counts[assign[item_id]["stratum"]] = counts.get(assign[item_id]["stratum"], 0) + 1
    print(f"{spec['out']}: {len(picked)} items")
    for cell in sorted(counts):
        print(f"    {cell:24} {counts[cell]}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", choices=sorted(CORPORA), default=None)
    ap.add_argument("--alias", action="store_true",
                    help="draw the alias-weighted sets instead")
    args = ap.parse_args()
    for name in ([args.adapter] if args.adapter else sorted(CORPORA)):
        draw(name, alias=args.alias)
    if args.alias:
        print("\nNo verdicts in either file. Label with:")
        print("  python3 validation/label.py --labels validation/labels.alias.human.txt")
        print("  python3 validation/label.py --labels validation/labels.ripple-alias.human.txt")
        return 0
    print("\nNo verdicts in either file. Label with:")
    print("  python3 validation/label.py --labels validation/labels.human.txt")
    print("  python3 validation/label.py --labels validation/labels.ripple.human.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
