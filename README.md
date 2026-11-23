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
editscreen 0.1.0 — 5 items

  CLEAN               2
  STRICT              2   subject's own surface form in the probe
  ALIAS               1   a name variant only

  contaminated at STRICT or above: 60.0%

  by declared test type:
    one-hop      3/3      100.0%
    two-hop      0/2        0.0%
```

## This release is not validated yet

`0.1.0a1`. The matchers run, the tests pass, and **nobody has measured how often they are wrong.** The hand-labelled set that would give a precision and a recall is not built, so no contamination rate produced by this version should be quoted.

That is the next piece of work and it is the one that matters. A screen that reports what it found without reporting how often it is mistaken is asking to be believed rather than checked.

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

## Install

```bash
pip install editscreen          # not published yet
pip install -e ".[dev]"         # from a clone
```

Requires Python 3.10+.

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
