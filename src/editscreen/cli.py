"""Command line entry point, because many users will never import anything."""

from __future__ import annotations

import argparse
import json
import sys

from . import adapters
from .report import Report
from .screen import screen_items
from .types import Level

ADAPTERS = {"generic": adapters.generic, "mquake": adapters.mquake}


def _emit_json(report: Report) -> str:
    return json.dumps(
        {
            "matcher_version": report.matcher_version,
            "n_items": len(report),
            "counts": {lv.name: n for lv, n in report.counts().items()},
            "rate_strict": report.rate(Level.STRICT),
            "rate_alias_or_above": report.rate(Level.ALIAS),
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

    try:
        report = screen_items(ADAPTERS[args.adapter].load(args.path))
    except (ValueError, OSError) as exc:
        print(f"editscreen: {exc}", file=sys.stderr)
        return 2

    print(_emit_json(report) if args.json else report.summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
