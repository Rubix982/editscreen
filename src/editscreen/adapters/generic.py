"""Load items from a plain JSON file of your own.

Built first, deliberately. A screen that only reads benchmarks it was
born knowing is not a tool anyone else can use, and when the generic path
is added last it ends up shaped by whichever benchmark came first.

The format is the smallest thing that can carry the question:

    [
      {
        "id": "q-001",
        "subject": "Henry Mackenzie",
        "probe": "Henry Mackenzie was born in the country of",
        "test_type": "two-hop",            # optional
        "aliases": ["The Man of Feeling"], # optional
        "relation": "birth_city",          # optional
        "object_new": "Rome"               # optional
      }
    ]

Only `subject` and `probe` are required. `id` is generated from position
when absent, and the generated form says so, because an id that looks
authoritative and was invented here would be a quiet kind of wrong.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

from ..types import Edit, Item

REQUIRED = ("subject", "probe")


def from_records(records: list[dict]) -> Iterator[Item]:
    for i, r in enumerate(records):
        missing = [k for k in REQUIRED if not r.get(k)]
        if missing:
            raise ValueError(
                f"record {i}: missing {', '.join(missing)}. "
                f"Every item needs a subject and a probe; got keys {sorted(r)}"
            )
        yield Item(
            item_id=str(r.get("id") or f"generated:{i}"),
            edit=Edit(
                subject=r["subject"],
                relation=r.get("relation"),
                object_new=r.get("object_new"),
                object_old=r.get("object_old"),
                aliases=tuple(r.get("aliases") or ()),
            ),
            probe=r["probe"],
            test_type=r.get("test_type"),
        )


def load(path: str | Path) -> Iterator[Item]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(
            f"{path}: expected a JSON list of records, got {type(data).__name__}. "
            "A benchmark in its own format needs its own adapter."
        )
    return from_records(data)
