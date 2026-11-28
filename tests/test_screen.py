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


class TestRateIsCumulativeTowardTheLooserRule:
    """The ladder runs by how far from the undeniable a level had to go, so
    a rate GROWS as the level loosens. Written against the enum's integer
    order it meant the opposite, and shipped a field called `rate_strict`
    holding every non-clean item."""

    def _report(self):
        from editscreen.report import Report
        from editscreen.types import Evidence, Verdict
        rows = []
        # two strict, one alias, one clean
        for i, lv in enumerate([Level.STRICT, Level.STRICT, Level.ALIAS, Level.CLEAN]):
            item = Item(item_id=str(i), edits=(Edit(subject="x"),), probe="p")
            rows.append((item, Verdict(level=lv, evidence=(Evidence(rule="t"),))))
        return Report(rows=tuple(rows), matcher_version="test")

    def test_strict_rate_counts_only_strict(self):
        assert self._report().rate(Level.STRICT) == 0.5

    def test_alias_rate_adds_strict_to_alias(self):
        assert self._report().rate(Level.ALIAS) == 0.75

    def test_clean_is_never_counted(self):
        r = self._report()
        assert r.rate(Level.IDENTIFIABLE) == 0.75

    def test_ids_split_on_the_same_rule(self):
        r = self._report()
        assert r.ids(Level.STRICT) == ("0", "1")
        assert set(r.ids(Level.STRICT, at_or_above=False)) == {"2", "3"}


class TestRippleAdapter:
    """Prompt shapes are real ones from `random.json`, not invented. The
    patterns take the LEFTMOST " of " and reject a lowercase capture, so
    "The place of birth of Leo Arons is" yields nothing — it captures
    "birth of Leo Arons". That is why coverage is 80% and not higher, and
    it is kept because changing it changes the recorded figure."""

    entry = {
        "example_type": "random",
        "edit": {"subject_id": "Q42", "relation": "COUNTRY",
                 "prompt": "The name of the field of work of  is photography."},
        "Relation_Specificity": [{"test_queries": [
            {"prompt": "The official language of Goursez Vreizh is"},
            {"prompt": "The name of the country which Gorsedd of Brittany "
                       "is associated with is"},
        ]}],
        "Subject_Aliasing": [{"test_queries": [
            {"prompt": "The name of the country which  is associated with is"},
        ]}],
    }

    def test_subject_is_the_longest_candidate(self):
        from editscreen.adapters import ripple
        assert ripple.subject_label(self.entry) == "Gorsedd of Brittany"

    def test_shorter_forms_become_aliases(self):
        from editscreen.adapters import ripple
        item = next(iter(ripple.from_records([self.entry])))
        assert item.edit.aliases == ("Goursez Vreizh",)

    def test_candidates_are_sorted_so_ties_do_not_wobble(self):
        """`max` over a set is nondeterministic on a length tie, and two runs
        of the original measurement once differed by 15 prompts."""
        from editscreen.adapters import ripple
        got = ripple.candidates(self.entry)
        assert got == sorted(got)

    def test_a_prompt_naming_an_alias_is_still_caught(self):
        """The subject is the longest form; a prompt carrying a shorter one
        is reached through the aliases, which is why they are passed on."""
        from editscreen.adapters import ripple
        items = list(ripple.from_records([self.entry]))
        by_probe = {it.probe: it for it in items}
        short = by_probe["The official language of Goursez Vreizh is"]
        assert screen_any(short.edits, short.probe).level is Level.ALIAS

    def test_an_entry_with_no_recoverable_subject_is_skipped(self):
        from editscreen.adapters import ripple
        blank = {"edit": {"subject_id": "Q1"}, "Relation_Specificity": [
            {"test_queries": [{"prompt": "The name of the field of work of  is"}]}]}
        assert list(ripple.from_records([blank])) == []

    def test_declared_criterion_becomes_the_test_type(self):
        from editscreen.adapters import ripple
        types = {it.test_type for it in ripple.from_records([self.entry])}
        assert types == {"Relation_Specificity", "Subject_Aliasing"}

    def test_a_blank_slot_prompt_really_is_clean(self):
        """1,004 of 46,754 released test prompts leave the subject's slot
        empty. Those genuinely do not name it."""
        from editscreen.adapters import ripple
        items = {it.test_type: it for it in ripple.from_records([self.entry])}
        probe = items["Subject_Aliasing"]
        assert screen_any(probe.edits, probe.probe).level is Level.CLEAN

    def test_load_rejects_a_file_that_is_not_ripple(self, tmp_path):
        import json
        import pytest
        from editscreen.adapters import ripple
        p = tmp_path / "x.json"
        p.write_text(json.dumps([{"case_id": 1}]))
        with pytest.raises(ValueError, match="does not look like RippleEdits"):
            list(ripple.load(p))


def test_a_relative_clause_never_survives_into_the_recovered_subject() -> None:
    """RippleEdits writes negated attributes inline, and longest-wins preferred them.

    `" which (.+?) is associated"` captures the clause along with the subject, and
    the clause is what made that string the longest, so `subject_label` chose the
    damaged form over the clean one sitting beside it in the same set. Measured at
    577 of 3,818 entries (15.1%) across the three released files before the trim.
    """
    from editscreen.adapters.ripple import candidates, subject_label

    entry = {
        "Logical_Generalization": [{
            "test_queries": [
                {"prompt": "The name of the country which Dakhovskaya, "
                           "which is not Russian, is associated with is"},
                {"prompt": "The place of birth of Dakhovskaya is"},
            ]
        }]
    }
    cands = candidates(entry)
    assert all("which" not in c for c in cands), cands
    # The two prompts must collapse to ONE candidate, not compete on length.
    assert cands == ["Dakhovskaya"], cands
    assert subject_label(entry) == "Dakhovskaya"
