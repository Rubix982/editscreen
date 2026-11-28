"""RippleEdits (Cohen et al., TACL 2024), read without a knowledge base.

    editscreen recent.json --adapter ripple

THE PROBLEM THIS FILE SOLVES, and it is the only hard part.

RippleEdits names its subject by Wikidata QID. The edit record says
`subject_id: "Q109315250"` and the edit prompt reads

    "The name of the field of work of  is photography."

with the subject's slot left empty. Screening needs a STRING to look for,
and resolving a QID means a knowledge base, a network call and a
dependency this package has promised not to take.

It is not needed. The corpus materialises the subject in its own test
prompts — "The place of birth of Leo Arons is" — so the label can be read
back out of the entry that needs it. Measured over the three released
subsets, this recovers a label for **80.3% of entries**: 75.0% on
`recent`, 85.0% on `random`, 81.8% on `popular`.

Report that per subset and never pooled. The subsets differ by ten points
because they are built from different slices of Wikidata, and a single
80.3% describes no file anybody can download.

WHAT HAPPENS TO THE OTHER FIFTH. The entry is skipped, every one of its
queries with it, and `coverage()` says how many. Emitting them with an
unrecoverable subject would report them CLEAN, and a false clean is the
one error this package exists to prevent — it would silently lower the
very rate being measured.

WHY IT IS 80% AND NOT MORE. Each pattern takes the LEFTMOST " of " and
rejects a capture that does not start with a capital, so

    "The place of birth of Leo Arons is"

yields nothing: it captures "birth of Leo Arons". Retrying at later " of "
positions would recover some of the missing fifth. It is not done here,
because the 80.3% figure and the [R-013] measurement behind it were taken
with this behaviour, and a silently better number would not be comparable
to either. Change it deliberately or not at all.

A NOTE ON THE EMPTY SLOT. Some released prompts keep the subject's slot
blank, as the edit prompt above does. Those really do not name the
subject and are really CLEAN; that is the corpus, not a failure here. It
is rarer than it looks from reading the first record — 1,004 of 46,754
test prompts, 2.1%.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from pathlib import Path

from ..types import Edit, Item

# The six test criteria RippleEdits declares. Each becomes a test type on
# the items it produces, so a report stratifies by the benchmark's own
# vocabulary rather than by anything invented here.
CRITERIA = (
    "Logical_Generalization",
    "Compositionality_I",
    "Compositionality_II",
    "Subject_Aliasing",
    "Relation_Specificity",
    "Forgetfulness",
)

# The shapes a materialised subject takes in this corpus, lifted from the
# [R-013] measurement that counted them. Anchored at the end, or followed
# by a clause marker, because an unanchored ".+?" swallows the relation.
PATTERNS = (
    r" of (.+?) is$",
    r" of (.+?) are$",
    r"^Is (.+?) still alive\?$",
    r" of (.+?), which",
    r" which (.+?) is associated",
)


#: A relative clause is prompt text, never part of a name. RippleEdits writes
#: negated attributes inline -- "Dakhovskaya, which is not Russian, is ..." --
#: and the pattern ` which (.+?) is associated` captures the clause along with
#: the subject. `subject_label` then prefers that string precisely BECAUSE the
#: clause makes it the longest, so longest-wins selects the damaged form over
#: the clean one sitting beside it in the same candidate set.
#:
#: Measured over the three released files: the longest candidate carries a
#: clause for **577 of 3,818 entries (15.1%)** -- 95 recent, 387 random, 95
#: popular. It is trimmed rather than rejected: rejecting would lose entries
#: whose only candidate carries one, and this function's docstring records that
#: taking a worse candidate once left 17,206 prompts unclassifiable.
_CLAUSE = re.compile(r",\s+which\b")

#: Bumped whenever the recovered string can change for the same input. Rates
#: taken under different values are NOT comparable, and the matcher version does
#: not capture this because the matchers are untouched.
RECOVERY_VERSION = "0.3.0"


def candidates(entry: dict) -> list[str]:
    """Every subject-shaped string this entry's own prompts offer.

    SORTED, and that is not cosmetic. `max` over a set is nondeterministic
    when two candidates tie on length, and two runs of the original
    measurement differed by 15 prompts because of it. A rate that changes
    between runs is not a rate.
    """
    found: set[str] = set()
    for criterion in CRITERIA:
        for group in entry.get(criterion) or []:
            for query in (group or {}).get("test_queries") or []:
                prompt = (query or {}).get("prompt")
                if not isinstance(prompt, str):
                    continue
                for pattern in PATTERNS:
                    m = re.search(pattern, prompt)
                    if m and m.group(1) and m.group(1)[0].isupper():
                        # Trim before adding, so the clean form and the
                        # clause-laden one collapse to one candidate instead of
                        # competing on length.
                        cand = _CLAUSE.split(m.group(1).strip(), 1)[0]
                        cand = cand.strip().rstrip(",").strip()
                        if cand:
                            found.add(cand)
    return sorted(found)


def subject_label(entry: dict) -> str | None:
    """The longest candidate, or None.

    Longest because an entry carries its subject in several shapes — "Leo
    Arons" and "Martin Leo Arons" — and the longest is the likeliest to be
    the full name. Taking the first instead left 17,206 prompts
    unclassifiable, more than a third of the corpus, which is not a
    measurement. A prompt carrying only the shorter form is still caught,
    because the shorter forms are passed on as aliases.
    """
    cands = candidates(entry)
    return max(cands, key=len) if cands else None


def _edit(entry: dict) -> Edit | None:
    subject = subject_label(entry)
    if subject is None:
        return None
    others = tuple(c for c in candidates(entry) if c != subject)
    return Edit(
        subject=subject,
        relation=(entry.get("edit") or {}).get("relation"),
        # The edit's target is a QID and its label is not in the record,
        # so there is nothing honest to put here. The screen does not use
        # it; it is on Edit for callers whose data has it.
        object_new=None,
        # Shorter surface forms of the same subject, read out of this
        # entry's own prompts. They are the corpus's own aliases, which is
        # what Subject_Aliasing is built from — but they are produced by
        # the patterns above and inherit whatever those get wrong.
        aliases=others,
    )


def from_records(records: list[dict], source: str | None = None) -> Iterator[Item]:
    """One item per test query, for entries whose subject could be read."""
    prefix = f"{source}:" if source else ""
    for i, entry in enumerate(records):
        edit = _edit(entry)
        if edit is None:
            continue
        for criterion in CRITERIA:
            for g, group in enumerate(entry.get(criterion) or []):
                for q, query in enumerate((group or {}).get("test_queries") or []):
                    prompt = (query or {}).get("prompt")
                    if not isinstance(prompt, str) or not prompt.strip():
                        continue
                    yield Item(
                        item_id=f"{prefix}{i}:{criterion}:{g}:{q}",
                        edits=(edit,),
                        probe=prompt,
                        test_type=criterion,
                    )


def coverage(path: str | Path) -> dict:
    """How much of a file could be screened at all.

    Quote this beside any rate from this adapter. A rate computed over the
    80% whose subject was recoverable is a rate over 80% of the file, and
    saying so is the difference between a measurement and a claim about a
    benchmark.
    """
    records = _records(path)
    readable = sum(1 for e in records if subject_label(e) is not None)
    return {
        "file": Path(path).name,
        "subset": (records[0].get("example_type") if records else None),
        "entries": len(records),
        "subject_recovered": readable,
        "rate": round(readable / len(records), 4) if records else 0.0,
        "note": "entries whose subject label could not be read are skipped "
                "entirely; reporting them would mean reporting them CLEAN",
    }


def _records(path: str | Path) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(
            f"{path}: expected a JSON list of RippleEdits entries, got "
            f"{type(data).__name__}"
        )
    if data and "edit" not in (data[0] or {}):
        raise ValueError(
            f"{path}: this does not look like RippleEdits — the first record "
            f"has no `edit` (keys: {sorted(data[0] or {})}). Use --adapter "
            "generic for your own format."
        )
    return data


def load(path: str | Path) -> Iterator[Item]:
    return from_records(_records(path), source=Path(path).stem)
