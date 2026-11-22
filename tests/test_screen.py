"""The behaviour that must not drift.

Several of these assert that the screen says CLEAN. Those matter most: a
matcher that over-fires turns the lower bound into a number people argue
with, which is the one thing this release is built to avoid.
"""

import pytest

from editscreen import Edit, Level, screen
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
            Item("a", Edit(subject="Henry Mackenzie"), "Henry Mackenzie was born", test_type="one-hop"),
            Item("b", Edit(subject="Henry Mackenzie"), "The capital of France is", test_type="two-hop"),
        ]
        r = screen_items(items)
        assert r.rate(Level.STRICT) == 0.5
        assert r.ids(Level.STRICT) == ("a",)
        assert r.ids(Level.STRICT, at_or_above=False) == ("b",)
        assert r.by_test_type()["one-hop"] == (1, 1, 1.0)

    def test_matcher_version_is_stamped(self):
        from editscreen import MATCHER_VERSION, screen_items
        assert screen_items([]).matcher_version == MATCHER_VERSION
