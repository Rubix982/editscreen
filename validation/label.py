"""Label the sample one item at a time.

    python3 validation/label.py

Shows the next unlabelled item, takes one letter, writes labels.txt before
asking the next. Quit whenever; nothing is held in memory. Editing
labels.txt by hand does the same job and the two can be mixed freely —
this file is a typing convenience, not a second source of truth.

It does NOT show what the screen decided, for the reason sample.py gives.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
VALID = {"s", "a", "d", "n", "w"}

HELP = """\
  s  the subject's own name appears in the probe, written out in full
  a  only a VARIANT appears — a surname alone, a given name, a pen name
  d  no name, but the probe describes the subject well enough to place it
  n  nothing in the probe points at the edited subject
  w  RippleEdits only: the `edit:` line is not this entry's subject at all.
     Compare it with `subject:`, which is what Wikidata says the QID is.
     `w` beats every other letter, and the four above are answered about
     `subject:`, the real one. It applies only where an `edit:` line is
     shown: the paired draw deliberately shows neither recovered string,
     so there is nothing for `w` to be about there.

  For several edits, answer about the STRONGEST case among them.
  Add a note after the letter for anything that fits none of the four:
      d the description is of the relation, not the subject

  ?  this help      -  skip for now      q  save and quit\
"""


def blocks(lines: list[str]) -> list[tuple[int, int]]:
    """(start, end) line index of each `### nnn` block."""
    starts = [i for i, l in enumerate(lines) if l.startswith("###")]
    return [(s, e) for s, e in zip(starts, starts[1:] + [len(lines)])]


def field(lines, span, name):
    for i in range(*span):
        m = re.match(rf"{name}:\s*(.*)$", lines[i])
        if m:
            return i, m.group(1).strip()
    return None, None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--labels", type=Path, default=HERE / "labels.txt")
    args = ap.parse_args()

    if not args.labels.exists():
        print(f"no label file at {args.labels}\n"
              "draw one first:  python3 validation/sample.py", file=sys.stderr)
        return 1

    lines = args.labels.read_text().splitlines()
    spans = blocks(lines)
    total = len(spans)
    done = sum(1 for s in spans if field(lines, s, "label")[1])

    print(f"{done} of {total} labelled.  `?` for the letters, `q` to stop.\n")

    for span in spans:
        li, current = field(lines, span, "label")
        if current:
            continue
        ident = lines[span[0]][3:].strip()
        edits = [lines[i].split(":", 1)[1].strip()
                 for i in range(*span) if lines[i].startswith("edit:")]
        _, probe = field(lines, span, "probe")
        # The paired draw has no `edit:` line at all: it shows the Wikidata
        # label for the subject rather than either recovered string, because
        # which of those two is the subject's name is the question it asks.
        # Printing only `edit:` lines would leave that file unlabellable.
        _, subject = field(lines, span, "subject")
        _, aliases = field(lines, span, "aliases")

        print(f"── {ident}   ({done}/{total} done)")
        for e in edits:
            print(f"   edited:  {e}")
        if subject:
            print(f"   subject: {subject}")
        if aliases:
            print(f"   aliases: {aliases}")
        print(f"   probe:   {probe}")

        while True:
            try:
                raw = input("   > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nstopped.")
                return 0
            if raw == "?":
                print(HELP)
                continue
            if raw == "q":
                print(f"\nstopped at {done} of {total}.")
                return 0
            if raw == "-" or raw == "":
                print()
                break
            letter, _, note = raw.partition(" ")
            if letter not in VALID:
                print(f"   want one of {sorted(VALID)}, or ? - q")
                continue
            lines[li] = f"label: {letter}"
            if note.strip():
                ni, _ = field(lines, span, "note")
                if ni is not None:
                    lines[ni] = f"note: {note.strip()}"
            args.labels.write_text("\n".join(lines) + "\n")
            done += 1
            print()
            break

    print(f"all {total} labelled. run: python3 validation/score.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
