# Changelog

## 0.2.0a1 — 2026-11-23

MQuAKE, and the type change it forced.

- **Breaking.** `Item.edit` is now `Item.edits`, a tuple. Most MQuAKE cases edit two to four facts and then ask one question, so "does this probe identify the edited subject" has to become "does it identify ANY of them". Passing a bare `Edit` raises with instructions rather than failing obscurely.
- `screen_any(edits, probe)` returns the highest level any edit reaches. Highest, because a probe that names one of four edited subjects IS contaminated, and reporting it clean would make the headline an under-count the caller cannot see. `screen(edit, probe)` is unchanged.
- MQuAKE adapter: `editscreen data.json --adapter mquake`. Reads all four released files — MQuAKE-CF, MQuAKE-CF-3k, its v2, MQuAKE-T — which share one record shape. Each of a case's three questions is screened separately; hop count is read off `orig.triples_labeled` rather than assumed, and is `None` rather than a guess when it cannot be read.
- Evidence on a multi-edit verdict names which edited subject fired.

Matcher behaviour is unchanged, so `matcher_version` stays `0.1.0` and rates from 0.1.0a1 remain comparable to these.

**Still not validated.** No measurement exists of how often the matchers are wrong, so no rate from this version should be quoted.

## 0.1.0a1 — 2026-11-23

First cut. The screen runs and its limits are stated.

- `screen(edit, probe)` returns a `Level`, not a boolean, with `Evidence` on every verdict including clean ones.
- `STRICT` (subject's own surface form) and `ALIAS` (name variant, supplied or derived) implemented. `IDENTIFIABLE` is not.
- `Report` stratifies by the benchmark's own declared test type, and returns item ids so a user can split their own results.
- `matcher_version` stamped on every report.
- Generic JSON adapter. No benchmark-specific adapters yet.
- Core has no dependencies outside the standard library; CI asserts it.

**Not validated.** No measurement exists of how often the matchers are wrong, so no rate from this version should be quoted.
