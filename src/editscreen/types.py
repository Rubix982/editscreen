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

    Ordered, and the order is the point: it runs by HOW FAR FROM THE
    UNDENIABLE a level had to go. STRICT assumes least and IDENTIFIABLE
    most, so the rate rises as you read down and STRICT is the lower
    bound everything else is quoted against.

    It is NOT an order of evidential strength, and reading it as one is
    what made `screen_any` order-dependent until 0.2. The levels are also
    mutually exclusive in practice rather than nested: alias is only
    asked where strict said no, and a mononym named in full is STRICT
    while deriving no variants for ALIAS to find.

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
    """One evaluation item: the edits in force, and a probe meant to test them.

    `edits` is a tuple, not a single edit, because benchmarks routinely
    change several facts at once and then ask one question. Most MQuAKE
    cases edit two to four facts. The question a screen answers there is
    *"does this probe identify ANY subject that was edited"*, and that
    cannot be asked of one edit at a time without changing its meaning.

    Single-edit items are the common case and stay easy to write: pass a
    one-tuple, and read it back through `edit`.
    """

    item_id: str
    edits: tuple[Edit, ...]
    probe: str
    # What the benchmark claims this item measures, verbatim from the
    # benchmark. Kept as the benchmark's own string rather than mapped
    # onto a vocabulary of ours, so a report can be checked against the
    # source file.
    test_type: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.edits, Edit):
            raise TypeError(
                f"item {self.item_id!r}: `edits` is a tuple of edits, not one "
                "Edit. Pass (edit,) for a single-edit item. This changed in "
                "0.2 so that multi-edit benchmarks could be screened at all."
            )
        if not self.edits:
            raise ValueError(
                f"item {self.item_id!r}: no edits. An item with nothing edited "
                "has no subject to screen for, so a verdict on it would be "
                "meaningless rather than clean."
            )

    @property
    def edit(self) -> Edit:
        """The single edit, for the common case.

        Raises when there is more than one, on purpose. Returning the
        first would let code written for single-edit data run silently
        against multi-edit data and under-report, which is the failure
        this whole package exists to catch.
        """
        if len(self.edits) != 1:
            raise ValueError(
                f"item {self.item_id!r} has {len(self.edits)} edits; `.edit` is "
                "only meaningful for one. Use `.edits`."
            )
        return self.edits[0]


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
