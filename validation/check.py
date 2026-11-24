"""Draw a blind subset for a second labeller, and report agreement.

    python3 validation/check.py --draw 25     # writes labels.human.txt
                                              # ... fill it in ...
    python3 validation/check.py               # agreement against labels.claude.txt

WHY THIS EXISTS.

labels.claude.txt was produced by a model, not a person. That is a usable
way to label a few hundred items and a bad thing to leave unstated: every
precision figure scored against it inherits whatever that labeller gets
wrong. So a person labels a random subset without seeing those labels, and
the agreement between the two is reported beside the precision it
qualifies. Two error rates stacked, both named, rather than one hidden.

Agreement is reported two ways. Exact agreement counts the letters
matching. The one that matters for precision is agreement on the only
distinction precision rests on: whether a name or a variant is present at
all — `s` or `a` against `d` or `n`.
"""

from __future__ import annotations

import argparse
import random
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRESENT = {"s", "a"}


def read(path: Path) -> dict[str, tuple[str, str]]:
    out, ident, label, note = {}, None, "", ""
    for line in path.read_text().splitlines():
        if line.startswith("###"):
            if ident:
                out[ident] = (label, note)
            ident, label, note = line[3:].strip(), "", ""
        elif line.startswith("label:"):
            label = line.split(":", 1)[1].strip()
        elif line.startswith("note:"):
            note = line.split(":", 1)[1].strip()
    if ident:
        out[ident] = (label, note)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--draw", type=int, help="draw this many items and stop")
    ap.add_argument("--seed", type=int, default=99)
    ap.add_argument("--blank", type=Path, default=HERE / "labels.txt")
    ap.add_argument("--machine", type=Path, default=HERE / "labels.claude.txt")
    ap.add_argument("--human", type=Path, default=HERE / "labels.human.txt")
    args = ap.parse_args()

    if args.draw:
        if args.human.exists():
            print(f"{args.human} already exists — move it aside first")
            return 1
        src = args.blank.read_text().splitlines()
        ids = sorted(l[3:].strip() for l in src if l.startswith("###"))
        keep = set(random.Random(args.seed).sample(ids, min(args.draw, len(ids))))

        out, ident, block = [], None, []
        for line in src:
            if line.startswith("###"):
                if ident in keep:
                    out += block
                ident, block = line[3:].strip(), [line]
            elif ident is None:
                out.append(line)       # the legend
            else:
                block.append(line)
        if ident in keep:
            out += block
        args.human.write_text("\n".join(out) + "\n")
        print(f"wrote {args.human} — {len(keep)} items, seed {args.seed}\n"
              f"label them with:  python3 validation/label.py --labels {args.human}")
        return 0

    if not args.human.exists():
        print(f"no {args.human} yet — draw one with --draw 25")
        return 1

    machine, human = read(args.machine), read(args.human)
    both = [i for i in human if human[i][0] and machine.get(i, ("",))[0]]
    if not both:
        print("nothing labelled in the human file yet")
        return 0

    exact = sum(1 for i in both if human[i][0] == machine[i][0])
    coarse = sum(1 for i in both
                 if (human[i][0] in PRESENT) == (machine[i][0] in PRESENT))

    print(f"{len(both)} items labelled by both\n")
    print(f"  exact agreement on the letter        {exact}/{len(both)}"
          f"  {exact/len(both):.0%}")
    print(f"  agreement on name-present (s,a)      {coarse}/{len(both)}"
          f"  {coarse/len(both):.0%}")
    print("\n  The second line is the one precision rests on. The first can")
    print("  drop on an s-versus-a call without moving any reported number.")

    disagree = [i for i in both if human[i][0] != machine[i][0]]
    if disagree:
        print(f"\nDisagreements ({len(disagree)}):")
        for i in sorted(disagree):
            flag = "" if (human[i][0] in PRESENT) == (machine[i][0] in PRESENT) \
                else "   <- changes precision"
            print(f"  {i}  human={human[i][0]}  machine={machine[i][0]}{flag}")
            if human[i][1]:
                print(f"       human note: {human[i][1]}")
            if machine[i][1]:
                print(f"       machine note: {machine[i][1]}")
    counts = Counter(human[i][0] for i in both)
    print(f"\n  human label mix: {dict(sorted(counts.items()))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
