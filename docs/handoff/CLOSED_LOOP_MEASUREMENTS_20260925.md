# Closed-loop measurements, 2026-09-25

Four questions. Each one was run on this tree before the version cut.
`engine.py` was not edited. `biological_red_queen_proved` is false.
`red_queen_proved` is false. The host–parasite profile still raises on
`assert_claim_allowed("red_queen_proved")`.

## 1. Intelligence is not an output of this run

The open problem is definitional before it is empirical. Legg and Hutter
(Minds and Machines 17:391–444, 2007, doi:10.1007/s11023-007-9079-x) collect
informal definitions and still need an external reward and a universal
mixture before a scalar exists. This library does not compute that scalar.

On the `alife` profile the blocked set includes `intelligence`,
`collective_intelligence`, `agi`, and `tokyo_type1_passed`. On
`host_parasite`, `assert_claim_allowed` raises for `intelligence`,
`collective_intelligence`, `agi`, and `red_queen_proved`. The HE01 bundle
writes those three intelligence keys as false. Nothing in the closed-loop
census sets them.

## 2. A pure mating arm is not selection on sex

Agrawal (Evolution 63:2131–2141, 2009, doi:10.1111/j.1558-5646.2009.00695.x)
showed that haploid models make sex and recombination the same operator,
while diploid selection on sex is often segregation, not recombination.
Otto and Nuismer (Science 304:1018–1020, 2004, doi:10.1126/science.1094072)
found that species interactions usually select against sex. Otto
(J. Heredity 112:9–18, 2021, doi:10.1093/jhered/esaa026) leaves open whether
natural populations carry enough selected alleles for selective interference
to explain obligate sex.

What was run: `resolve_copy_self_mode` returns `chamber` for codon `001` and
`asexual` for codon `000` when the locus is enabled. `ClosedLoopP5Session.boot`
stamps one codon onto every founder. A selfing boot of four organisms yields
only `000`. An outcross boot yields only `001`. The two codons do not meet,
so no frequency slope was recorded. A new birth rule was not added. Ashby
(J. Evol. Biol. 33:1795–1805, 2020, doi:10.1111/jeb.13718) is the reason a
later slope, if it is measured, still has to be separated from a stable
diversity advantage that does not cycle.

## 3. The virulence-32 name flip is not a cycle clause

Outcross × coevolve, virulence 32, four generations, birth ATP 10:

| Generation | Match debits | Window set |
|---|---|---|
| 0 | 2 | `000000`, `111111` |
| 1 | 0 | `000111`, `111000` |
| 2 | 0 | `000000`, `111111` |
| 3 | 0 | `000111`, `111000` |

`frequency_cycles` on that history is true. `debit_backed_cycle` is false,
and the arm's `cycles` flag is false. Holling type II at H=1 is
`virulence / 2`: 16 at virulence 32, 10 at 20, 8 at 16. Birth ATP is 10.
A one-copy hit at virulence 32 empties the account. The same unpaid orbit
is already present at virulence 16 on outcross × coevolve: debits
`2, 0, 0, 0`, not extinct, `cycles` false. Virulence 32 is not a separate
onset, and the density shape is not identified on that outcross arm.

Density does separate selfing at virulence 16. Holling type II on three
copies is `16 * 3/4 = 12`, above the birth account, and on one copy is 8,
below it. Generation 0 removes the common window. The survivor is
`111000`. Under coevolve the antagonist moves to that window and debits it
on generations 1–3 (`3, 1, 1, 1`) without emptying the account, so the arm
is not extinct and the type-set does not return through a different set.
Under frozen the antagonist stays `000111`, which misses `111000`, and
later debits are `3, 0, 0, 0`. At virulence 20 the one-copy cost equals
10, the hit drains the birth account, and selfing × coevolve is extinct
(`3, 1, 0, 0`). The same extinction holds at 32. Outcross × coevolve is
not extinct at 16, 20, or 32, and its `cycles` flag stays false. A
survival gap without a debit inside the repeat is not the maintenance of
sex.

## 4. A paid name flip under a frozen window is still not the flag

Frozen passage, virulence 16, outcross: match debits are `2, 1, 0, 1`.
The same two window sets alternate, and `debit_backed_cycle` is true because
generations 0, 1, and 3 pay. The antagonist window stays `000111`. A cycle
clause that ignores whether types update would accept this arm.

The factorial does not select that arm. No cell on the declared grid
clears the full rule, so the chosen row is the last survival gap,
virulence 64. On that row the frozen outcross debits are `2, 1, 0, 0` and
`cycles` is false, so `frozen_cycles` on the factorial is false.
`low_debit_gap` is true because selfing × coevolve is already extinct at
20, 32, and 64 while outcross × coevolve is not. `pattern_holds` is false,
`debit_threshold` is unset, and `red_queen_proved` is false. Ceiling
remains `runtime_observation`. The paid flip at virulence 16 is not
`factorial.frozen_cycles`.

`absent` still skips the window update together with the debit, so it is
not a pure zero-debit cut (Pearl, Biometrika 82:669–688, 1995,
doi:10.1093/biomet/82.4.669). That split was not added.

## What this cut does not contain

No mixed-population modifier trial. No claim that a parasite maintained
sex. No change to `engine.py`. Morran et al. (Science 333:216–218, 2011,
doi:10.1126/science.1206360) is not repeated here.
