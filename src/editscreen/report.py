"""What a screened dataset adds up to.

The report deliberately does NOT compute a corrected accuracy. It cannot:
it never sees the user's scores. What it does is hand back the item ids,
so the user can split their own already-computed results and find out for
themselves. Stating which items cannot test propagation is a claim this
screen can support; stating that someone's number was inflated is not.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

from .types import Item, Level, Verdict


@dataclass(frozen=True)
class Report:
    rows: tuple[tuple[Item, Verdict], ...]
    matcher_version: str

    def __len__(self) -> int:
        return len(self.rows)

    def rate(self, level: Level = Level.STRICT) -> float:
        """Fraction of items at or above `level`.

        Default is STRICT, which is the lower bound, because that is the
        number that should be quoted when only one number is quoted.
        """
        if not self.rows:
            return 0.0
        return sum(1 for _, v in self.rows if v.level >= level) / len(self.rows)

    def counts(self) -> dict[Level, int]:
        c = Counter(v.level for _, v in self.rows)
        return {lv: c.get(lv, 0) for lv in Level}

    def by_test_type(self, level: Level = Level.STRICT) -> dict[str, tuple[int, int, float]]:
        """(hits, total, rate) per test type the benchmark declares.

        Stratified because the claim is never "this benchmark is dirty" —
        it is that items of a particular declared type cannot measure what
        that type is named after.
        """
        buckets: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        for item, v in self.rows:
            b = buckets[item.test_type or "(unspecified)"]
            b[1] += 1
            if v.level >= level:
                b[0] += 1
        return {k: (h, n, h / n if n else 0.0) for k, (h, n) in sorted(buckets.items())}

    def ids(self, level: Level = Level.STRICT, *, at_or_above: bool = True) -> tuple[str, ...]:
        """Item ids on one side of `level` — the most useful thing here.

        `at_or_above=False` gives the clean items, which is the set a user
        wants when recomputing their own score on items that could have
        measured something.
        """
        return tuple(
            item.item_id
            for item, v in self.rows
            if (v.level >= level) is at_or_above
        )

    def summary(self) -> str:
        c = self.counts()
        lines = [
            f"editscreen {self.matcher_version} — {len(self)} items",
            "",
            f"  {'CLEAN':<14}{c[Level.CLEAN]:>7}",
            f"  {'STRICT':<14}{c[Level.STRICT]:>7}   subject's own surface form in the probe",
            f"  {'ALIAS':<14}{c[Level.ALIAS]:>7}   a name variant only",
            "",
            f"  contaminated at STRICT or above: {self.rate(Level.STRICT):.1%}",
            "",
            "  STRICT is a lower bound. Items naming the subject only by",
            "  description are not detected in this release.",
        ]
        by_type = self.by_test_type()
        if len(by_type) > 1:
            lines += ["", "  by declared test type:"]
            width = max(len(k) for k in by_type)
            lines += [f"    {k:<{width}}  {h:>5}/{n:<5} {r:>7.1%}"
                      for k, (h, n, r) in by_type.items()]
        return "\n".join(lines)
