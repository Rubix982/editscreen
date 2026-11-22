"""The screen: one edit, one probe, one verdict."""

from __future__ import annotations

from collections.abc import Iterable

from .matchers import alias, strict
from .types import Edit, Evidence, Item, Level, Verdict

# Bumped whenever a matcher's behaviour changes, and stamped onto every
# report. A contamination rate from one version is not comparable to one
# from another, and a number whose matcher cannot be identified is not
# reproducible — the same discipline as recording a seed.
MATCHER_VERSION = "0.1.0"


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


def screen_items(items: Iterable[Item]) -> "Report":
    from .report import Report

    return Report(
        rows=tuple((it, screen(it.edit, it.probe)) for it in items),
        matcher_version=MATCHER_VERSION,
    )
