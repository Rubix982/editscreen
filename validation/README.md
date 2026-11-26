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

## Three label sets, one of them filled in

| file | n | what it settles |
| --- | ---: | --- |
| `labels.human.txt` | 25 | whether the MQuAKE precision figures are agreement with one labeller or a measurement |
| `labels.ripple.human.txt` | 25 | the same, on RippleEdits |
| `labels.ripple-pairs.human.txt` | 39 | which of two recovery rules is right — [T-019]. **Filled in, both passes** |

The first two are still empty. They are blind re-draws of items already labelled once, so filling them gives an agreement rate where today there is none. Score them with `score.py --labels <the human file> --sample <the matching sample.json>` and compare against the `.claude.txt` run.

**Both were redrawn on 2026-11-24, and the first draw is discarded.** It was a random slice of the already-labelled items, so it inherited the big draw's stratum proportions: mostly CLEAN and ALIAS, and **four** items the matcher had called STRICT on MQuAKE. A false positive can only appear in an item the matcher called STRICT, so the headline claim — *the strict rule has not been seen to be wrong* — would have got an agreement rate built on four items, while twenty-one measured agreement on recall, which nothing published leans on. Same hour either way. The replacement spends it on the number that is actually quoted:

```
python3 validation/sample_human.py      # 15 STRICT, 5 ALIAS, 5 CLEAN per corpus
```

Each verdict's quota is spread evenly over the released files or subsets that carry it, so no one file dominates. The blocks are copied verbatim out of the first pass's file rather than re-rendered, so both labellers answer about identical text — a rendering difference would show up as a difference in judgement.

**The third is a different kind of draw and `sample.py` cannot produce it.** [C-012] showed the released longest-candidate rule and a restricted one — canonical pick taken only from the five non-aliasing test types — give strict rates eighteen points apart on `random`, while the named-or-varied rate does not move. The existing sets cannot decide between them: they were drawn stratified by the *released* rule's own verdicts, so they cannot be reweighted to score another rule.

```
python3 validation/sample_pairs.py      # redraw it; seed 20261124, deterministic
```

**Only the items the two rules disagree on can separate them**, and 4,044 prompts of the 38,092 screened do. `sample_pairs.py` draws six from each subset × transition cell. One label settles both rules at once, because the scorer already knows what each decided — which is why that file shows neither verdict and, unlike the other two, **neither recovered string.** What it shows instead is the Wikidata label for the subject id the benchmark itself cites, because which of the two recovered strings is the subject's name is the entire question and showing them would be the circularity this draw exists to escape.

`s` means the same thing in all three files: the name on the `subject:` line, written out in full. A name on the `aliases:` line is `a`.

```
python3 validation/score_pairs.py --labels validation/labels.ripple-pairs.human.txt
```

### Both passes are in, and the restricted rule wins both

Reweighted to the 4,044 contested prompts:

| labeller | released rule right | restricted rule right | neither |
| --- | ---: | ---: | ---: |
| model — `labels.ripple-pairs.claude.txt` | 9.4% | **89.7%** | 0.9% |
| human — `labels.ripple-pairs.human.txt` | 10.3% | **87.7%** | 2.0% |

It wins in both directions — on the prompts the restriction moves ALIAS→STRICT and on the ones it moves STRICT→ALIAS — so it is not an artifact of one rule flagging more.

**Agreement between the two labellers: 35 of 39, 89.7%**, measured on the blind labels before anything was revisited. The four disagreements are where the rule is soft rather than where someone slipped. Two are a stage name (`Show Master of Africa` for Bob Pinodo) and a legal name (`Alison Moira Clarkson` for Betty Boo): *names* by the written rule, *descriptions* to a reader, so one labeller said `a` and the other `d`. One is a two-letter spelling difference, `Kaboeai Island` against the subject's `Kabuai Island`. The fourth, item 034, was a slip and was corrected afterwards **with the other labeller's answer visible** — it is marked NOT BLIND in the file and excluded from the agreement rate above. It moves the restricted rule from 85.9% to 87.7% and moves nothing else.

