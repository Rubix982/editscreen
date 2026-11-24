"""The behaviour that must not drift.

Several of these assert that the screen says CLEAN. Those matter most: a
matcher that over-fires turns the lower bound into a number people argue
with, which is the one thing this release is built to avoid.
"""

import pytest

from editscreen import Edit, Item, Level, screen, screen_any
from editscreen.adapters import mquake
from editscreen.matchers.alias import derived_variants


def lvl(subject, probe, **kw):
    return screen(Edit(subject=subject, **kw), probe).level


class TestStrict:
    def test_full_name_present(self):
        assert lvl("Henry Mackenzie", "Henry Mackenzie was born in") is Level.STRICT

    def test_case_and_accents_do_not_hide_it(self):
        assert lvl("Antonín Dvořák", "ANTONIN DVORAK composed") is Level.STRICT

    def test_substring_of_a_longer_word_is_not_a_match(self):
        # "Ann" inside "announced" is the classic false positive.
        assert lvl("Ann", "The committee announced a decision") is Level.CLEAN

    def test_punctuation_adjacent_still_matches(self):
        assert lvl("Henry Mackenzie", "Who was Henry Mackenzie?") is Level.STRICT


class TestAlias:
    def test_surname_alone(self):
        assert lvl("Henry Mackenzie", "Mackenzie was born in") is Level.ALIAS

    def test_given_name_alone(self):
        assert lvl("Henry Mackenzie", "Henry was born in") is Level.ALIAS

    def test_supplied_alias(self):
        assert lvl("Samuel Clemens", "Mark Twain wrote", aliases=("Mark Twain",)) is Level.ALIAS

    def test_particles_never_fire_alone(self):
        # "van" matching would contaminate essentially every probe.
        assert lvl("Vincent van Gogh", "The van drove away") is Level.CLEAN

    def test_mononym_has_no_derived_variants(self):
        assert derived_variants("Aristotle") == []

    def test_short_parts_are_not_used(self):
        assert "Ng" not in derived_variants("Ng Wai")


class TestClean:
    def test_unrelated_probe(self):
        assert lvl("Henry Mackenzie", "The capital of France is") is Level.CLEAN

    def test_description_without_a_name_is_not_detected(self):
        # Documented miss, not a bug: this is what IDENTIFIABLE is for.
        # The test exists so the day it starts passing is a deliberate one.
        assert lvl("Henry Mackenzie",
                   "The author of The Man of Feeling was born in") is Level.CLEAN


class TestEvidence:
    def test_every_verdict_carries_evidence(self):
        for probe in ("Henry Mackenzie was born", "Mackenzie was born", "Paris is"):
            v = screen(Edit(subject="Henry Mackenzie"), probe)
            assert v.evidence and v.evidence[0].rule

    def test_span_indexes_into_the_original_probe(self):
        probe = "Who was ANTONIN DVORAK, really?"
        v = screen(Edit(subject="Antonín Dvořák"), probe)
        start, end = v.evidence[0].span
        assert probe[start:end] == "ANTONIN DVORAK"


class TestReport:
    def test_rate_and_ids_agree(self):
        from editscreen import Item, screen_items
        items = [
            Item("a", (Edit(subject="Henry Mackenzie"),), "Henry Mackenzie was born", test_type="one-hop"),
            Item("b", (Edit(subject="Henry Mackenzie"),), "The capital of France is", test_type="two-hop"),
        ]
        r = screen_items(items)
        assert r.rate(Level.STRICT) == 0.5
        assert r.ids(Level.STRICT) == ("a",)
        assert r.ids(Level.STRICT, at_or_above=False) == ("b",)
        assert r.by_test_type()["one-hop"] == (1, 1, 1.0)

    def test_matcher_version_is_stamped(self):
        from editscreen import MATCHER_VERSION, screen_items
        assert screen_items([]).matcher_version == MATCHER_VERSION


class TestMultipleEdits:
    """A probe is contaminated if it names ANY edited subject."""

    def test_highest_level_across_edits_wins(self):
        from editscreen.screen import screen_any
        edits = (Edit(subject="Marie Curie"), Edit(subject="Ellie Kemper"))
        v = screen_any(edits, "Who is the head of state of the country where Ellie Kemper lives?")
        assert v.level is Level.STRICT

    def test_clean_only_when_no_edit_matches(self):
        from editscreen.screen import screen_any
        edits = (Edit(subject="Marie Curie"), Edit(subject="United States of America"))
        v = screen_any(edits, "What is the capital of the country Michael Feinstein belongs to?")
        assert v.level is Level.CLEAN

    def test_evidence_names_which_edit_fired(self):
        from editscreen.screen import screen_any
        edits = (Edit(subject="Marie Curie"), Edit(subject="Ellie Kemper"))
        v = screen_any(edits, "Where does Ellie Kemper live?")
        assert "Ellie Kemper" in v.evidence[0].note

    def test_an_item_needs_at_least_one_edit(self):
        with pytest.raises(ValueError):
            Item("x", (), "a probe")

    def test_passing_a_bare_edit_says_what_to_do(self):
        with pytest.raises(TypeError, match=r"tuple of edits"):
            Item("x", Edit(subject="Marie Curie"), "a probe")


