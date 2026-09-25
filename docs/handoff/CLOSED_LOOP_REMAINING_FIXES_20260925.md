# What was still wrong, and what changed

Revision stays `p6-review-20260925` in spirit and the code version string is
unchanged except where a record gained fields. `engine.py` was not edited.
`red_queen_proved` is false. Sexual maintenance is not claimed.

## Round 1. Mate choice still had to be shown, not only offered

Nuismer, Otto, and Cornell (Ecol. Lett. 11:921–934, 2008,
doi:10.1111/j.1461-0248.2008.01207.x) treat disassortative mating as its own
trait. The parameter existed. The development seed had not been run under
both rules. On seed 7, outcross, virulence 32, 48 generations: random
mating with recombination leaves 4 hosts and the class `forced`. The same
run with disassortative mating goes extinct. Recombination off, random
mating, is class `none`. Disassortative mating does not rescue a cycle.
It is not the default.

## Round 2. A gap without a success is not a low-debit exception

`low_debit_gap` was set whenever any positive virulence had a survival
gap, including when no virulence had met the full rule. There is then no
threshold for a cell to lie below. That flag is now true only when a
first tested success exists and a cheaper cell also has the survival gap.
A gap that never meets the cycle clause is `unqualified_survival_gap`.
On the development factorial that flag is true and `low_debit_gap` is
false. `first_tested_success` stays absent.

## Round 3. The parasite stock was not the length it was given

`_passage` always wrote 12 new parasites. A stock of another length was
put back to 12 on the next generation, so the fixed-size assumption could
not be varied and the flag `parasite_stock_fixed` compared every run with
12. Renewal now keeps the length it received. Gandon and Michalakis
(J. Evol. Biol. 15:451–462, 2002, doi:10.1046/j.1420-9101.2002.00402.x)
show that population size changes evolutionary potential. It is a
sensitivity, not a new endpoint.

Seeds 101–108, virulence 32, strict, random mating. Outcross arms in the
stable class: 0 at stock 6, 12, and 24. Selfing extinctions: 3, 6, and 5.
The stock size moves the selfing count. It does not produce the missing
stable cycle. The flag stays false.

## Round 4. The mixed record could not be audited

The shared census applied `mate_choice` and `recombine` and then did not
store them, and it stored host names without counts. It now stores the
mating rule, birth ATP, both frequency paths, the oscillation class, the
stock length, and the same statement that births are a passage reset.

## Round 5. The digest has to be checkable

`digest_matches` recomputes the hash of the record with the digest field
removed. A record that cannot be hashed back to itself is not a
reproduction. The check passes on a fresh arm.
