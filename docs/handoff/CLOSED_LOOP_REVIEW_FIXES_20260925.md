# Corrections before any further claim

The notes through `CLOSED_LOOP_GRADED_SENSITIVITY_20260925.md` were measured
on the previous mating rule and the previous cycle detector. They are the
record of that code. They are not the measurement of this revision
(`p6-review-20260925`). `engine.py` was not edited. `red_queen_proved`
is false. Maintenance of sexual reproduction is not claimed.

## Round 1. One mating rule

Nuismer, Otto, and Cornell (Ecol. Lett. 11:921–934, 2008,
doi:10.1111/j.1461-0248.2008.01207.x) showed that parasite-driven
disassortative mating is a separate trait from recombination, and that it
evolves only under narrow infection genetics. The pure arm was pairing a
leftover parent with itself and writing two offspring. The mixed census
gave that parent none. Both paths now call `mate_outcross`. A singleton
has no child. An odd count leaves one parent unmated. A pair has two
offspring. The two-fold cost of sex is still not applied.

The default pairing is by identity. Preferring a different recognition
window is `mate_choice="disassortative"` and is not silent. `recombine`
False copies the two parental tapes, so recombination can be turned off
without turning mating off.

## Round 2. Non-finite numbers

A comparison with NaN is false, so `virulence < 0` accepted NaN and still
produced a record. Virulence, birth ATP, and mutation rate must be finite.
Generations and the seed must be integers. A boolean is not an integer
here. Birth ATP must be positive because the birth is a refill, not a
free organism.

## Round 3. Counts, not names

A type-set return deletes how many hosts carry the window. One return
with one match debit was enough for `debit_backed_cycle`. That function
remains as a detector test. It is not the live cycle flag.

The live class is pre-declared. `stable` requires two paid returns of the
same host count-vector and a parasite count-vector that is not constant.
`transient` is one paid return while the parasite moved. `forced` is a
repeat under a fixed parasite, or a return that was not paid. The live
`cycles` flag is `stable` only.

## Round 4. A cost of zero is not removal of the parasite

Setting virulence to 0 used to skip resampling and mutation as well as
the debit. `absent` still removes the interaction: no contact and no
passage. `costless`, and virulence 0 on `coevolve`, record the match,
keep the passage, and charge nothing. Those are different interventions
(Pearl, Biometrika 82:669–688, 1995, doi:10.1093/biomet/82.4.669).

## Round 5. What may not be claimed

The factorial stores every virulence row, the birth ATP, the mating rule,
both frequency paths, a revision string, and a digest. Seed 7 is marked
`development_seed`. It is not an evaluation seed. `first_tested_success`
is the first grid value that meets the full rule. On this revision that
value is absent: the development factorial does not meet the rule, and
neither does seed 1. The field is not a biological threshold.

Offspring and the next parasite stock are created at `birth_atp`, and the
parasite count is held at 12. The record names this
`passage_reset_not_ecological_closure`. It is the assumption of a passage
experiment. It is not evidence that the two populations sustain each
other.

A time-shift panel on a mechanism built to cycle tests that detector. It
is not a measurement of this population. The pure-arm table is not a
claim that a mating strategy increases inside a mixed population.
`sexual_maintenance_claimed` is false. Maynard Smith's two-fold cost is
not in the model.

## What the corrected evaluation seeds do

Seeds 101–108, strict weight, random mating, mutation 0.7, 48 generations,
birth ATP 10, virulence 32. The cycle clause is the stable class.

Separate populations: 0 of 8. No outcross arm is in the stable class at
this virulence. Selfing goes extinct on some seeds and not others. The
block fails.

Mixed census: 0 of 8. Outcross count at generation 48 is 0 under both
coevolution and the frozen stock. Generation 0 has no unmated outcross
parent. The block fails.

Graded overlap: 0 of 8. Outcross × coevolve is extinct on every seed.

The sensitivity cross, virulence 8 through 40 by 2 and birth ATP 8, 10,
and 12, never puts a stable outcross cycle and a selfing extinction
together. The conjunction is 0 in every cell. Stable cycles are common
below the extinction step: at virulence 8 and birth ATP 10, all 8
outcross arms are stable and no selfing arm is extinct. The first
virulence at which at least 6 selfing arms are extinct is 16, 20, and 24
for birth ATP 8, 10, and 12. From that step through virulence 40 the
stable-cycle count on outcross is 0 and the selfing-extinct count stays
6. The primary cell, virulence 32 and birth ATP 10, is on that plateau.

The flag needs 6 of 8 on the separate block, the mixed block, and the
graded block. The counts are 0, 0, and 0. The flag stays false.
