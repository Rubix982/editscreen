"""The screen: the edits in force, one probe, one verdict."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import replace

from .matchers import alias, strict
from .types import Edit, Evidence, Item, Level, Verdict

# Bumped whenever a matcher's behaviour changes, and stamped onto every
# report. A contamination rate from one version is not comparable to one
# from another, and a number whose matcher cannot be identified is not
# reproducible — the same discipline as recording a seed.
MATCHER_VERSION = "0.2.0"


def screen(edit: Edit, probe: str) -> Verdict:
    """Does `probe` identify the subject `edit` changed?

    Returns the HIGHEST level that fires, with the evidence for it. The
    strict rule is tried first because it is the one that cannot be
    argued with; alias only gets asked when strict says no.
    """
    found = strict.check(probe, edit)
    if found is not None:
        return Verdict(level=Level.STRICT, evidence=(found,))

    found = alias.check(probe, edit)
    if found is not None:
        return Verdict(level=Level.ALIAS, evidence=(found,))

    return Verdict(
        level=Level.CLEAN,
        evidence=(Evidence(rule="clean", note="no surface form and no name variant found"),),
    )


def _strength(level: Level) -> tuple[bool, int]:
    """Sort key putting the strongest evidence first.

    CLEAN sorts last whatever its numeric value, because it is the absence
    of evidence rather than a weak kind of it. Among the rest, the ladder's
    own order applies: STRICT assumed least, so it wins.
    """
    return (level is Level.CLEAN, int(level))


def screen_any(edits: Sequence[Edit], probe: str) -> Verdict:
    """Does `probe` identify ANY of the subjects these edits changed?

    The item is contaminated if ANY edit matches: naming one of four
    edited subjects contaminates the item, and reporting it clean because
    the other three were absent would make the headline rate an
    under-count in a way the caller cannot see.

    Where several edits match, the verdict carries the STRONGEST evidence,
    which is the LOWEST non-clean level. The ladder is ordered by how far
    from the undeniable a level had to go — STRICT assumes least — so an
    item with one subject named outright and another caught by a surname
    is reported at STRICT, on the match nobody can argue with.

    Taking the numeric maximum instead made the verdict depend on the
    order the edits arrived in, which hit 36 of the 9,000 MQuAKE-CF-3k
    items. The CLEAN-vs-contaminated split was never affected; the level
    was, and a level that moves when a list is reordered is not a
    measurement.

    The winning evidence carries the subject that produced it, because
    with four edits in play "STRICT" alone does not say which one fired.
    """
    if not edits:
        raise ValueError("screen_any needs at least one edit")

    best = None
    for edit in edits:
        verdict = screen(edit, probe)
        if best is None or _strength(verdict.level) < _strength(best[0].level):
            best = (verdict, edit)
        if best[0].level is Level.STRICT:
            break  # the strongest evidence there is; stop looking

    verdict, edit = best
    if len(edits) == 1:
        return verdict

    note = f"matched the edit of {edit.subject!r}, of {len(edits)} edits in force"
    if verdict.level is Level.CLEAN:
        note = f"no surface form or name variant of any of {len(edits)} edited subjects"
    return Verdict(
        level=verdict.level,
        evidence=tuple(replace(e, note=note) for e in verdict.evidence),
    )


def screen_items(items: Iterable[Item]) -> "Report":
    from .report import Report

    return Report(
        rows=tuple((it, screen_any(it.edits, it.probe)) for it in items),
        matcher_version=MATCHER_VERSION,
    )
