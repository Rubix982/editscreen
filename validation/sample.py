"""Draw the stratified sample that the matchers get scored against.

    python3 validation/sample.py                      # MQuAKE -> labels.txt
    python3 validation/sample.py --adapter ripple     # RippleEdits
    python3 validation/sample.py --data DIR           # benchmarks elsewhere

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

WHY EVERY ROW CARRIES A CLUSTER.

Items are not independent. Three MQuAKE questions share one case and one
edited subject; a few dozen RippleEdits prompts share one entry and one
recovered subject label. A bootstrap that resamples rows treats those as
separate draws and reports an interval narrower than the evidence
supports. `cluster` names the thing that was really sampled, and the
scorer resamples clusters inside each stratum.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(REPO / "src"))

from editscreen import MATCHER_VERSION, screen_any  # noqa: E402
from editscreen.adapters import mquake, ripple  # noqa: E402

import wikidata  # noqa: E402  (validation/wikidata.py, beside this file)

# The benchmark files live in the edit-slice repo, not in this one, and
# these are the lines that will not survive being moved to another
# machine. Pass --data to override.
EDIT_SLICE = Path.home() / "code/open-concept-lab/ai/edit-slice/data"

LEGEND_HEAD = """\
# The labelled set — fill in every `label:` with ONE letter.
#
"""

LETTERS = """\
#   s   the subject's own name appears in the probe, written out in full
#   a   only a VARIANT appears — a surname alone, a given name, a pen name
#   d   no name appears, but the probe describes the subject well enough
#       that a reader could say who it is ("the author of The Man of Feeling")
#   n   none of the above: nothing in the probe points at the edited subject
#
# When the match sits INSIDE a longer name, ask which entity that longer
# name denotes. The test is the entity, never the string.
#   - it denotes the subject, or a product carrying the subject's own name
#     -> `a`.  "Aston Martin DB9" and "Ford Taurus" carry the maker's name,
#     and the maker is the subject.
#   - it denotes something else that merely shares a name part -> `d`.
#     "Mike Mignola" is not Mike Richardson. "Ford Orion" is not Henry Ford:
#     the man is reached only as "the founder of the manufacturer".
#
# This was not written down for the first held-out pass. It is what that
# pass did, reconstructed from its own four `note:` lines and checked to
# hold across all 47 of its items. Writing it down is what stops the next
# pass from drifting, which one of them already did.
"""

LEGEND_TAIL = """\
#
# `s` and `a` are what the screen claims to detect, so they decide its
# precision and recall. `d` is what it deliberately does not detect, and
# counting them is how we find out how loose the lower bound is.
#
# `note:` is optional and only worth filling when an item fits none of the
# letters. Those are the interesting ones — the levels in types.py were
# written from a handful of examples and have never met real data.
#
# Nothing here says what the screen decided. That is deliberate: seeing its
# verdict would invite you to agree with it, and the number that inflates
# is precision. The verdicts are in sample.json and the scorer rejoins them.
#
# Stop whenever you like. Every stopping point is a usable sample; the
# scorer reweights on what is actually filled in.
"""

MQUAKE_LEGEND = (LEGEND_HEAD + LETTERS + """\
#
# For an item with several edits, answer about the STRONGEST case among
# them: if any one subject is named in full, the answer is `s`.
""" + LEGEND_TAIL)

RIPPLE_LEGEND = (LEGEND_HEAD + LETTERS + """\
#   w   the `edit:` line is not this entry's subject at all — the adapter
#       recovered the wrong string. `w` beats every other letter: answer it
#       whenever it applies, whatever the probe says.
#
# RippleEdits names its subject by Wikidata QID, and the adapter has no
# knowledge base, so it reads a label back out of the entry's own prompts.
# `edit:` is what it recovered and `subject:` is what Wikidata says that
# QID is. When they disagree, the item is `w` — that is a failure of the
# recovery and not of the matcher, and the whole point of this draw is to
# tell the two apart.
#
# Answer `s`, `a`, `d` and `n` about `subject:`, the real one. A probe that
# names the recovered string but not the real subject is still `w`.
""" + LEGEND_TAIL)

# How many to draw from each (benchmark, verdict) stratum. `None` means
# take the whole stratum, for strata too small to sample.
MQUAKE_PLAN: dict[tuple[str, str], int | None] = {
    ("MQuAKE-T", "STRICT"): None,   # 21 in all
    ("MQuAKE-T", "ALIAS"): 40,
    ("MQuAKE-T", "CLEAN"): 60,
    ("MQuAKE-CF-3k", "STRICT"): 40,
    ("MQuAKE-CF-3k", "ALIAS"): 40,
    ("MQuAKE-CF-3k", "CLEAN"): 60,
}

# Three subsets crossed with three verdicts, twenty each. Even, because
# no subset is the headline and the three recover their subjects at rates
# ten points apart; an uneven draw would decide in advance which one the
# interval is tightest on.
RIPPLE_PLAN: dict[tuple[str, str], int | None] = {
    (subset, level): 20
    for subset in ("recent", "random", "popular")
    for level in ("STRICT", "ALIAS", "CLEAN")
}

SEED = 20261124
RIPPLE_SEED = 20261124


def mquake_cluster(item_id: str) -> str:
    """`MQuAKE-T:1234:q2` -> `MQuAKE-T:1234`. Three questions, one case,
    one edit: they move together and are one draw, not three."""
    return re.sub(r":q\d+$", "", item_id)


def ripple_cluster(item_id: str) -> str:
    """`recent:12:Forgetfulness:0:3` -> `recent:12`. Every prompt under one
    entry shares the one recovered subject label, so a wrong recovery is
    one mistake however many prompts inherit it."""
    return ":".join(item_id.split(":")[:2])


class Bench:
    """What differs between one benchmark and another, in one place."""

    def __init__(self, name, module, data, files, plan, legend, cluster, seed):
        self.name = name
        self.module = module
        self.data = data
        self.files = files
        self.plan = plan
        self.legend = legend
        self.cluster = cluster
        self.seed = seed

    def extra_lines(self, item, truth: dict) -> list[str]:
        """Lines between `edit:` and `probe:` in a labelling block."""
        return []


class RippleBench(Bench):
    """RippleEdits blocks carry what Wikidata says the subject is.

    Without it `w` cannot be answered at all: the recovered label came out
    of the entry's own prompts, so those prompts cannot adjudicate it. The
    screen's verdict is still hidden, which is what the blinding was for.
    """

    def extra_lines(self, item, truth: dict) -> list[str]:
        row = truth.get(ripple_cluster(item.item_id))
        if row is None:
            return ["subject: ?"]
        label = row.get("label")
        alias = ", ".join((row.get("aliases") or [])[:6])
        out = [f"subject: {label if label else '(no English label)'}"]
        if alias:
            out.append(f"also:    {alias}")
        return out


BENCHES = {
    "mquake": Bench("mquake", mquake, EDIT_SLICE / "mquake",
                    ("MQuAKE-T", "MQuAKE-CF-3k"), MQUAKE_PLAN, MQUAKE_LEGEND,
                    mquake_cluster, SEED),
    "ripple": RippleBench("ripple", ripple, EDIT_SLICE / "ripple",
                          ("recent", "random", "popular"), RIPPLE_PLAN,
                          RIPPLE_LEGEND, ripple_cluster, RIPPLE_SEED),
}


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


def rescore(bench: Bench, data: Path, meta_path: Path) -> int:
    """Refresh the verdicts on the draw already made, without redrawing.

    A matcher change moves items between levels, and re-running the draw
    would throw away labels that are still perfectly valid — they describe
    the items, not the screen. But it cannot simply overwrite the stratum
    either: the stratum is what each item's SELECTION PROBABILITY was based
    on, so it is part of the design and stays fixed. The new verdict is
    recorded beside it as one more measured attribute of the item, and
    `score.py` weights by the first and flags by the second.
    """
    meta = json.loads(meta_path.read_text())
    verdicts = {}
    for name in sorted({k.split("/")[0] for k in meta["stratum_sizes"]}):
        for item in bench.module.load(data / f"{name}.json"):
            verdicts[item.item_id] = screen_any(item.edits, item.probe).level.name

    moved = 0
    for row in meta["assignment"].values():
        was = row.get("verdict", row["stratum"].split("/")[1])
        now = verdicts[row["item"]]
        row["verdict"] = now
        row.setdefault("cluster", bench.cluster(row["item"]))
        moved += was != now

    meta["matcher_version"] = MATCHER_VERSION
    meta["editscreen_commit"] = editscreen_commit()
    meta_path.write_text(json.dumps(meta, indent=1) + "\n")
    print(f"rescored {len(meta['assignment'])} items at matcher "
          f"{MATCHER_VERSION}: {moved} changed level")
    return 0


def subject_truth(bench: Bench, data: Path, clusters: set[str],
                  offline: bool) -> dict:
    """{cluster: {label, aliases}} for the entries actually drawn.

    Only RippleEdits needs this, and only for adjudication. MQuAKE hands
    the screen a subject string, so there is nothing to adjudicate: the
    subject in `labels.txt` IS the benchmark's own.
    """
    if bench.name != "ripple":
        return {}
    qids: dict[str, str] = {}
    by_file: dict[str, set[int]] = defaultdict(set)
    for c in clusters:
        stem, _, idx = c.partition(":")
        by_file[stem].add(int(idx))
    for stem, wanted in by_file.items():
        records = json.loads((data / f"{stem}.json").read_text(encoding="utf-8"))
        for i in wanted:
            qid = ((records[i] or {}).get("edit") or {}).get("subject_id")
            if qid:
                qids[f"{stem}:{i}"] = qid
    if offline:
        rows = {q: r for q, r in json.loads(
            (HERE / "wikidata.json").read_text()).items()}
    else:
        rows = wikidata.labels(sorted(set(qids.values())))
    return {c: dict(rows.get(q, {}), qid=q) for c, q in qids.items()}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--adapter", choices=sorted(BENCHES), default="mquake")
    ap.add_argument("--data", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--meta", type=Path)
    ap.add_argument("--seed", type=int)
    ap.add_argument("--plan", help="stratum=n pairs, comma separated, to "
                                   "override the plan for a focused draw")
    ap.add_argument("--exclude", type=Path, action="append", default=[],
                    help="a sample.json whose items must not be drawn again")
    ap.add_argument("--rescore", action="store_true",
                    help="keep the existing draw and refresh its verdicts, "
                         "for when a matcher changes")
    ap.add_argument("--offline", action="store_true",
                    help="never call Wikidata; use validation/wikidata.json")
    args = ap.parse_args()

    bench = BENCHES[args.adapter]
    suffix = "" if bench.name == "mquake" else f".{bench.name}"
    data = args.data or bench.data
    out = args.out or HERE / f"labels{suffix}.txt"
    meta_path = args.meta or HERE / f"sample{suffix}.json"
    seed = bench.seed if args.seed is None else args.seed

    if args.rescore:
        return rescore(bench, data, meta_path)

    if not data.is_dir():
        print(f"no benchmark directory at {data} — pass --data", file=sys.stderr)
        return 1

    plan = dict(bench.plan)
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

    rng = random.Random(seed)
    strata: dict[tuple[str, str], list] = defaultdict(list)
    sizes: dict[str, int] = {}
    digests: dict[str, str] = {}
    coverage: dict[str, dict] = {}

    for name in bench.files:
        path = data / f"{name}.json"
        if not path.exists():
            print(f"missing {path}", file=sys.stderr)
            return 1
        digests[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        if hasattr(bench.module, "coverage"):
            coverage[name] = bench.module.coverage(path)
        for item in bench.module.load(path):
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

    truth = subject_truth(bench, data,
                          {bench.cluster(it.item_id) for _, it, _ in drawn},
                          args.offline)

    # The stratum carries the screen's own verdict, and the item id now
    # carries the benchmark's name, which carries its base rate — MQuAKE-T
    # is 98% clean and knowing that is a thumb on the scale. Both are
    # recorded HERE and kept out of labels.txt, which shows a labeller the
    # edits and the probe and nothing else. The block number is the key.
    meta = {
        "assignment": {f"{i:03d}": {"stratum": "/".join(k), "item": it.item_id,
                                    "verdict": v.level.name,
                                    "cluster": bench.cluster(it.item_id)}
                       for i, (k, it, v) in enumerate(drawn, start=1)},
        "adapter": bench.name,
        "drawn": date.today().isoformat(),
        "seed": seed,
        "excluded_items": len(seen),
        "matcher_version": MATCHER_VERSION,
        "editscreen_commit": editscreen_commit(),
        "stratum_sizes": sizes,
        "stratum_drawn": {"/".join(k): sum(1 for kk, _, _ in drawn if kk == k)
                          for k in plan},
        "input_sha256": digests,
    }
    if coverage:
        meta["coverage"] = coverage
    if truth:
        meta["subject_truth"] = truth
    meta_path.write_text(json.dumps(meta, indent=1, ensure_ascii=False) + "\n")

    lines = [bench.legend]
    for i, (_key, item, _verdict) in enumerate(drawn, start=1):
        lines.append(f"### {i:03d}")
        for e in item.edits:
            lines.append(f"edit:    {e.subject}")
        lines.extend(bench.extra_lines(item, truth))
        lines.append(f"probe:   {item.probe}")
        lines.append("label:")
        lines.append("note:")
        lines.append("")

    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out} — {len(drawn)} items")
    for k, n in sorted(meta["stratum_drawn"].items()):
        print(f"  {k:<22} {n:>4} of {sizes.get(k, 0):>6,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
