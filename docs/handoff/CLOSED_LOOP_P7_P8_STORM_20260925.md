# Two reviews before the shared census and the specificity weight

Written before the code change, checked against the run after it.
Commit on `main`. `engine.py` was not edited. `red_queen_proved` is false.

## Round 1. What the papers change

Kouyos, Salathé, and Bonhoeffer (Theor. Popul. Biol. 75:1–13, 2009,
doi:10.1016/j.tpb.2008.09.007) separate two infection rules. Matching
every locus is strong epistasis. A cost that grows with the number of
matched loci is a different interaction, and in their models it selects
against recombination. The closed loop's exact window test is the first
rule. A graded weight is the second. It must be allowed to remove a
pattern that exact equality produced. It is not a second population.

Agrawal and Lively (Evol. Ecol. Res. 4, 2002, "Infection genetics:
gene-for-gene versus matching-alleles models and all points in between")
place the two rules on one axis. Partial specificity is a weight on the
existing debit, not a new life cycle. A later review of that continuum
(PLoS Comput. Biol. 8:e1002633, 2012, doi:10.1371/journal.pcbi.1002633)
records host-parasite specificities that are neither pure matching-allele
nor gene-for-gene. That is why the graded clause exists, and why a
positive strict result is not automatically a graded result.

Ashby (J. Evol. Biol. 33:1795–1805, 2020, doi:10.1111/jeb.13718) still
applies: a debit that does not require the window to move can keep a
mating codon. The virulence-16 shared census, below, is that case.

## Round 2. What the clock will and will not do

The shared census was the last caller of the survivor-modal update. It
pointed the parasite at the living host. That is the same defect already
removed from `run_match_arm`. The census now uses the same contact and
the same passage: parasites that matched are the next stock, a miss
resamples the whole stock, and a frozen stock stays on the ancestral
window. No new population class. No second ATP account.

`graded_alpha_from_overlap` returns a positive floor when the task sets
do not overlap. Putting that floor on the ATP clock would tax a host
that matches no locus. The clock pays 0 in that case. Exact overlap uses
the function and is 0.99, not 1. The default weight stays strict
equality, so the seed-7 factorial is the same endpoint as before.

Not done in this cut, and not to be smuggled in after seeing the table:
the Euler stepper, a new mutation rate, seeds 101–108, and any copy of
`pattern_holds` into `red_queen_proved`.

## What the run did

Shared founders: three selfing (`000111`, `000111`, `111000`) and two
outcross (`000111`, `111000`). Seed 7, mutation 0.7, strict weight.

At virulence 20 the outcross counts are `(2, 1, 0, 0, 0, 0, 0, 0)` under
both coevolution and a frozen stock. One selfing host remains in both.
The coevolving stock ends on `001111`. The living host window is
`111000`. The parasite did not copy the survivor. Absent keeps two
outcross and three selfing and debits nothing.

At virulence 16 both codons remain under both passages. The frozen stock
keeps the debit `(2, 1, 0, 1, 0, 1, 0, 1)`. Coevolution pays `(2, 1)` and
then nothing. Ongoing payment here is not evidence that the stock is
moving.

Graded weights, checked directly: exact window 0.99, no locus in common
0, three loci in common 0.451. A frozen selfing generation at virulence
32 still records 9 debits, the same count as strict, because an exact
match at that virulence still spends the birth account. The factorial
flag stays false.

The two-fold cost is not applied. The census is a haploid codon, not an
Agrawal modifier. Morran et al. (2011) is not repeated here.