**So this one number is no longer single-labeller. Every other precision figure in this directory still is**, and the two 25-item sets above are what would change that.

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

**Any precision figure from either set must be quoted with that agreement rate beside it.** Two error rates stacked, both named, is honest; one of them hidden is not.

**Both subsets are filled in as of 2026-11-24, and the strict rule survives.**

| | agreement | STRICT items | disagreements on a STRICT item |
| --- | ---: | ---: | ---: |
| MQuAKE | **25 of 25** | 15 | 0 |
| RippleEdits | **22 of 25** | 15 | 0 |

Strict precision reads 100% under the second labeller on both corpora, as it did under the first. **Thirty items the matcher called STRICT, two labellers, no disagreement between them and no error against either.** That does not enlarge the sample the published figure rests on — that is still the 121 STRICT items of the first pass, with rule-of-three bounds of 7.5%, 14% and 15% per stratum — but it does mean those labels are no longer one annotator's word.

All three RippleEdits disagreements sit on the same boundary, and none of them is on a STRICT item: **a name variant that Wikidata does not list.** `Jacob Gershon`, a Hebrew name for the subject, read as a variant by one labeller and as nothing by the other; `Koba`, likewise; and one item where a longer form was read as the name itself by one and as a variant by the other. That boundary is where this matcher is genuinely uncertain, and it is the alias rule's territory rather than the strict rule's.

**What the redraw cost, stated because it was a deliberate choice.** Weighting to STRICT left **five ALIAS items across three RippleEdits subsets** — one, two and two. `score.py` duly reports alias precision of 0%, 50% and 100% on those. Those are not measurements of anything; at n=1 a single judgement call on an unlisted Hebrew name prints as 0.0%. The alias rule's figure remains the held-out 90.2% [75.8, 100.0] from the first pass. **That draw now exists:**

```
python3 validation/sample_human.py --alias
```

`labels.alias.human.txt` is 10 items from the **held-out** MQuAKE set, which is where the 90.2% is measured — 5 from each released file, and that set is alias-only, so there is nothing else in it to draw. `labels.ripple-alias.human.txt` is 12, ten of them alias. Score them against `holdout.json` and `sample.ripple.json` respectively — **not** against `sample.json`, whose item ids collide with the holdout's and would rejoin the labels to the wrong items without erroring.

### The MQuAKE half did not buy a second labeller, and is a test–retest instead

**It drew from the wrong file, and the mistake is instructive rather than fatal.** The RippleEdits half takes its items from `labels.ripple.claude.txt`, blanks them, and asks the human — which is how a second labeller is bought. The MQuAKE half takes its items from `labels.holdout.txt`, and that file is the **human's own** first pass. There is no model pass on the held-out set to draw from, so by this route a second labeller was never available. The draw blanked the human's answers and asked the same person again.

What that produced is a **test–retest reliability check**: the same labeller, the same ten items, verdicts hidden, one day apart.

| id | subset | first pass | retest |
| --- | --- | --- | --- |
| 001 | MQuAKE-CF-3k | `a` | `a` |
| 004 | MQuAKE-CF-3k | `a` | **`d`** |
| 014 | MQuAKE-CF-3k | `a` | `a` |
| 018 | MQuAKE-T | `a` | `a` |
| 019 | MQuAKE-CF-3k | `a` | **`d`** |
| 029 | MQuAKE-T | `a` | `a` |
| 039 | MQuAKE-T | `a` | **`d`** |
| 040 | MQuAKE-T | `a` | **`d`** |
| 043 | MQuAKE-CF-3k | `a` | `a` |
| 045 | MQuAKE-T | `a` | **`d`** |

**Agreement is 5 of 10, and every one of the five changes runs the same way, `a` to `d`.** A one-directional shift is not noise. The reading of one boundary moved between passes, and on the retest `score.py` reports alias precision of 60.0% [20.0, 100.0] on MQuAKE-CF-3k and 40.0% [0.0, 80.0] on MQuAKE-T, against 100% on these same ten items the first time.

