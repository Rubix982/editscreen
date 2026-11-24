"""Load items from MQuAKE, in the format the authors released.

MQuAKE asks multi-hop questions about facts it has edited, so it is the
benchmark where the question this package screens for matters most: if a
multi-hop question names the edited subject outright, the hop structure
the item was built to test may never be exercised.

Four files ship under this name — MQuAKE-CF, MQuAKE-CF-3k, its v2, and
MQuAKE-T — and all four share one record shape, so there is no per-file
special case here. Checked against all four.

What this adapter reads, and what it ignores:

    case_id             -> the item id, with the question's position
    requested_rewrite[] -> ALL of them become edits. Most cases edit two
                           to four facts; only MQuAKE-T is uniformly
                           single-edit.
    questions[]         -> the probes. Three per case, paraphrases of one
                           multi-hop question. Each is screened on its own
                           because each is a separate thing a model is
                           asked, and a paraphrase can name the subject
                           when its siblings do not.
    orig.triples_labeled-> the hop count, as `test_type`: "2-hop" and so
                           on. Read off the chain rather than assumed, so
                           the stratification in a report can be checked
                           against the source file.

`single_hops`, `new_single_hops`, the answers and their aliases are not
read. The answers describe what a correct response looks like; this
package never sees responses.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

from ..types import Edit, Item


def _edits(case: dict, where: str) -> tuple[Edit, ...]:
    rewrites = case.get("requested_rewrite")
    if not isinstance(rewrites, list) or not rewrites:
        raise ValueError(
            f"{where}: no requested_rewrite. Without it there is no edited "
            f"subject to screen for; got keys {sorted(case)}"
        )
    out = []
    for j, rw in enumerate(rewrites):
        subject = (rw or {}).get("subject")
        if not subject:
            raise ValueError(f"{where}: requested_rewrite[{j}] has no subject")
        out.append(
            Edit(
                subject=subject,
                relation=rw.get("relation_id"),
                object_new=(rw.get("target_new") or {}).get("str"),
                object_old=(rw.get("target_true") or {}).get("str"),
            )
        )
    return tuple(out)


def _test_type(case: dict) -> str | None:
    """Hop count from the labelled chain, or None.

    None rather than a guess. An item whose hop count cannot be read is
    reported under no stratum at all, which is visible in a report; a
    guessed "2-hop" would not be.
    """
    chain = (case.get("orig") or {}).get("triples_labeled")
    if isinstance(chain, list) and chain:
        return f"{len(chain)}-hop"
    return None


def from_records(records: list[dict], source: str | None = None) -> Iterator[Item]:
    """Screenable items, one per question.

    `source` prefixes every item id. MQuAKE's `case_id` restarts at 0 in
    each released file, so "1614:q1" names a record in MQuAKE-T and a
    different one in MQuAKE-CF-3k. `load` passes the file's stem, and a
    caller joining a report back to their own data gets ids that cannot
    collide. Omitting it keeps the bare form for a caller who has already
    namespaced the records themselves.
    """
    prefix = f"{source}:" if source else ""
    for i, case in enumerate(records):
        case_id = case.get("case_id", f"index:{i}")
        where = f"case {case_id}"
        edits = _edits(case, where)
        test_type = _test_type(case)

        questions = case.get("questions")
        if not isinstance(questions, list) or not questions:
            raise ValueError(f"{where}: no questions to screen")

        for q, question in enumerate(questions):
            if not isinstance(question, str) or not question.strip():
                raise ValueError(f"{where}: questions[{q}] is not a usable string")
            yield Item(
                item_id=f"{prefix}{case_id}:q{q}",
                edits=edits,
                probe=question,
                test_type=test_type,
            )


def load(path: str | Path) -> Iterator[Item]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(
            f"{path}: expected a JSON list of MQuAKE cases, got "
            f"{type(data).__name__}"
        )
    if data and "requested_rewrite" not in (data[0] or {}):
        raise ValueError(
            f"{path}: this does not look like MQuAKE — the first record has no "
            f"requested_rewrite (keys: {sorted(data[0] or {})}). Use --adapter "
            "generic for your own format."
        )
    return from_records(data, source=Path(path).stem)
