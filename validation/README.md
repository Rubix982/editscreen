# The labelled set

A few hundred items drawn from real benchmarks and labelled by hand, and the command that scores the matchers against them. Until the labels exist, `editscreen` reports what it found and cannot say how often it is wrong.

```
python3 validation/sample.py     # draws labels.txt and sample.json
python3 validation/label.py      # one item at a time, or edit labels.txt by hand
python3 validation/score.py      # precision and recall, any time, part-way through
```

The same three commands run against RippleEdits by naming it:

```
python3 validation/sample.py --adapter ripple
python3 validation/label.py  --labels validation/labels.ripple.txt
python3 validation/score.py  --labels validation/labels.ripple.claude.txt \
                             --sample validation/sample.ripple.json
```

`label.py` is a typing convenience and writes to `labels.txt` after every answer, so the file stays the one source of truth and the two ways of filling it mix freely.

## What you are labelling

One letter per item:

- `s` — the subject's own name appears in the probe, written out in full
- `a` — only a variant appears: a surname alone, a given name, a pen name
- `d` — no name appears, but the probe describes the subject well enough that a reader could say who it is
- `n` — nothing in the probe points at the edited subject

RippleEdits adds a fifth, and it beats the other four:

- `w` — the `edit:` line is not this entry's subject at all

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

**`labels.txt` does not say which stratum an item came from.** Seeing that the screen called an item STRICT is an invitation to agree with it, and the quantity that inflates is precision — the one number this set exists to produce. The assignment lives in `sample.json` and the scorer rejoins it.

The rows are shuffled across strata on purpose. Labelling stops when it stops, and a file ordered stratum by stratum would turn an hour's work into a complete census of one stratum and nothing of the others. Interleaved, every stopping point is a smaller version of the same design.

## Who produced the labels

`labels.claude.txt` holds all 261, labelled by a model. That is a usable way to get a few hundred items done and a bad thing to leave unstated: every figure scored against it inherits whatever that labeller gets wrong.

So `check.py` draws a random subset, a person labels it without seeing the model's answers, and the agreement is reported beside the precision it qualifies:

```
python3 validation/check.py --draw 25
python3 validation/label.py --labels validation/labels.human.txt
python3 validation/check.py
```

Agreement is reported twice. Exact agreement counts matching letters. The one precision actually rests on is agreement on whether a name or variant is present at all — `s` or `a` against `d` or `n` — because an `s`-versus-`a` disagreement moves no reported number.

The RippleEdits set has its own 25, drawn the same way:

```
python3 validation/check.py --draw 25 --seed 101 \
    --blank validation/labels.ripple.txt --human validation/labels.ripple.human.txt
python3 validation/check.py --machine validation/labels.ripple.claude.txt \
    --human validation/labels.ripple.human.txt
```

**Any precision figure from either set must be quoted with that agreement rate beside it.** Two error rates stacked, both named, is honest; one of them hidden is not. **Neither human subset is filled in yet**, so every figure in this file currently rests on one labeller, and that labeller is a model.

## The held-out set

`labels.holdout.txt` is 47 alias matches drawn with a different seed and `--exclude`d from the 261, so no item appears in both.

It exists because the alias fixes in 0.2.0 were derived by reading the false positives in the first sample. Scoring them there gave 100%, which is training-set performance and means nothing. The matcher was committed before this set was drawn.

| | first sample | held out |
| --- | --- | --- |
| alias, flag is right | 57.1% [42.4, 71.4] | 90.2% [75.8, 100.0] |

The intervals do not overlap, so the improvement is real; 100% was not.

**Both intervals are wider than this table first carried**, because the bootstrap now resamples clusters rather than rows — see below. The two point estimates did not move and the conclusion did not change, but [45.1, 69.0] and [80.5, 97.6] were too narrow and are superseded.

Two failure modes survive, both found here and **not** fixed, because fixing against this set would spend it the same way the first one was spent:

- **A given name shared with someone else.** The edited subject is Mike Richardson and the probe says "Mike Mignola's employer". The neighbour guard reads the word *before* a match, and a given name is followed by the other person's surname rather than preceded by it.
- **A brand two steps from the person.** The edited subject is Henry Ford and the probe says "the manufacturer of Ford Orion". The car is named for the company and the company for the man, and a reader meeting "Ford" there is not being handed Henry Ford. Item 019 is the same shape and goes the other way — the Browning M1919 is named directly for its designer — so this one is a judgement call, and it is recorded as one.

## A shortcut that does not work

MQuAKE questions are rendered from the labelled chain in `orig.triples_labeled`, and the edited subject is a node on that chain in 100% of cases in both files. It is tempting to conclude that every unnamed subject is therefore reachable by description, and to derive the `d` label for free.

Three of the 120 clean items in this sample show it is not so. The chain holds the subject, but the question does not render the hop that reaches it — item 157 asks where Avery Johnson is from and never mentions a sport, while the edited subject is the sport. The chain is a property of the record; the probe is a property of the text, and only the text is what a model sees.

## What this set cannot establish

