"""Command line entry point, because many users will never import anything."""

from __future__ import annotations

import argparse
import json
import sys

from . import adapters
from .report import Report
from .screen import screen_items
from .types import Level

ADAPTERS = {"generic": adapters.generic, "mquake": adapters.mquake,
            "ripple": adapters.ripple}


def _emit_json(report: Report) -> str:
    return json.dumps(
        {
            "matcher_version": report.matcher_version,
            "n_items": len(report),
            "counts": {lv.name: n for lv, n in report.counts().items()},
            "rate_strict": report.rate(Level.STRICT),
            "rate_strict_or_alias": report.rate(Level.ALIAS),
            "by_test_type": {
                k: {"hits": h, "total": n, "rate": r}
                for k, (h, n, r) in report.by_test_type().items()
            },
            "contaminated_ids": list(report.ids(Level.STRICT)),
            "clean_ids": list(report.ids(Level.STRICT, at_or_above=False)),
        },
        indent=2,
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="editscreen",
        description="Does each evaluation probe identify the subject its edit changed?",
    )
    p.add_argument("path", help="dataset file")
    p.add_argument("--adapter", default="generic", choices=sorted(ADAPTERS),
                   help="source format (default: generic)")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    args = p.parse_args(argv)

    adapter = ADAPTERS[args.adapter]
    try:
        report = screen_items(adapter.load(args.path))
        # An adapter that cannot read every record says so here. Printing it
        # beside the rate is the point: a rate over the records an adapter
        # could read is a rate over part of the file, and a reader who is
        # not told that will take it for the whole.
        cover = adapter.coverage(args.path) if hasattr(adapter, "coverage") else None
    except (ValueError, OSError) as exc:
        print(f"editscreen: {exc}", file=sys.stderr)
        return 2

    if cover and cover["subject_recovered"] < cover["entries"]:
        skipped = cover["entries"] - cover["subject_recovered"]
        print(f"editscreen: {skipped:,} of {cover['entries']:,} entries skipped "
              f"({cover['rate']:.1%} readable) — every rate below is over the "
              f"rest. See `coverage()`.", file=sys.stderr)

    print(_emit_json(report) if args.json else report.summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
