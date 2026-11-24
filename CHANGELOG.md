# Changelog

## 0.2.0a2 — 2026-11-24

The matchers get measured, and one of them fails.

- 261 MQuAKE items labelled by hand against a stratified draw, in `validation/`. The strict rule's precision is **100%**, so the decision to build the headline on it holds. The derived-alias rule's was **57.1% [45.1, 69.0]** — it fired on a name reduced to a generic word ("country music" matching "a genre of music") and on the tail of somebody else's name ("Nicolae Ceausescu" when the edited subject was Elena).
- Both are fixed. On a **held-out** draw of 47 alias matches, disjoint from the labelled set and drawn after the fix was committed, the rule is right **90.2% [80.5, 97.6]**. Recall is unchanged.
- **Rates move, and `STRICT` rates do not.** Under 0.1.x the combined strict-plus-alias rate read 1.57% on MQuAKE-T and 67.79% on MQuAKE-CF-3k. Corrected, they are **0.82%** and **66.96%**. Strict alone was 0.37% and 65.41% before and after. A lower bound built on strict survived the correction; one built on strict plus alias did not, which is the argument for the headline being what it is.
- `screen_any` reports the strongest evidence rather than the numerically highest level, so a multi-edit verdict no longer depends on the order the edits arrive in.
- MQuAKE item ids are namespaced by source file. `case_id` restarts at 0 in each release, so `"1614:q1"` named a record in two different files.
- `MATCHER_VERSION` is `0.2.0`. **No rate from 0.1.x is comparable to one from this release.**

**Two known failure modes remain**, both found on the held-out set and left unfixed so that set stays usable: a given name shared with another person, and a brand two steps removed from the person it is named for. `validation/README.md` has both.

## 0.2.0a1 — 2026-11-23

MQuAKE, and the type change it forced.

- **Breaking.** `Item.edit` is now `Item.edits`, a tuple. Most MQuAKE cases edit two to four facts and then ask one question, so "does this probe identify the edited subject" has to become "does it identify ANY of them". Passing a bare `Edit` raises with instructions rather than failing obscurely.
- `screen_any(edits, probe)` flags the item if ANY edit matches, because a probe that names one of four edited subjects IS contaminated and reporting it clean would make the headline an under-count the caller cannot see. Where several match it reports the STRONGEST evidence, the lowest non-clean level. `screen(edit, probe)` is unchanged.
- The `Level` ladder is ordered by how far from the undeniable each level had to go, not by evidential strength. Reading it as strength made `screen_any` take the numeric maximum, which made its verdict depend on the order the edits arrived in — 36 of 9,000 MQuAKE-CF-3k items. The clean-vs-contaminated split was never affected and no recorded rate changes; the level was, and a level that moves when a list is reordered is not a measurement.
- MQuAKE adapter: `editscreen data.json --adapter mquake`. Reads all four released files — MQuAKE-CF, MQuAKE-CF-3k, its v2, MQuAKE-T — which share one record shape. Each of a case's three questions is screened separately; hop count is read off `orig.triples_labeled` rather than assumed, and is `None` rather than a guess when it cannot be read.
- Evidence on a multi-edit verdict names which edited subject fired.

`matcher_version` is `0.1.1`. The two matchers themselves are untouched, so every single-edit rate from 0.1.0a1 is reproduced exactly; the stamp moves because multi-edit screening no longer answers differently depending on input order.

- `validation/` now holds the machinery, though not yet the labels: `sample.py` draws a stratified sample across both MQuAKE variants and `score.py` reports precision and recall with bootstrap intervals, reweighted by the real stratum sizes. Its own README says what the set cannot establish, chiefly that recall on MQuAKE-T has a wide interval at any affordable sample size.

**Still not validated.** The labels are not filled in, so no measurement exists of how often the matchers are wrong, and no rate from this version should be quoted.

## 0.1.0a1 — 2026-11-23

First cut. The screen runs and its limits are stated.

- `screen(edit, probe)` returns a `Level`, not a boolean, with `Evidence` on every verdict including clean ones.
- `STRICT` (subject's own surface form) and `ALIAS` (name variant, supplied or derived) implemented. `IDENTIFIABLE` is not.
- `Report` stratifies by the benchmark's own declared test type, and returns item ids so a user can split their own results.
- `matcher_version` stamped on every report.
- Generic JSON adapter. No benchmark-specific adapters yet.
- Core has no dependencies outside the standard library; CI asserts it.

**Not validated.** No measurement exists of how often the matchers are wrong, so no rate from this version should be quoted.
