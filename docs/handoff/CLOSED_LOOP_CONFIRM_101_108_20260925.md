# Confirmatory seeds 101–108, separate populations and the mixed census

The rule was locked in
`docs/handoff/CLOSED_LOOP_P7_ROADMAP_PREREG_20260925.md` before these seeds
were run. It was not edited after the table below. `engine.py` was not
edited. Mutation stays 0.7. Horizon stays 48 generations. Birth ATP stays
10. Specificity stays strict. Primary virulence is 32. Virulence 8 is only
the check that selfing × coevolve is still alive.

## Round 1. What a failed bar is

Nosek et al. (Proc. Natl. Acad. Sci. USA 115:2600–2606, 2018,
doi:10.1073/pnas.1708274114) draw the line between a prediction and a
result that was fit afterwards. Seeds 1–12 and seed 7 were already seen.
They are not in this table. Kriegeskorte et al. (Nat. Neurosci. 12:535–540,
2009, doi:10.1038/nn.2303) is why a seed that passes is not then used to
choose a new mutation rate.

Otto and Nuismer (Science 304:1018–1020, 2004,
doi:10.1126/science.1094072) and Agrawal (Evolution 63:2131–2141, 2009,
doi:10.1111/j.1558-5646.2009.00695.x) both expect selection against sex
under many matching-allele regimes. A bar that is missed is a result, not
a broken clock.

Morran et al. (Science 333:216–218, 2011, doi:10.1126/science.1206360)
saw obligate selfers go extinct under coevolution and not under the
evolution treatment. In the mixed wild-type populations, outcrossing rose
under both the evolution treatment and coevolution. A mixed codon whose
frequency does not rise under coevolution relative to a frozen stock is
not a failure to copy that mixed figure. The figure was not
coevolution-specific.

## Round 2. What this cut will not do

The pass bar is 6 of 8 seeds, written before the run. One primary
virulence means Holm's adjustment is not applied (Scand. J. Stat. 6:65–70,
1979, would apply only if this cut had searched a family of virulences).
A BCa interval across seeds (Efron, J. Am. Stat. Assoc. 82:171–185, 1987,
doi:10.1080/01621459.1987.10478410) is not the pass rule. The pass rule is
the count.

`absent` still removes the debit and the update together. It is not a
pure virulence knockout (Pearl, Biometrika 82:669–688, 1995,
doi:10.1093/biomet/82.4.669).

The graded-overlap clause was not run. The locked rule needs that clause
as well as these two blocks. This report cannot set `red_queen_proved`.
`biological_red_queen_proved` stays false. The two-fold cost of sex is
not applied. The mixed census is a haploid mating codon, not a diploid
modifier.

No second grid, no new seeds, and no new mutation rate follow from the
numbers below.

## Separate populations

A seed passes only when, at virulence 32, outcross × coevolve is alive and
`debit_backed_cycle` is true, selfing × coevolve is extinct, outcross ×
frozen is alive and not cycling, selfing × frozen is alive, both absent
arms are alive, and selfing × coevolve is alive at virulence 8.

| Seed | Passed | Outcross coevolve extinct, cycles | Selfing coevolve extinct | Outcross frozen cycles | Selfing extinct at virulence 8 |
|---|---|---|---|---|---|
| 101 | no | no, no | yes | no | no |
| 102 | yes | no, yes | yes | no | no |
| 103 | no | no, no | yes | no | no |
| 104 | no | no, yes | no | no | no |
| 105 | no | no, no | yes | no | no |
| 106 | no | no, no | no | no | no |
| 107 | no | no, no | yes | no | no |
| 108 | no | no, no | yes | no | no |

Passes: 1 of 8. The block fails. Frozen outcross did not cycle on any of
these seeds, and no absent arm went extinct. The usual miss is the
debit-backed cycle on the outcross coevolve arm. Selfing goes extinct
under coevolution on six seeds, which is the extinction half without the
cycle half. Seed 102 is the only seed that has both, and it is one seed,
not six.

## Mixed census

Founders: selfing `000111`, `000111`, `111000`, and outcross `000111`,
`111000`. Frequency is the outcross count divided by the living count at
generation 48. A seed passes when that frequency is strictly higher under
coevolution than under the frozen stock, both denominators are positive,
and the generation-0 unmated outcross count is 0.

| Seed | Passed | Coevolve outcross, selfing | Frozen outcross, selfing |
|---|---|---|---|
| 101 | no | 0, 1 | 0, 1 |
| 102 | no | 0, 1 | 0, 1 |
| 103 | no | 0, 1 | 0, 1 |
| 104 | no | 0, 1 | 0, 1 |
| 105 | no | 0, 1 | 0, 1 |
| 106 | no | 0, 1 | 0, 1 |
| 107 | no | 0, 0 | 0, 1 |
| 108 | no | 0, 1 | 0, 1 |

Passes: 0 of 8. The block fails. Generation 0 has no unmated outcross
codon on any seed. At virulence 32 the outcross codon is gone under both
passages. Coevolution does not raise its frequency above the frozen
stock. On seed 107 the coevolving population is gone as well, so that
seed has no frequency.

`red_queen_proved` is false. `biological_red_queen_proved` is false.
Morran et al. (2011) is not repeated here.