**Recall on MQuAKE-T will have a wide interval whatever the labels say.** One real miss among 60 labelled clean items stands for about 92 items in the corpus, against the 88 the screen finds in total — so a single labelled item moves the estimate by more than the entire flagged population. Planting six misses as a test gave recall 13.8% with an interval of [8.0%, 32.4%]. Narrowing that needs roughly four times the clean items for half the width, and it is the one place extra labelling pays: raise `MQuAKE-T/CLEAN` in `PLAN` and redraw.

Precision does not have this problem in either benchmark, and recall on MQuAKE-CF-3k does not either, because 67.8% of its items are flagged.

**Nothing here says whether an edit worked.** The screen measures how an evaluation item was written, not what a model did with it.

**The matchers are Western-name-shaped**, as `matchers/alias.py` says, and both corpora are English questions over Wikidata entities. That is the friendliest case they will ever meet, and precision measured here is an optimistic estimate for a corpus of another shape.

## The RippleEdits set

180 items, twenty from each of the three subsets crossed with the three verdicts, drawn with the same sampler and scored by the same scorer.

It exists because MQuAKE hands the screen its subject as a string and RippleEdits does not. There the subject is a Wikidata QID, and the adapter recovers a label from the entry's own test prompts, so a strict match says a *recovered* string is in the probe. A hundred per cent on MQuAKE says nothing about that, because it is a measurement of a different thing: there the only way a strict hit can be wrong is a bad word boundary, and here the recovery itself can be wrong.

| | strict | alias |
| --- | --- | --- |
| recent | 100.0% [100.0, 100.0] | 95.0% [84.2, 100.0] |
| random | 100.0% [100.0, 100.0] | 100.0% [100.0, 100.0] |
| popular | 100.0% [100.0, 100.0] | 95.0% [84.2, 100.0] |

Per subset and never pooled: the three recover their subjects at rates ten points apart, so a single figure would describe no file anyone can download.

**`w` was never used.** On 166 distinct entries the longest-candidate recovery named the right entity every time, including where the two strings look nothing alike — `Camp Rucker Theatre` for *Fort Rucker Theatre*, `Anyer Island` for *Anyar*, `Carolina Paz Santana de la Hoz` for *Leslie Santana*. What the recovery gets wrong is the *shape* of the string and not the entity: **28 of the 180 carried a trailing clause** from the benchmark's own phrasing, as in `Daniel G Gavin, which is not media consultant,`. A malformed string is harder to find in a probe, not easier, so it costs recall and cannot cost precision.

### How `w` is adjudicated, and why it is not self-judged

The recovered label came out of the entry's own prompts, so those prompts cannot adjudicate it: a wrong label consistent with them would be invisible. So the adjudication goes to the authority the benchmark itself cites. `validation/wikidata.py` resolves each drawn entry's `subject_id` to its English label and aliases, and `labels.ripple.txt` shows that beside the recovered string.

Nothing in the package imports it and nothing calls it at screening time. The cache it writes is the artifact, so scoring runs on a machine with no route to Wikidata.

### Two false positives, and what they share

Both are alias matches on a word that belongs to somebody else in the probe.

- **A title.** "Princess Alice of Battenberg" matched "The place of burial of the mother of Princess Margarita of Greece and Denmark is" — on *Princess*. Titles are not in the generic-word list in `matchers/alias.py`.
- **A house name.** "Ursula von Baden" matched "The name of the father of Agnes of Baden is" — on *Baden*, shared by a relative, which is the same shape as the Henry Ford case in the held-out set.

### The misses, which are more numerous and more interesting

Twenty-five of the 180 were called CLEAN while a variant really was present, and most are one failure: **the neighbour guard suppresses a surname that follows a middle initial.** The guard reads the word before a match and drops the match if that word is a capitalised name belonging to someone else. In `William H. Gates III` the preceding word is `H`, which is capitalised, is not part of `Bill Gates`, and is not at a sentence start — so the guard fires and the real surname is thrown away. `A. Fauci`, `Steven Jonathan Carlip`, `Michael Scott Matthews` and `Sir Arthur Alexander Foulkes` all go the same way.

**None of this is fixed here.** Both faults were found by reading this sample's errors, and the 0.2.0a2 lesson is that a fix read off a sample scores 100% on it and 90.2% anywhere else. A fix is committed before a second draw exists, and that draw is what scores it.

## Why the intervals resample clusters

Items are not independent. Three MQuAKE questions share one case and one edited subject; dozens of RippleEdits prompts share one entry and one recovered label. A bootstrap over rows counts those as separate draws and reports an interval narrower than the evidence supports.

So `sample.json` records a `cluster` for every row — the case for MQuAKE, the entry for RippleEdits — and the bootstrap resamples clusters inside each stratum. It widened the held-out alias interval from [80.5, 97.6] to [75.8, 100.0] and the pre-fix one from [45.1, 69.0] to [42.4, 71.4], and moved neither point estimate. Rows drawn before `cluster` existed stand alone, which reproduces the older numbers rather than silently changing them.

## Reproducing

`sample.json` records the seed, the stratum sizes, the matcher version, the `editscreen` commit and the sha256 of every input file. The scorer reads it rather than the corpus, so scoring needs neither the benchmarks nor a network.

Numbers from one matcher version are not comparable to another's. If `MATCHER_VERSION` changes, the verdicts have to be redrawn even though the labels stay valid — the labels describe the items, not the screen.
