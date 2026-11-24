"""Score the matchers against the hand labels.

    python3 validation/score.py

Reads `labels.txt` and `sample.json`, and reports precision and recall with
bootstrap intervals. Unlabelled items are skipped, so this is worth running
part-way through.

HOW THE REWEIGHTING WORKS, because the raw counts are not the answer.

The strata were sampled at wildly different rates — every one of MQuAKE-T's
21 strict matches is here, against 60 of its 5,516 clean items — so a labelled
item from a small stratum stands for one real item while a labelled clean item
stands for about ninety. Every count below is a sum of those weights, not a
count of rows. Reading the rows directly would put the screen's precision at
roughly the ratio of the sample plan and have nothing to do with the corpus.

WHAT IS BEING SCORED.

The screen claims to detect a name or a name variant, nothing more. So:

  detected   = the screen returned STRICT or ALIAS
  present    = the label is `s` or `a` — a name really is there
  reachable  = the label is `s`, `a` or `d` — a reader could name the subject

Precision and recall are `detected` against `present`. The gap between
`present` and `reachable` is the part the screen declines to chase, and
reporting it is how the lower bound gets a size instead of an adjective.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
VALID = {"s", "a", "d", "n"}
PRESENT = {"s", "a"}
REACHABLE = {"s", "a", "d"}
BOOTSTRAP = 10_000
SEED = 7


def parse(path: Path) -> list[dict]:
    """One record per `### nnn` block. Blocks with an empty label are kept
    and marked, so the report can say how far through the file we are."""
    rows, cur = [], None
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if line.startswith("###"):
            if cur:
                rows.append(cur)
            cur = {"id": line[3:].strip(), "edits": []}
            continue
        if cur is None or not line or line.startswith("#"):
            continue
        m = re.match(r"(stratum|item|edit|probe|label|note):\s*(.*)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if key == "edit":
            cur["edits"].append(val)
        else:
            cur[key] = val
    if cur:
        rows.append(cur)
    return rows


def wsum(rows, weights, predicate) -> float:
    return sum(weights[r["stratum"]] for r in rows if predicate(r))


def ratio(num: float, den: float) -> float | None:
    return num / den if den else None


def boot(rows, weights, num_p, den_p, rng) -> tuple[float, float] | None:
    """Percentile interval, resampling WITHIN each stratum.

    Resampling the pooled rows would let a draw change the stratum mix,
    which the design fixed on purpose; the uncertainty being estimated is
    about the items inside each stratum, not about how many were drawn.
    """
    by = defaultdict(list)
    for r in rows:
        by[r["stratum"]].append(r)
    out = []
    for _ in range(BOOTSTRAP):
        sample = [rng.choice(v) for v in by.values() for _ in v]
        v = ratio(wsum(sample, weights, num_p), wsum(sample, weights, den_p))
        if v is not None:
            out.append(v)
    if len(out) < BOOTSTRAP // 2:
        return None
    out.sort()
    return out[int(0.025 * len(out))], out[int(0.975 * len(out))]


def line(name: str, num: float, den: float, ci, note: str = "") -> str:
    v = ratio(num, den)
    if v is None:
        return f"  {name:<34} —      (nothing to divide by) {note}"
    span = f"[{ci[0]:5.1%}, {ci[1]:5.1%}]" if ci else "[interval unavailable]"
    return f"  {name:<34} {v:6.1%}  {span}  n={den:,.0f} weighted {note}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--labels", type=Path, default=HERE / "labels.txt")
    ap.add_argument("--sample", type=Path, default=HERE / "sample.json")
    args = ap.parse_args()

    meta = json.loads(args.sample.read_text())
    rows = parse(args.labels)
    # labels.txt deliberately does not say which stratum an item came from,
    # so that the labeller cannot see the screen's verdict. Rejoin here.
    for r in rows:
        r["stratum"] = meta["assignment"][r["id"]]
    total = len(rows)

    bad = [r["id"] for r in rows if r.get("label") and r["label"] not in VALID]
    if bad:
        print(f"unrecognised labels (want one of {sorted(VALID)}): {', '.join(bad)}",
              file=sys.stderr)
        return 1

    done = [r for r in rows if r.get("label")]
    if not done:
        print("nothing labelled yet — fill in some `label:` lines in labels.txt")
        return 0

    labelled_per = defaultdict(int)
    for r in done:
        labelled_per[r["stratum"]] += 1

    missing = [s for s in meta["stratum_sizes"] if not labelled_per.get(s)]
    weights = {s: meta["stratum_sizes"][s] / n for s, n in labelled_per.items()}

    print(f"labelled {len(done)} of {total} drawn "
          f"(editscreen {meta.get('editscreen_commit', '?')[:12]}, "
          f"matcher {meta['matcher_version']})\n")
    print("  stratum                  labelled   stands for")
    for s in sorted(meta["stratum_sizes"]):
        n = labelled_per.get(s, 0)
        size = meta["stratum_sizes"][s]
        w = f"{weights[s]:.1f}x" if n else "—"
        print(f"  {s:<24} {n:>4}/{size:<7,} {w:>8}")

    if missing:
        print("\n  WARNING: nothing labelled in " + ", ".join(missing) +
              ".\n  Those items are dropped, so every number below describes a corpus"
              "\n  that does not contain them. Label a few before quoting any of it.")

    rng = random.Random(SEED)
    det = lambda r: not r["stratum"].endswith("/CLEAN")          # noqa: E731
    pres = lambda r: r["label"] in PRESENT                        # noqa: E731
    reach = lambda r: r["label"] in REACHABLE                     # noqa: E731

    benchmarks = sorted({s.split("/")[0] for s in meta["stratum_sizes"]})

    # Reported per benchmark and never pooled. MQuAKE-T and MQuAKE-CF-3k
    # name the edited subject at 1.6% and 67.8%, so an average over the two
    # describes no corpus that exists and would move if either file were
    # subsetted. Same rule the RippleEdits subsets are under.
    print("\nDoes it flag the items that name a subject?")
    for b in benchmarks:
        sub = [r for r in done if r["stratum"].startswith(b + "/")]
        print(f"  {b}")
        if not sub:
            print("    nothing labelled")
            continue
        hit = lambda r: det(r) and pres(r)  # noqa: E731
        print("  " + line("precision", wsum(sub, weights, hit),
                          wsum(sub, weights, det),
                          boot(sub, weights, hit, det, rng)))
        print("  " + line("recall", wsum(sub, weights, hit),
                          wsum(sub, weights, pres),
                          boot(sub, weights, hit, pres, rng)))

    print("\nPer level — did it also get the level right?")
    for level, want in (("STRICT", {"s"}), ("ALIAS", {"a"})):
        sub = [r for r in done if r["stratum"].endswith("/" + level)]
        if not sub:
            print(f"  {level:<34} —      (none labelled)")
            continue
        print(line(f"{level}: level is right",
                   wsum(sub, weights, lambda r: r["label"] in want),
                   wsum(sub, weights, lambda r: True),
                   boot(sub, weights, lambda r: r["label"] in want,
                        lambda r: True, rng)))
        print(line(f"{level}: flag is right",
                   wsum(sub, weights, pres), wsum(sub, weights, lambda r: True),
                   boot(sub, weights, pres, lambda r: True, rng)))

    print("\nHow loose is the lower bound? — share of items a reader could identify")
    for b in benchmarks:
        sub = [r for r in done if r["stratum"].startswith(b + "/")]
        print(f"  {b}")
        if not sub:
            print("    nothing labelled")
            continue
        every = lambda r: True  # noqa: E731
        print("  " + line("named or varied (what it chases)",
                          wsum(sub, weights, pres), wsum(sub, weights, every),
                          boot(sub, weights, pres, every, rng)))
        print("  " + line("identifiable at all", wsum(sub, weights, reach),
                          wsum(sub, weights, every),
                          boot(sub, weights, reach, every, rng)))

    notes = [r for r in done if r.get("note")]
    if notes:
        print(f"\nItems that fitted none of the four letters ({len(notes)}):")
        for r in notes:
            print(f"  {r['id']} [{r['stratum']}] {r['note']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
