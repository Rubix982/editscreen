"""Does a name variant of the subject occur, where the full form does not?

Two sources, kept apart because they have different error profiles.

  SUPPLIED  aliases the caller passed on the Edit. Trusted: if a caller
            says "Mark Twain" is "Samuel Clemens", that is their claim to
            make and the screen records it as theirs.

  DERIVED   variants this module generates from the subject string. These
            are guesses and they are wrong in predictable ways, listed on
            each generator below.

The derived rules are Western-name-shaped and will under-fire on names
that do not split into given and family parts in that order. That is a
real limitation of this release and it is in the README, not only here.
"""

from __future__ import annotations

from ..types import Edit, Evidence
from .strict import find

RULE_SUPPLIED = "alias.supplied"
RULE_DERIVED = "alias.derived"

# Dropped before a name is split. A surname match on "of" or "the" would
# fire on nearly every probe in every benchmark.
_PARTICLES = {"de", "van", "von", "del", "della", "di", "da", "la", "le",
              "of", "the", "bin", "ibn", "al", "el", "ter", "ten"}

# Too short to carry identity on their own. "Ng" is a real surname and a
# two-letter match is noise, so short parts are only used when the whole
# subject is that short.
_MIN_PART = 3


def derived_variants(subject: str) -> list[str]:
    """Name parts that plausibly stand in for the whole.

    Wrong when: the subject is a single mononym (returns nothing extra);
    a family name is also a common word ("Bush", "Rice") — those fire and
    are the main source of derived false positives; the name is given in
    family-first order, where this labels the parts backwards (harmless,
    since both parts are emitted either way).
    """
    parts = [p for p in subject.split() if p.lower() not in _PARTICLES]
    if len(parts) < 2:
        return []
    return [p for p in parts if len(p) >= _MIN_PART]


def check(probe: str, edit: Edit) -> Evidence | None:
    for a in edit.aliases:
        span = find(probe, a)
        if span is not None:
            return Evidence(rule=RULE_SUPPLIED, matched=probe[span[0]:span[1]],
                            span=span, note=f"caller-supplied alias {a!r}")
    for v in derived_variants(edit.subject):
        span = find(probe, v)
        if span is not None:
            return Evidence(rule=RULE_DERIVED, matched=probe[span[0]:span[1]],
                            span=span,
                            note=f"name part of {edit.subject!r}; derived, not supplied")
    return None
