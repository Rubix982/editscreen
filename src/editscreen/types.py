"""The objects a screen is stated in terms of.

Named in English before they take a symbol, because a reader who meets
`Level.ALIAS` in a report needs to know what it asserts without reading
the matcher that produced it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class Level(IntEnum):
    """How strongly an evaluation item identifies the edited subject.

    Ordered, and the order is the point: a higher level is a stronger
    claim that the item is contaminated, and every level above CLEAN
    implies the levels below it would also have fired if asked.

    CLEAN         nothing in the probe points at the edited subject.
    STRICT        the subject's own surface form occurs in the probe.
    ALIAS         a known or derived name variant occurs — a surname on
                  its own, a given name, a supplied alias.
    IDENTIFIABLE  no name occurs, but a description in the probe picks the
                  subject out anyway. Not implemented in 0.1; it needs a
                  knowledge base or a model, so it ships as an optional
                  extra and is never folded into the headline rate.
    """

    CLEAN = 0
    STRICT = 1
    ALIAS = 2
    IDENTIFIABLE = 3


@dataclass(frozen=True)
class Edit:
    """A knowledge edit, described without reference to how it was written.

    Nothing here names ROME, MEMIT, fine-tuning or any other mechanism,
    because contamination is a property of how the evaluation item was
    written and not of how the weights were changed.
    """

    subject: str
    relation: str | None = None
    object_new: str | None = None
    object_old: str | None = None
    # Aliases the caller knows about. The screen derives common variants
    # itself; this is for the ones it cannot derive, such as pen names.
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class Item:
    """One evaluation item: an edit, and a probe meant to test it."""

    item_id: str
    edit: Edit
    probe: str
    # What the benchmark claims this item measures, verbatim from the
    # benchmark. Kept as the benchmark's own string rather than mapped
    # onto a vocabulary of ours, so a report can be checked against the
    # source file.
    test_type: str | None = None


@dataclass(frozen=True)
class Evidence:
    """Why a verdict came out the way it did.

    Present on every verdict, including CLEAN ones. The first thing a
    skeptical reader does is spot-check ten decisions, and a screen that
    cannot say *why* is one they are right to discard.
    """

    rule: str
    matched: str | None = None
    span: tuple[int, int] | None = None
    note: str | None = None


@dataclass(frozen=True)
class Verdict:
    level: Level
    evidence: tuple[Evidence, ...] = field(default_factory=tuple)

    @property
    def contaminated(self) -> bool:
        """True above CLEAN.

        A convenience, and a lossy one: it throws away which level fired,
        which is the part worth reporting. Prefer `verdict.level`.
        """
        return self.level > Level.CLEAN
