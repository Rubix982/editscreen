"""Draw the items on which the two recovery rules disagree. [T-019]

    python3 validation/sample_pairs.py

WHY THIS IS A DIFFERENT DRAW FROM `sample.py --adapter ripple`.

[C-012] found that the RippleEdits adapter's canonical-subject rule decides a
published rate. Taking the longest candidate across all six test types gives a
strict rate of 0.519 on `random`; restricting that pick to the five non-aliasing
types gives 0.707. The named-or-varied rate is the same either way, so every
prompt that moved went between STRICT and ALIAS inside the flagged set.

Which rule is right cannot be read off the existing labelled set. That set was
drawn stratified by the RELEASED rule's own verdicts, so it cannot be reweighted
to score a different one.

THE ONLY ITEMS THAT CAN SEPARATE TWO RULES ARE THE ONES THEY DISAGREE ON, and
labelling anything else spends a human hour on items where both rules are
already right together or wrong together. 4,044 prompts of the 38,092 screened
disagree. This draws from those, stratified by subset and by which way the
verdict moved.

ONE LABEL SCORES BOTH RULES. The question put to the labeller is about the
probe and the real subject — is the subject's own name written out, is only a
variant there, is it describable, is there nothing — and the answer settles both
rules at once, because the scorer already knows what each decided. That is why
the file shows neither verdict and neither recovered string.

WHAT IS SHOWN, AND WHY IT IS NOT THE RECOVERED NAME. `subject:` is the Wikidata
label for the QID the benchmark itself cites, with its aliases. Showing the
recovered strings would be the circularity this draw exists to escape: the whole
disagreement is about which recovered string is the subject's name.
"""
from __future__ import annotations

import collections
import hashlib
import json
import pathlib
import random
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
SEED = 20261124
PER_CELL = 6
SUBSETS = ("recent", "random", "popular")

sys.path.insert(0, str(ROOT / "src"))
from editscreen import screen                       # noqa: E402
from editscreen.adapters import ripple              # noqa: E402
from editscreen.types import Edit                   # noqa: E402


def _data() -> pathlib.Path | None:
    for root in (pathlib.Path.home() / "code" / "open-concept-lab" / "ai" / "edit-slice",
                 pathlib.Path.home() / "code" / "edit-slice", ROOT.parent / "edit-slice"):
        if (root / "data" / "ripple").exists():
            return root / "data" / "ripple"
    return None


def _narrow(entry: dict) -> dict:
    return {k: ([] if k == "Subject_Aliasing" else entry.get(k)) for k in ripple.CRITERIA}


def _rules(entry: dict):
    """(released, restricted) Edits for one entry, or None where a rule cannot name it."""
    full = ripple.candidates(entry)
    narrow = ripple.candidates(_narrow(entry))
    relation = (entry.get("edit") or {}).get("relation")

    def build(pool):
        if not pool:
            return None
        subject = max(pool, key=len)
        return Edit(subject=subject, relation=relation, object_new=None,
                    aliases=tuple(c for c in full if c != subject))
    return build(full), build(narrow)


