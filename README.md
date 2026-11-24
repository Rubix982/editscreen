# editscreen

**Given a knowledge edit and an evaluation probe, does the probe identify the edited subject?**

If it does, a score on that item is not evidence that the edit propagated. The model can reach the answer by recalling what was just written into it, with no propagation having occurred at all.

```python
from editscreen import Edit, screen

screen(Edit(subject="Henry Mackenzie"),
       "Henry Mackenzie was born in the country of").level
# <Level.STRICT: 1>

screen(Edit(subject="Henry Mackenzie"),
       "The capital of France is").level
# <Level.CLEAN: 0>
```

```
$ editscreen mydata.json
editscreen 0.2.0 — 5 items

  CLEAN               2
  STRICT              2   subject's own surface form in the probe
  ALIAS               1   a name variant only

  names the subject outright:      40.0%
  including name variants:         60.0%

  Quote the first. Measured on 441 hand-labelled items from
  MQuAKE and RippleEdits, the strict rule has not yet been seen
  to be wrong and the alias rule is right nine times in ten, so
  the two are not worth merging into one number.

  Neither is a bound on IDENTIFIABILITY. A probe that picks the
  subject out by description without naming it reads CLEAN here.

  by declared test type:
    one-hop      2/3       66.7%
    two-hop      0/2        0.0%
```

## How often the matchers are wrong

Measured, on two benchmarks, against 441 items labelled by hand. The strict rule has not yet been seen to be wrong: **100%** on 261 MQuAKE items and **100%** on each of RippleEdits' three subsets. The derived-alias rule is right **90.2% [75.8, 100.0]** on a held-out MQuAKE draw and 95–100% per RippleEdits subset.

`validation/` holds the sample, the labels, the scorer and the limits — including the one that matters most, which is that the labels were produced by a model and the human agreement check is still outstanding.

## What it does not do

It does not load a model, compute a gradient, or apply an edit. Contamination is a property of **how the evaluation item was written**, not of how the weights were changed — so the answer is the same whether the edit came from ROME, MEMIT, fine-tuning or a person typing it. Core has no dependencies beyond the standard library.

It also does not tell you your score was inflated. It cannot: it never sees your scores. It hands back the item ids, and you split your own results:

```python
report.ids()                      # items that name the subject
report.ids(at_or_above=False)     # items that do not
```

Whether your number moves when you drop the first set is a question about your experiment, and it stays yours.

## The levels

| | |
| --- | --- |
| `CLEAN` | nothing in the probe points at the edited subject |
| `STRICT` | the subject's own surface form occurs in the probe |
| `ALIAS` | a name variant occurs — a surname alone, a given name, a supplied alias |
| `IDENTIFIABLE` | no name occurs, but a description picks the subject out anyway |

**`STRICT` is a lower bound, and that is why it is the headline.** Everything it finds is really there. It misses every item that identifies the subject some other way, so the true rate is higher than the reported one, never lower.

**`IDENTIFIABLE` is not implemented.** *"The author of The Man of Feeling was born in"* names Henry Mackenzie without containing his name, and detecting that needs a knowledge base or a model. When it lands it will ship as an optional extra and its number will stay in its own column, never folded into the headline — a disputed headline rate would cost more than the extra coverage is worth.

## Known failure modes

Stated here rather than discovered by a reader:

- **Derived name variants are Western-name-shaped.** Splitting on whitespace into given and family parts under-fires on names that do not work that way. Pass `aliases=` to cover what it cannot derive.
- **Family names that are also common words fire.** "Bush", "Rice", "Baker" — the main source of derived false positives.
- **Pronouns are invisible.** A probe saying "he" after a subject named in an earlier turn is scored `CLEAN`.
- **One probe, no context.** Items whose probe depends on a surrounding conversation are screened on the probe alone.
- **A surname after a middle initial is suppressed.** The guard that drops a match belonging to a neighbouring name reads the word before it, and in "William H. Gates III" that word is an initial. Found on the RippleEdits draw, where it accounts for most of the misses, and deliberately not fixed there — see `validation/README.md` on why a fix is never scored on the sample that produced it.
- **Titles survive as derived variants.** "Princess", "Count", "Sir" are not in the generic-word list, so "Princess Alice of Battenberg" can match on "Princess" alone. Both of the two false positives in the RippleEdits draw were this shape or its family-name cousin, "Ursula von Baden" against "Agnes of Baden".

