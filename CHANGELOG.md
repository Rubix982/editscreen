# Changelog

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
