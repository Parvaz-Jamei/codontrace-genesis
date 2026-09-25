# Graded overlap and the virulence–birth table, seeds 101–108

The strict separate block passed on 1 of 8 seeds. The mixed census passed
on 0 of 8. Both are in
`docs/handoff/CLOSED_LOOP_CONFIRM_101_108_20260925.md`. This note finishes
the two clauses that were still open: graded overlap on the same seeds,
and the sensitivity table. The pass bar was not moved. `engine.py` was
not edited. `red_queen_proved` is false. `biological_red_queen_proved`
is false.

## Round 1. Partial match is a different interaction

Kouyos, Salathé, and Bonhoeffer (Theor. Popul. Biol. 75:1–13, 2009,
doi:10.1016/j.tpb.2008.09.007) found that a cost which grows with the
number of matched loci selects against recombination, unlike the
all-locus match. The graded weight is that second rule. It was not fit
to the strict result. Ashby (J. Evol. Biol. 33:1795–1805, 2020,
doi:10.1111/jeb.13718) is the other warning already in the locked rule:
if graded overlap reverses the block, the flag stays false.

The graded run uses the same six lines as the strict block. Exact overlap
pays 0.99 of the Holling debit. No shared locus pays 0. The repertoire
floor from the Euler helper is not on this clock.

## Round 2. The birth account is not a new endpoint

Holling type II is `virulence * H / (1 + H)`, taken from the host's own
ATP, and a birth is funded with a fixed account. Raising that account
must move the virulence at which a matched host is cleared, if the step
is that arithmetic rather than a hidden constant. The table therefore
crosses virulence 8, 10, …, 40 with birth ATP 8, 10, and 12, on seeds
101–108, strict weight, mutation 0.7, 48 generations.

A cell counts three things across the eight seeds: selfing × coevolve
extinct, outcross × coevolve with a debit-backed cycle, and the
conjunction of those with a living non-cycling frozen outcross and a
living frozen selfing. The conjunction is not the primary pass. The
primary pass also needs both absent arms alive and selfing alive at
virulence 8, and it is scored only at virulence 32 and birth ATP 10.
Holm (Scand. J. Stat. 6:65–70, 1979) is not applied. These cells are not
a family of tests being used to choose a winner. Simmons, Nelson, and
Simonsohn (Psychol. Sci. 22:1359–1366, 2011,
doi:10.1177/0956797611417632) is why a cell that looks closer to the bar
is not promoted into the endpoint.

## Graded block

Outcross × coevolve is extinct on all eight seeds. No seed passes. Frozen
outcross does not cycle. The one strict seed that had passed, 102, does
not pass under graded overlap, because the outcross arm is extinct there
too. Graded overlap reverses the survival of outcross. Passes: 0 of 8.

## Where the selfing step sits

The first virulence at which at least six seeds lose selfing × coevolve:

| Birth ATP | Virulence |
|---|---|
| 8 | 16 |
| 10 | 20 |
| 12 | 24 |

Below that step the extinct count is 0 or 1. From the step through
virulence 40, on every birth account, the counts stay at 6 extinct
selfing arms, 2 outcross arms with a debit-backed cycle, and 1 seed in
the conjunction. Virulence 32 with birth ATP 10, the primary cell, is on
that plateau: 6, 2, and 1. It is the same 1-of-8 conjunction already
recorded for the strict block. The step moves by four virulence units
when the birth account moves by two. That is the Holling debit against
the birth account, not a second Red Queen threshold.

One cell is not on the step and not on the plateau. Birth ATP 12 at
virulence 14 has a debit-backed cycle on all eight outcross arms, and
selfing is extinct on none of them. The conjunction is 0. Cycles without
the extinction gap do not clear a line of the primary rule.

No cell reaches a conjunction of 6. The sensitivity table does not
reopen the flag.

## The locked rule, applied

Strict separate block: 1 of 8. Mixed census: 0 of 8. Graded block: 0 of
8. The flag requires all three at 6 of 8. It is false.
`biological_red_queen_proved` is false. The two-fold cost of sex is not
applied. The mixed census is a haploid codon. Morran et al. (Science
333:216–218, 2011, doi:10.1126/science.1206360) is not repeated here.