## Install

```bash
pip install editscreen          # alpha; pip resolves it with no --pre needed
pip install -e ".[dev]"         # from a clone
```

Requires Python 3.10+.

## Benchmarks it reads directly

```bash
editscreen MQuAKE-CF-3k.json --adapter mquake
```

Reads all four released MQuAKE files, which share one record shape. Each case's three questions are screened separately, and the hop count is read off the labelled chain rather than assumed, so the stratification can be checked against the source file.

**Most MQuAKE cases edit more than one fact**, so an item carries several edits. The item is flagged if any of them matches, and the verdict reports the strongest evidence among those that did. `Item.edits` is a tuple for this reason.

```bash
editscreen random.json --adapter ripple
```

RippleEdits names its subject by Wikidata QID and leaves the slot blank in some prompts, so there is no string to look for. There is no knowledge base here and there is not going to be one. Instead the label is read back out of the entry's own test prompts, which materialise it — "The official language of Goursez Vreizh is". That recovers a subject for **75.0% of `recent`, 85.0% of `random` and 81.8% of `popular`**.

Report those per subset and never pooled; the subsets are built from different slices of Wikidata and a single 80.3% describes no file anyone can download. Entries whose subject cannot be read are skipped entirely, the command says how many, and `ripple.coverage(path)` returns the numbers — because emitting them would report them CLEAN, and a false clean is the one error this package exists to prevent.

## Which number to quote

`rate_strict` counts probes containing the subject's own surface form. `rate_strict_or_alias` adds matches on a name variant. **Quote the first.**

Measured on 261 hand-labelled MQuAKE items, the strict rule was right every time and the alias rule 90.2% [75.8, 100.0] on a held-out draw — and before it was fixed, 57.1% [42.4, 71.4]. When that fix landed, every alias-inclusive rate moved and every strict rate stayed exactly where it was. `validation/` has the method and the limits.

Neither rate bounds **identifiability**. A probe that picks the subject out by description without naming it reads CLEAN. On MQuAKE that is almost every unnamed item, because its questions are rendered from the chain the edit sits on. What these rates measure is whether the probe hands the model the *name*, which is the thing a model can exploit without reasoning.

**That advice now rests on two corpora rather than one, and the second does not hand the screen its subject.** 180 further items were drawn from RippleEdits — its three subsets crossed with the three verdicts — and labelled with a fifth letter meaning *the recovered subject is not this entry's subject at all*. The strict rule was right on every flagged item in all three subsets, and that fifth letter was never used: on 166 distinct entries the longest-candidate recovery named the right entity every time.

So a strict hit means what it means on MQuAKE even where the subject had to be recovered rather than read. What the recovery gets wrong is the *shape* of the string, not the entity — 28 of the 180 carried a trailing clause from the benchmark's own phrasing, which costs recall and cannot cost precision.

## Your own data

A JSON list. `subject` and `probe` are required, everything else is optional.

```json
[{"id": "q1",
  "subject": "Henry Mackenzie",
  "probe": "Henry Mackenzie was born in the country of",
  "test_type": "one-hop",
  "aliases": ["The Man of Feeling"]}]
```

```bash
editscreen mydata.json --json
```

## Where it came from

The observation this screens for was found while measuring how far a single rank-one weight edit travels: on one published multi-hop benchmark, the items that name the edited subject are exactly the items where the edit sits on the first hop. The measurement work is at [edit-reach](https://github.com/Rubix982/edit-reach).

That project's own screen was a delivery coefficient computed from the unedited model, and it was reported negative — it predicted delivery, not effect. This package is the part that survived: the half that needs no model, and holds for any editing mechanism.

MIT.
