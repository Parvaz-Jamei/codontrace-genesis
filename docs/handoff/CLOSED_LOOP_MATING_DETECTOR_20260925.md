# Seeded mating and a terminal oscillation rule

The measurements below are revision `p6-review-20260925b`. Earlier tables,
including those from `d4e63b0` and `93c3182`, used identity-ordered pairing
under the name `random` and a detector that called a later-extinct path
stable. Those tables stay the record of those revisions. They are not this
one. `engine.py` was not edited. `red_queen_proved` is false.

## Round 1. Identity order is not a random mating

Fisher and Yates (1938) and the in-place form of Durstenfeld (1964), as
given by Knuth (1998, The Art of Computer Programming, vol. 2), generate
each permutation exactly once when each index is drawn uniformly from the
prefix that remains. A sort by `org.id` followed by adjacent pairs does
not. Four parents with windows `000111, 000111, 111000, 111000` produced
those same windows in identity order, and the recombinant windows
`111111, 000000` when the identities were interleaved.

`random` is now that shuffle on a stream forked as `mating`, so mating
draws do not advance the contact stream. The unmated parent in an odd
population is the last position of the permutation, which is uniform.
`ordered` keeps the identity sort and is not called random.
`disassortative` is unchanged and does not use the mating stream.

The acceptance window was set before this shuffler was run. Three
pairings of four parents are equally likely and two are heterotypic, so
48 seeds have expectation 32. The window is 24 to 40. Both an
identity-grouped labeling and an interleaved labeling fall inside it.
`ordered` still separates the two labelings.

## Round 2. A return that dies is not a sustained oscillation

Buckingham and Ashby (J. Evol. Biol., 2022, doi:10.1111/jeb.13981)
distinguish sustained fluctuating selection from a transient that damps.
The previous rule returned `stable` for

```text
host     A B A B A ∅ ∅ ∅
parasite P Q Q Q Q Q Q Q
```

with a debit on every step, because two paid returns and one parasite
change anywhere on the path were enough. The same path is now `extinct`.
The previous function is `classify_oscillation_v1` and still returns
`stable` there, so the detector change can be scored on a fixed path.

`stable` now requires two paid returns whose intervals contain a parasite
change, and the latest of those returns must fall on the last generation.
A host orbit after the parasite has already stopped changing is
`decoupled`. A return under a parasite that never moves is
`forced_fixed_antagonist`. A return with no debit, while the parasite did
move, is `forced_unpaid`. An empty host count followed by a later host
is `revived`.

## What changed the evaluation, and what did not

Seeds 101–108, outcross, virulence 32, 48 generations. Extinctions are 5
under `ordered` and 6 under `random`. Stable labels are 0 under both
detectors. At this virulence the mating rule moves one extinction and the
detector moves none.

At virulence 8 the split is visible. `ordered` with the old detector: 8
of 8 stable. `ordered` with the new detector: 6 of 8. `random` with the
old detector: 8 of 8. `random` with the new detector: 4 of 8. The mating
rule does not remove the old label. The new detector does, and it removes
more once the paths are the seeded pairings.

The separate block, the mixed census, and graded overlap remain 0 of 8
at virulence 32. The conjunction of a stable outcross cycle and selfing
extinction is 0 on the virulence grid from 8 to 40 and on birth ATP 8, 10,
and 12. The first virulence at which at least six selfing arms are
extinct is still 16, 20, and 24 for those three birth accounts. The flag
stays false.

`costless` and virulence 0 on `coevolve` share host and parasite
frequencies when the seed and the other settings match. `absent` does
not passage. The shared census stores founders, birth ATP, the mating
rule, recombination, the revision, both frequency paths, and a digest.
A changed birth ATP changes the digest. Replacing a field in the payload
and hashing it does not reproduce the stored digest.

## Execution

Python 3.11.2. The suite command was `PYTHONPATH=src python -m pytest tests -q --tb=line`.
That run reported 2138 passed, 1 failed, 1 skipped, and 1 xfailed. The
failure was a docstring in this file that contained the characters
`random.` and tripped the source scan which forbids the random module
outside `rng.py`. The sentence was rewritten. `tests/test_rng.py`,
`tests/closed_loop`, and the digest-policy sweep then passed. The full
suite was not started a second time after that wording change.
`tests/closed_loop` passed on its own, including the regressions that
failed on the previous revision before these edits.