def main() -> int:
    data = _data()
    if data is None:
        print("no RippleEdits release found beside this checkout")
        return 1

    pool: dict[str, list] = collections.defaultdict(list)
    sizes: collections.Counter = collections.Counter()
    sha = {}

    for subset in SUBSETS:
        path = data / f"{subset}.json"
        raw = path.read_bytes()
        sha[subset] = hashlib.sha256(raw).hexdigest()
        for i, entry in enumerate(json.loads(raw)):
            released, restricted = _rules(entry)
            if released is None or restricted is None:
                continue
            if released.subject == restricted.subject:
                continue
            qid = (entry.get("edit") or {}).get("subject_id")
            for crit in ripple.CRITERIA:
                for g, group in enumerate(entry.get(crit) or []):
                    for q, query in enumerate((group or {}).get("test_queries") or []):
                        prompt = (query or {}).get("prompt")
                        if not isinstance(prompt, str) or not prompt.strip():
                            continue
                        a = screen(released, prompt).level.name
                        b = screen(restricted, prompt).level.name
                        if a == b:
                            continue
                        cell = f"{subset}/{a}->{b}"
                        sizes[cell] += 1
                        pool[cell].append({
                            "item": f"{subset}:{i}:{crit}:{g}:{q}",
                            "cluster": f"{subset}:{i}",
                            "stratum": cell,
                            "qid": qid,
                            "probe": prompt,
                            "released_verdict": a,
                            "restricted_verdict": b,
                        })

    rng = random.Random(SEED)
    drawn = []
    for cell in sorted(pool):
        rows = sorted(pool[cell], key=lambda r: r["item"])
        drawn += rng.sample(rows, min(PER_CELL, len(rows)))
    drawn.sort(key=lambda r: r["item"])

    # Resolve the QIDs through the existing adjudicator, which caches and sends
    # nothing but the ids. A draw that cannot be adjudicated is not a draw.
    qids = sorted({r["qid"] for r in drawn if r["qid"]})
    subprocess.run([sys.executable, str(HERE / "wikidata.py"), *qids], check=True)
    wd = json.loads((HERE / "wikidata.json").read_text(encoding="utf-8"))

    assignment = {}
    for n, row in enumerate(drawn, 1):
        assignment[f"{n:03d}"] = {k: row[k] for k in
                                  ("stratum", "item", "cluster", "qid",
                                   "released_verdict", "restricted_verdict")}

    commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                            capture_output=True, text=True).stdout.strip()
    sample = {
        "assignment": assignment,
        "adapter": "ripple",
        "draw": "disagreement between the released and restricted recovery rules",
        "drawn": "2026-11-24",
        "seed": SEED,
        "per_cell": PER_CELL,
        "matcher_version": "0.2.0",
        "editscreen_commit": commit,
        "stratum_sizes": dict(sizes),
        "stratum_drawn": {c: sum(1 for r in drawn if r["stratum"] == c) for c in sorted(pool)},
        "input_sha256": sha,
    }
    (HERE / "sample.ripple-pairs.json").write_text(
        json.dumps(sample, indent=1), encoding="utf-8")

    lines = [
        "# The paired set — fill in every `label:` with ONE letter.",
        "#",
        "#   s   the subject's own name appears in the probe, written out in full",
        "#   a   only a VARIANT appears — a surname alone, a given name, a pen name,",
        "#       a longer or shorter form of the same name",
        "#   d   no name appears, but the probe describes the subject well enough",
        "#       that a reader could say who it is",
        "#   n   nothing in the probe points at the edited subject",
        "#",
        "# `subject:` is what Wikidata says the entry's subject id is, and `aliases:`",
        "# are the names Wikidata lists for it. Answer about THAT subject.",
        "#",
        "# WHY THESE ITEMS. The adapter has to work the subject's name out of the",
        "# benchmark's own prompts, and two reasonable ways of doing that disagree on",
        "# these items and only these. One of the two is wrong on each one. Your",
        "# letter decides which, so nothing here says what either of them decided —",
        "# and neither recovered name is shown, because which of those two strings is",
        "# the subject's name is the whole question.",
        "#",
        "# `s` versus `a` is the distinction that carries this draw, and it is the",
        "# same distinction as in the other label files: `s` only when the probe",
        "# carries the name on the `subject:` line, written out in full. A name on",
        "# the `aliases:` line is `a`, not `s` — the aliases are listed so you can",
        "# tell a real variant of this subject from a different person entirely.",
        "#",
        "# Stop whenever you like. Every stopping point is a usable sample.",
        "",
    ]
    for n, row in enumerate(drawn, 1):
        ent = wd.get(row["qid"]) or {}
        lines.append(f"### {n:03d}")
        lines.append(f"subject: {ent.get('label', '(unresolved)')}")
        if ent.get("aliases"):
            lines.append(f"aliases: {', '.join(ent['aliases'])}")
        lines.append(f"probe:   {row['probe']}")
        lines.append("label:")
        lines.append("note:")
        lines.append("")
    (HERE / "labels.ripple-pairs.human.txt").write_text(
        "\n".join(lines), encoding="utf-8")

    print(f"{len(drawn)} items drawn from {sum(sizes.values()):,} disagreeing prompts\n")
    for cell in sorted(sizes):
        print(f"  {cell:24} {sample['stratum_drawn'].get(cell, 0):>3} of {sizes[cell]:>6,}")
    print("\n  validation/labels.ripple-pairs.human.txt   <- fill this in")
    print("  validation/sample.ripple-pairs.json        <- the verdicts, kept apart")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