**One boundary accounts for all of it: a subject's name embedded inside a product or work name.** Nine of the ten items have that shape, and the retest split it against itself — `Aston Martin DB5` and `DB3S` read as `a` while `DB9` and `DBR9`, on near-identical probes with the same subject, read as `d`; `Commodore PET` as `a` but `Yamaha DX7` as `d`. Item 019, the Browning M1919, is the case this file already recorded below as a judgement call before the retest existed, and it is one of the five that moved.

**The embedded-name case is most of the held-out set, not a corner of it.** Running the alias matcher over all 47 items and looking at what follows each match: **37 of 47 are a derived single-token match followed by a capitalised token** — `Bach`-Werke-Verzeichnis, `Commodore` PET, `Yamaha` DX7, `Browning` M1919, `Ford` Taurus, `Aston` Martin DB9, `Apple` Pay, `Mike` Mignola. So whichever way this case is called sets the 90.2% almost by itself.

**The first pass did settle it, and the rule is recoverable from its own notes.** It labelled exactly four items `d`, and each carries a note saying why:

| id | subject | match sits in | note | label |
| --- | --- | --- | --- | --- |
| 015, 041 | Mike Richardson | `Mike Mignola's` | *a different person* | `d` |
| 006, 016 | Henry Ford | `Ford Orion` | *the car brand two steps from the man* | `d` |

and the other 43 `a`, including seven where the subject is **Ford Motor Company** and the probe says `Ford Taurus`, `Ford GT40`, `Ford Capri`. Those two groups are not inconsistent. They are one rule applied twice:

> **When the match sits inside a longer name, ask which entity that longer name denotes. The test is the entity, never the string.** It denotes the subject, or a product carrying the subject's own name → `a`. It denotes something else that merely shares a name part → `d`.

`Ford Taurus` carries the maker's name and the maker is the subject, so `a`. `Ford Orion` carries the maker's name and the subject is the *man*, who is reached only as "the founder of the manufacturer", so `d`. `Mike Mignola` is a different person, so `d`. **That rule is consistent across all 47 items of the first pass.**

**The retest is the pass that broke it.** Its five `a`→`d` moves are all on `Aston Martin DB*`, `Commodore PET`, `Yamaha DX7` and `Browning M1919` — company-or-maker subjects whose own name the product carries, which the rule calls `a` and which the first pass called `a` seven more times under the Ford Motor Company subject that the retest never saw. So the five are errors against the first pass's own standard rather than a competing reading of an undecided case.

**What stands, and what this cost.** The 90.2% [75.8, 100.0] stands, and now rests on a stated rule rather than an unstated habit — the rule is written into `sample.py`'s legend and `label.py`'s help as of this commit. The honest limit is that **it was written down after the fact.** It was reconstructed from four `note:` lines and verified against the pass it came from, which cannot be an independent check of that pass. What it does buy is that the next labeller is given the rule instead of having to re-derive it, which is the thing the retest shows does not survive a day.

**A genuine second labeller for MQuAKE is still unbought**, and needs a model pass on `holdout.json`, which does not exist yet.

**One thing the retest found that the first pass got wrong is in the instrument, not the labels.** `matchers/alias.py` already guards this class — `_belongs_to_another_name` declines a match when the capitalised word *before* it belongs to someone else, and its comment names the Ceausescu and Pinkett Smith cases. It only looks backwards. `Mike` in `Mike Mignola's` is the same error with the parts the other way round, and the guard cannot see it; items 015 and 041 were caught by the human and not by the screen. Extending the guard to a following token is **not** a safe fix, because the same shape covers `Ford Taurus`, where the match is correct. Any fix has to separate those two, and nothing here establishes how.

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

## `by_test_type()` on RippleEdits is checked differently, and one of its rows is partly circular