class TestMQuAKEAdapter:
    def _case(self, **over):
        case = {
            "case_id": 1,
            "requested_rewrite": [
                {"subject": "Ellie Kemper", "relation_id": "P27",
                 "target_new": {"str": "Croatia"},
                 "target_true": {"str": "United States of America"}}
            ],
            "questions": ["Where is Ellie Kemper a citizen?", "Ellie Kemper's country?"],
            "orig": {"triples_labeled": [["a", "r", "b"], ["b", "r", "c"]]},
        }
        case.update(over)
        return case

    def test_every_question_becomes_its_own_item(self):
        items = list(mquake.from_records([self._case()]))
        assert [i.item_id for i in items] == ["1:q0", "1:q1"]

    def test_hop_count_is_read_off_the_chain(self):
        items = list(mquake.from_records([self._case()]))
        assert items[0].test_type == "2-hop"

    def test_every_rewrite_becomes_an_edit(self):
        case = self._case(requested_rewrite=[
            {"subject": "Ellie Kemper", "target_new": {"str": "Croatia"}},
            {"subject": "Marie Curie", "target_new": {"str": "Peru"}},
        ])
        items = list(mquake.from_records([case]))
        assert [e.subject for e in items[0].edits] == ["Ellie Kemper", "Marie Curie"]

    def test_unreadable_hop_count_is_none_not_a_guess(self):
        items = list(mquake.from_records([self._case(orig={})]))
        assert items[0].test_type is None

    def test_a_case_without_rewrites_is_an_error_not_a_clean_verdict(self):
        with pytest.raises(ValueError, match="requested_rewrite"):
            list(mquake.from_records([self._case(requested_rewrite=[])]))


class TestVerdictDoesNotDependOnEditOrder:
    """36 of 9,000 MQuAKE-CF-3k items had one subject named outright and
    another caught only by a surname. Which level came back depended on
    which edit the adapter happened to emit first."""

    named = Edit(subject="Henry Mackenzie")
    surname_only = Edit(subject="Jane Austen")
    probe = "Who wrote the novel by Henry Mackenzie that Austen admired?"

    def test_same_verdict_either_way_round(self):
        a = screen_any([self.named, self.surname_only], self.probe)
        b = screen_any([self.surname_only, self.named], self.probe)
        assert a.level is b.level

    def test_reports_the_undeniable_match(self):
        """STRICT, not ALIAS: the point of a verdict is the best evidence
        behind it, and a full surface form cannot be argued with."""
        for edits in ([self.named, self.surname_only],
                      [self.surname_only, self.named]):
            assert screen_any(edits, self.probe).level is Level.STRICT

    def test_alias_still_wins_over_clean(self):
        absent = Edit(subject="Mary Shelley")
        for edits in ([absent, self.surname_only], [self.surname_only, absent]):
            assert screen_any(edits, self.probe).level is Level.ALIAS


class TestItemIdsDoNotCollideAcrossFiles:
    """MQuAKE's case_id restarts at 0 in each released file, so a bare
    "1614:q1" names one record in MQuAKE-T and another in MQuAKE-CF-3k."""

    case = {"case_id": 1614,
            "requested_rewrite": [{"subject": "Shelagh Delaney"}],
            "questions": ["Who wrote it?"]}

    def test_load_prefixes_with_the_file_stem(self, tmp_path):
        import json
        ids = []
        for name in ("MQuAKE-T", "MQuAKE-CF-3k"):
            p = tmp_path / f"{name}.json"
            p.write_text(json.dumps([self.case]))
            ids += [it.item_id for it in mquake.load(p)]
        assert ids == ["MQuAKE-T:1614:q0", "MQuAKE-CF-3k:1614:q0"]
        assert len(set(ids)) == len(ids)

    def test_bare_records_keep_the_unprefixed_form(self):
        ids = [it.item_id for it in mquake.from_records([self.case])]
        assert ids == ["1614:q0"]
