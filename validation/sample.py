"""Draw the stratified sample that the matchers get scored against.

    python3 validation/sample.py              # writes validation/labels.txt
    python3 validation/sample.py --data DIR   # if the benchmarks live elsewhere

WHY STRATIFIED, and not just a few hundred items off the top.

Precision and recall need different items and the corpus will not supply
both from one uniform draw. Precision asks: of the items the screen
flagged, how many really name the subject — so it needs flagged items.
Recall asks: of the items that really name the subject, how many did the
screen flag — so it needs the ones it MISSED, which live among the items
it called clean. In MQuAKE-T only 1.57% are flagged at all, so a uniform
sample of 200 would contain about three flagged items and tell us nothing
about precision.

So each (benchmark, verdict) pair is a stratum sampled at its own rate,
and `score.py` reweights by the real stratum sizes recorded here. Two of
the strata are small enough to take whole: MQuAKE-T has only 21 strict
matches in 5,604 items, and a census has no sampling error at all.

WHY THE ROWS ARE SHUFFLED ACROSS STRATA.

Labelling stops when it stops. If the file ran stratum by stratum, an
hour's work would be a complete census of one stratum and nothing of the
others, which is not an estimate of anything. Interleaved, every stopping
point is a smaller version of the same design, and `score.py` reweights
on what was actually labelled rather than what was drawn.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import subprocess
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(REPO / "src"))

from editscreen import MATCHER_VERSION, screen_any  # noqa: E402
from editscreen.adapters import mquake  # noqa: E402

# The MQuAKE files live in the edit-slice repo, not in this one, and this
# is the one line that will not survive being moved to another machine.
# Pass --data to override it.
DEFAULT_DATA = Path.home() / "code/open-concept-lab/ai/edit-slice/data/mquake"

# How many to draw from each (benchmark, verdict) stratum. `None` means
# take the whole stratum, for strata too small to sample.
PLAN: dict[tuple[str, str], int | None] = {
    ("MQuAKE-T", "STRICT"): None,   # 21 in all
    ("MQuAKE-T", "ALIAS"): 40,
    ("MQuAKE-T", "CLEAN"): 60,
    ("MQuAKE-CF-3k", "STRICT"): 40,
    ("MQuAKE-CF-3k", "ALIAS"): 40,
    ("MQuAKE-CF-3k", "CLEAN"): 60,
}

SEED = 20261124

LEGEND = """\
# The labelled set — fill in every `label:` with ONE letter.
#
#   s   the subject's own name appears in the probe, written out in full
#   a   only a VARIANT appears — a surname alone, a given name, a pen name
#   d   no name appears, but the probe describes the subject well enough
#       that a reader could say who it is ("the author of The Man of Feeling")
#   n   none of the above: nothing in the probe points at the edited subject
#
# For an item with several edits, answer about the STRONGEST case among
# them: if any one subject is named in full, the answer is `s`.
#
# `s` and `a` are what the screen claims to detect, so they decide its
# precision and recall. `d` is what it deliberately does not detect, and
# counting them is how we find out how loose the lower bound is.
#
# `note:` is optional and only worth filling when an item fits none of the
# four letters. Those are the interesting ones — the levels in types.py
# were written from a handful of examples and have never met real data.
#
# Nothing here says what the screen decided. That is deliberate: seeing its
# verdict would invite you to agree with it, and the number that inflates
# is precision. The verdicts are in sample.json and the scorer rejoins them.
#
# Stop whenever you like. Every stopping point is a usable sample; the
# scorer reweights on what is actually filled in.
"""


def editscreen_commit() -> str | None:
    """The commit these verdicts came from.

    The version string alone does not identify the code while 0.2 is
    unreleased, and a label set is only worth keeping if the thing it
    labels can be named exactly.
    """
    try:
        sha = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"],
                             capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain"],
                               capture_output=True, text=True, check=True).stdout.strip()
        return f"{sha}-dirty" if dirty else sha
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def rescore(data: Path) -> int:
    """Refresh the verdicts on the draw already made, without redrawing.

    A matcher change moves items between levels, and re-running the draw
    would throw away labels that are still perfectly valid — they describe
    the items, not the screen. But it cannot simply overwrite the stratum
    either: the stratum is what each item's SELECTION PROBABILITY was based
    on, so it is part of the design and stays fixed. The new verdict is
    recorded beside it as one more measured attribute of the item, and
    `score.py` weights by the first and flags by the second.
    """
    meta = json.loads((HERE / "sample.json").read_text())
    verdicts = {}
    for name in sorted({k.split("/")[0] for k in meta["stratum_sizes"]}):
        for item in mquake.load(data / f"{name}.json"):
            verdicts[item.item_id] = screen_any(item.edits, item.probe).level.name

    moved = 0
    for row in meta["assignment"].values():
        was = row.get("verdict", row["stratum"].split("/")[1])
        now = verdicts[row["item"]]
        row["verdict"] = now
        moved += was != now

    meta["matcher_version"] = MATCHER_VERSION
    meta["editscreen_commit"] = editscreen_commit()
    args.meta.write_text(json.dumps(meta, indent=1) + "\n")
    print(f"rescored {len(meta['assignment'])} items at matcher "
          f"{MATCHER_VERSION}: {moved} changed level")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", type=Path, default=DEFAULT_DATA)
    ap.add_argument("--out", type=Path, default=HERE / "labels.txt")
    ap.add_argument("--meta", type=Path, default=HERE / "sample.json")
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--plan", help="stratum=n pairs, comma separated, to "
                                   "override PLAN for a focused draw")
    ap.add_argument("--exclude", type=Path, action="append", default=[],
                    help="a sample.json whose items must not be drawn again")
    ap.add_argument("--rescore", action="store_true",
                    help="keep the existing draw and refresh its verdicts, "
                         "for when a matcher changes")
    args = ap.parse_args()

    if args.rescore:
        return rescore(args.data)

    if not args.data.is_dir():
        print(f"no benchmark directory at {args.data} — pass --data", file=sys.stderr)
        return 1

    plan = dict(PLAN)
    if args.plan:
        plan = {}
        for pair in args.plan.split(","):
            key, _, n = pair.partition("=")
            benchmark, _, level = key.strip().partition("/")
            plan[(benchmark, level)] = int(n)

    # A fix derived by reading one sample's errors cannot be scored on that
    # sample. --exclude keeps a later draw disjoint from an earlier one.
    seen: set[str] = set()
    for other in args.exclude:
        for row in json.loads(other.read_text())["assignment"].values():
            seen.add(row["item"])

    rng = random.Random(args.seed)
    strata: dict[tuple[str, str], list] = defaultdict(list)
    sizes: dict[str, int] = {}
    digests: dict[str, str] = {}

    for name in sorted({b for b, _ in PLAN}):
        path = args.data / f"{name}.json"
        if not path.exists():
            print(f"missing {path}", file=sys.stderr)
            return 1
        digests[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        for item in mquake.load(path):
            if item.item_id in seen:
                continue
            verdict = screen_any(item.edits, item.probe)
            strata[(name, verdict.level.name)].append((item, verdict))

    drawn = []
    for key, want in plan.items():
        pool = strata.get(key, [])
        sizes["/".join(key)] = len(pool)
        if not pool:
            print(f"warning: stratum {key} is empty", file=sys.stderr)
            continue
        take = len(pool) if want is None else min(want, len(pool))
        drawn.extend((key, it, v) for it, v in rng.sample(pool, take))

    rng.shuffle(drawn)

    # The stratum carries the screen's own verdict, and the item id now
    # carries the benchmark's name, which carries its base rate — MQuAKE-T
    # is 98% clean and knowing that is a thumb on the scale. Both are
    # recorded HERE and kept out of labels.txt, which shows a labeller the
    # edits and the probe and nothing else. The block number is the key.
    meta = {
        "assignment": {f"{i:03d}": {"stratum": "/".join(k), "item": it.item_id,
                                    "verdict": v.level.name}
                       for i, (k, it, v) in enumerate(drawn, start=1)},
        "drawn": date.today().isoformat(),
        "seed": args.seed,
        "excluded_items": len(seen),
        "matcher_version": MATCHER_VERSION,
        "editscreen_commit": editscreen_commit(),
        "stratum_sizes": sizes,
        "stratum_drawn": {"/".join(k): sum(1 for kk, _, _ in drawn if kk == k)
                          for k in plan},
        "input_sha256": digests,
    }
    args.meta.write_text(json.dumps(meta, indent=1) + "\n")

    lines = [LEGEND]
    for i, (_key, item, _verdict) in enumerate(drawn, start=1):
        lines.append(f"### {i:03d}")
        for e in item.edits:
            lines.append(f"edit:    {e.subject}")
        lines.append(f"probe:   {item.probe}")
        lines.append("label:")
        lines.append("note:")
        lines.append("")

    args.out.write_text("\n".join(lines))
    print(f"wrote {args.out} — {len(drawn)} items")
    for k, n in sorted(meta["stratum_drawn"].items()):
        print(f"  {k:<22} {n:>4} of {sizes.get(k, 0):>6,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