Every precision figure above is stratified by **subset**. The per-test-type breakdown the CLI prints is a different cut of the same items and has never been given its own labelled draw. What it has been given is a check of a different kind, run as [C-011] in `edit-reach`: RippleEdits declares six test types and defines each one, so each definition predicts whether that type's queries should contain the edited subject's name. The predictions were written down before the counts were read, and all six hold in all three subsets — the three types that ask about the edited subject screen at the top, the type that asks about a different entity screens at the bottom, and the mixed type sits between them.

**That is a check on the shape of the table, not on its precision.** It says the per-type numbers are not nonsense. It does not say how often a verdict on a given type is right, and a figure for that needs a draw stratified by type.

**One row is partly manufactured by the adapter.** This corpus names its subject by QID, so `subject_label()` takes the longest candidate the entry's own prompts offer — and `Subject_Aliasing` prompts contribute candidates like every other type. When the longest string an entry offers is an alias lifted out of an aliasing prompt, the screen then reports that same prompt as naming the subject. It read the name out of the prompt and found it there.

| subset | `Subject_Aliasing` strict hits | label came from an aliasing prompt |
| --- | ---: | ---: |
| `recent` | 190 | 64 (34%) |
| `random` | 621 | 483 (78%) |
| `popular` | 256 | 135 (53%) |

682 prompts of the 38,092 screened, 1.8%, and the share is not stable enough across subsets to be subtracted as a constant. It inflates this type's **strict** rate and not its alias rate.

**Measured 2026-11-24, and the circularity is the smaller half of what the rule does.** Rescoring all three subsets with the canonical pick restricted to the five non-aliasing types — every candidate still passed on as an alias — moves the strict rate **up**, not down:

| subset | strict, as released | strict, restricted | named-or-varied, as released | restricted |
| --- | ---: | ---: | ---: | ---: |
| recent | 0.796 | 0.820 | 0.898 | 0.898 |
| random | 0.519 | **0.707** | 0.902 | 0.905 |
| popular | 0.564 | 0.662 | 0.851 | 0.849 |

The longest candidate an entry offers is often a long formal variant lifted out of an aliasing prompt — `Theodore Vonkurnatowski` where the entry's other prompts all say `Theo Vonkurnatowski` — and once that is canonical, the prompts that do name the subject match only a variant of it. It relabels 19.9% of `random`'s entries against 3.2% of `recent`'s. **The union does not move**: every prompt that changed verdict moved between STRICT and ALIAS inside the flagged set.

**Still left in place, and now for a better reason than before.** Switching would change the documented 80.3% coverage figure and every rate taken under it, and it would publish a canonical-pick rule whose precision has never been measured — `sample.ripple.json` was drawn stratified by the *released* rule's verdicts, so it cannot be reweighted to score another one. Where the two rules disagree and the entry's Wikidata label can adjudicate, the restricted one wins 6 to 1 over 33 cases with 24 ties: directional, and not a precision figure. The fix is a draw under the new rule, not an edit to this one.

## Why the intervals resample clusters

Items are not independent. Three MQuAKE questions share one case and one edited subject; dozens of RippleEdits prompts share one entry and one recovered label. A bootstrap over rows counts those as separate draws and reports an interval narrower than the evidence supports.

So `sample.json` records a `cluster` for every row — the case for MQuAKE, the entry for RippleEdits — and the bootstrap resamples clusters inside each stratum. It widened the held-out alias interval from [80.5, 97.6] to [75.8, 100.0] and the pre-fix one from [45.1, 69.0] to [42.4, 71.4], and moved neither point estimate. Rows drawn before `cluster` existed stand alone, which reproduces the older numbers rather than silently changing them.

## Reproducing

`sample.json` records the seed, the stratum sizes, the matcher version, the `editscreen` commit and the sha256 of every input file. The scorer reads it rather than the corpus, so scoring needs neither the benchmarks nor a network.

Numbers from one matcher version are not comparable to another's. If `MATCHER_VERSION` changes, the verdicts have to be redrawn even though the labels stay valid — the labels describe the items, not the screen.
