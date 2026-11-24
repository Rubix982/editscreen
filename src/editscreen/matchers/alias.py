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

import re

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

# Words that name a KIND of thing rather than a particular one. Dropping a
# name to one of these does not leave anything that identifies the subject:
# "country music" reduced to "music" matches "a genre of music", and
# "Ford Motor Company" reduced to "Company" matches nothing anyone meant.
#
# Measured on 261 hand-checked MQuAKE items: the `country`/`music` family
# alone accounted for six of the derived rule's false positives, more than
# any other single cause. The list is deliberately short and literal. It
# holds words that are generic IN EVERY SENSE, so `football` is absent —
# in "Germany national football team" it really does name the sport.
_GENERIC = {
    # legal and organisational forms
    "inc", "inc.", "incorporated", "corp", "corp.", "corporation", "company",
    "co", "co.", "ltd", "ltd.", "limited", "llc", "plc", "gmbh", "ag", "sa",
    "group", "holdings", "partners", "associates", "systems", "technologies",
    "industries", "enterprises", "international", "worldwide", "global",
    # institutions
    "foundation", "institute", "association", "federation", "union",
    "society", "council", "committee", "authority", "agency", "bureau",
    "department", "ministry", "office", "center", "centre", "museum",
    "library", "university", "college", "school", "academy", "hospital",
    # media and product lines
    "press", "publishing", "publications", "media", "entertainment",
    "pictures", "studios", "studio", "films", "records", "productions",
    "production", "network", "broadcasting", "television", "radio",
    "magazine", "journal", "music", "cars", "motors", "motor", "automotive",
    "airlines", "airways", "railways", "bank", "insurance", "capital",
    "ventures", "club", "league", "team", "championship",
    # kinds of place, thing and category
    "country", "city", "state", "states", "republic", "kingdom", "province",
    "region", "district", "county", "town", "village", "sport", "sports",
    "game", "games", "language", "religion", "party", "movement",
    "national", "united", "new", "north", "south", "east", "west", "central",
}

# A capitalised word sitting immediately in front of a match is usually the
# rest of SOMEONE ELSE'S name: "Nicolae Ceausescu" when the edited subject
# is Elena, "Jada Pinkett Smith" when it is Will, "El Salvador" when it is
# San Salvador. Five of the derived rule's false positives were this.
#
# It is only applied when the subject itself reads as a proper name — every
# part capitalised. "association football" is not one, so "Football" inside
# "Italian Football Federation" is still a match, which it should be.
_SENTENCE_END = ".!?\u061f\u06d4"


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
    return [p for p in parts
            if len(p) >= _MIN_PART and p.lower().strip(".") not in _GENERIC]


def _looks_like_a_proper_name(subject: str) -> bool:
    """Every part capitalised, so the subject is a name rather than a phrase.

    "Elena Ceausescu" and "San Salvador" are; "association football" and
    "country music" are not. Only the first kind gets the neighbour check
    below, because only a name can have somebody else's name built on it.
    """
    parts = [p for p in subject.split() if p.lower() not in _PARTICLES]
    return len(parts) >= 2 and all(p[:1].isupper() for p in parts if p)


def _belongs_to_another_name(probe: str, start: int, subject: str) -> str | None:
    """The capitalised word right before the match, when it is not the
    subject's own. Returns it, so the caller can say why it declined."""
    before = probe[:start]
    m = re.search(r"([^\W\d_]+)[^\w]*$", before)
    if m is None:
        return None
    word = m.group(1)
    if not word[:1].isupper():
        return None
    # A capital at the start of a sentence says nothing about names.
    lead = before[:m.start(1)].rstrip()
    if not lead or lead[-1] in _SENTENCE_END:
        return None
    if word.casefold() in {p.casefold() for p in subject.split()}:
        return None
    return word


def check(probe: str, edit: Edit) -> Evidence | None:
    for a in edit.aliases:
        span = find(probe, a)
        if span is not None:
            return Evidence(rule=RULE_SUPPLIED, matched=probe[span[0]:span[1]],
                            span=span, note=f"caller-supplied alias {a!r}")
    guard = _looks_like_a_proper_name(edit.subject)
    for v in derived_variants(edit.subject):
        span = find(probe, v)
        if span is None:
            continue
        if guard:
            other = _belongs_to_another_name(probe, span[0], edit.subject)
            if other is not None:
                continue  # the match is the tail of someone else's name
        return Evidence(rule=RULE_DERIVED, matched=probe[span[0]:span[1]],
                        span=span,
                        note=f"name part of {edit.subject!r}; derived, not supplied")
    return None
