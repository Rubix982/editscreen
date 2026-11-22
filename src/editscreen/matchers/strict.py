"""Does the subject's own surface form occur in the probe?

The weakest claim the screen makes, and the one nobody can dispute. Its
rate is a LOWER BOUND on contamination: everything it finds is really
there, and it misses every item that names the subject some other way.
That asymmetry is why the headline number is built on this rule.

Known misses, stated rather than discovered later:
  - "Mackenzie" alone, when the subject is "Henry Mackenzie"  -> ALIAS
  - "The author of The Man of Feeling"                        -> IDENTIFIABLE
  - "he", after the subject is named in an earlier turn       -> neither
"""

from __future__ import annotations

import re
import unicodedata

from ..types import Edit, Evidence

RULE = "strict.surface_form"


def normalise(text: str) -> str:
    """Casefold and strip accents, so Dvorak matches Dvořák.

    Deliberately does NOT strip punctuation or collapse whitespace: the
    span this returns has to index back into the caller's own string, and
    a normalisation that changes length makes that a lie.
    """
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    # NFKD can expand a character into several; only accept the rewrite
    # when offsets are preserved, otherwise fall back to the original.
    if len(stripped) != len(text):
        return text.casefold()
    return stripped.casefold()


def find(probe: str, needle: str) -> tuple[int, int] | None:
    """Locate `needle` in `probe` on word boundaries.

    Word boundaries matter: without them "Ann" matches inside "Announce"
    and the screen reports contamination that is not there. A false
    positive costs more here than a false negative, because the whole
    value of the strict level is that its findings are not arguable.
    """
    if not needle.strip():
        return None
    pattern = r"(?<!\w)" + re.escape(normalise(needle)) + r"(?!\w)"
    m = re.search(pattern, normalise(probe))
    return (m.start(), m.end()) if m else None


def check(probe: str, edit: Edit) -> Evidence | None:
    span = find(probe, edit.subject)
    if span is None:
        return None
    return Evidence(rule=RULE, matched=probe[span[0]:span[1]], span=span)
