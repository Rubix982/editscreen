# Changelog

## 0.1.0.dev0 — unreleased

First cut. The screen runs and its limits are stated.

- `screen(edit, probe)` returns a `Level`, not a boolean, with `Evidence` on every verdict including clean ones.
- `STRICT` (subject's own surface form) and `ALIAS` (name variant, supplied or derived) implemented. `IDENTIFIABLE` is not.
- `Report` stratifies by the benchmark's own declared test type, and returns item ids so a user can split their own results.
- `matcher_version` stamped on every report.
- Generic JSON adapter. No benchmark-specific adapters yet.
- Core has no dependencies outside the standard library; CI asserts it.

**Not validated.** No measurement exists of how often the matchers are wrong, so no rate from this version should be quoted.
