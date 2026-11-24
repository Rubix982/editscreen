# The labelled set

A few hundred items drawn from real benchmarks and labelled by hand, and the command that scores the matchers against them. Until the labels exist, `editscreen` reports what it found and cannot say how often it is wrong.

```
python3 validation/sample.py     # draws labels.txt and sample.json
                                 # ... fill in the label: lines ...
python3 validation/score.py      # precision and recall, any time, part-way through
```

## What you are labelling

One letter per item:

- `s` — the subject's own name appears in the probe, written out in full
- `a` — only a variant appears: a surname alone, a given name, a pen name
- `d` — no name appears, but the probe describes the subject well enough that a reader could say who it is
- `n` — nothing in the probe points at the edited subject

`s` and `a` are what the screen claims to detect, so they decide precision and recall. `d` is what it deliberately does not detect; counting those is how the phrase "lower bound" gets a size instead of staying an adjective.

The `note:` line is worth filling only when an item fits none of the four letters. Those are the interesting ones — the levels in `types.py` were written from a handful of examples and have never met real data, and the expectation is that two or three items will fit none of them.

## Why it is stratified

Precision and recall need different items, and one uniform draw supplies neither well. Precision needs items the screen flagged. Recall needs the ones it missed, which live among the items it called clean. In MQuAKE-T only 1.57% of items are flagged at all, so a uniform sample of 200 would hold about three flagged items.

So each benchmark-and-verdict pair is sampled at its own rate and `score.py` reweights by the real stratum sizes. Two strata are taken whole: MQuAKE-T has 21 strict matches in 5,604 items, and a census has no sampling error.

| stratum | drawn | of |
| --- | --- | --- |
| MQuAKE-T / STRICT | 21 | 21 |
| MQuAKE-T / ALIAS | 40 | 67 |
| MQuAKE-T / CLEAN | 60 | 5,516 |
| MQuAKE-CF-3k / STRICT | 40 | 5,887 |
| MQuAKE-CF-3k / ALIAS | 40 | 214 |
| MQuAKE-CF-3k / CLEAN | 60 | 2,899 |

The rows are shuffled across strata on purpose. Labelling stops when it stops, and a file ordered stratum by stratum would turn an hour's work into a complete census of one stratum and nothing of the others. Interleaved, every stopping point is a smaller version of the same design.

## What this set cannot establish

**Recall on MQuAKE-T will have a wide interval whatever the labels say.** One real miss among 60 labelled clean items stands for about 92 items in the corpus, against the 88 the screen finds in total — so a single labelled item moves the estimate by more than the entire flagged population. Planting six misses as a test gave recall 13.8% with an interval of [8.0%, 32.4%]. Narrowing that needs roughly four times the clean items for half the width, and it is the one place extra labelling pays: raise `MQuAKE-T/CLEAN` in `PLAN` and redraw.

Precision does not have this problem in either benchmark, and recall on MQuAKE-CF-3k does not either, because 67.8% of its items are flagged.

**Nothing here says whether an edit worked.** The screen measures how an evaluation item was written, not what a model did with it.

**Both benchmarks are MQuAKE.** The matchers are Western-name-shaped, as `matchers/alias.py` says, and a corpus of English multi-hop questions over Wikidata entities is the friendliest case they will ever meet. Precision measured here is an optimistic estimate for anything else.

## Reproducing

`sample.json` records the seed, the stratum sizes, the matcher version, the `editscreen` commit and the sha256 of every input file. The scorer reads it rather than the corpus, so scoring needs neither the benchmarks nor a network.

Numbers from one matcher version are not comparable to another's. If `MATCHER_VERSION` changes, the verdicts have to be redrawn even though the labels stay valid — the labels describe the items, not the screen.
