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

## 5. The chase kills selfing, and that is still not sex maintained

This contrast was already on the virulence grid of the `0.3.0b10` code. The
accept tests are what name it. No engine change.

At virulence 20 and at 32 a one-copy hit costs at least the birth account
of 10. Selfing × coevolve goes extinct. Generation 0 removes the three
hosts on the ancestral window `000111`. The antagonist then moves onto the
remaining `111000`, and generation 1 removes that last host. Debits are
`3, 1, 0, 0`.

The same selfing founders under a frozen window do not go extinct. The
antagonist stays `000111`, misses `111000`, and the later debits are
`3, 0, 0, 0`. One host is alive at generation 3. `absent` pays nothing
and keeps all four founders' window types.

The selfing extinction therefore needs the window update. That is the sign
a chase has to show before anyone talks about maintaining sex. It is not
the flag. Outcross × coevolve at these two virulences is the unpaid name
orbit in section 3: not extinct, `cycles` false. Morran et al. (Science
333:216–218, 2011, doi:10.1126/science.1206360) reported that obligate
selfers were lost under a coevolving pathogen while outcrossers persisted,
and that the difference went away when the pathogen was held fixed. Only
the selfing half of that pattern is on this grid. The sexual arm is not
paying inside the repeat, so `red_queen_proved` stays false.

## 6. Four follow-ups on the same clock

These four runs use `run_match_arm` and `run_shared_modifier`. They do not
edit `engine.py`. Ashby (J. Evol. Biol. 33:1795–1805, 2020,
doi:10.1111/jeb.13718) showed that a diversity advantage can keep sex
without Red Queen dynamics. Agrawal (Evolution 63:2131–2141, 2009,
doi:10.1111/j.1558-5646.2009.00695.x) showed that a diploid modifier of sex
is usually segregation, not recombination. The census below is a haploid
mating codon. It is not that diploid invasion, and Maynard Smith's
two-fold cost is not applied (`two_fold_cost_applied` is false; the only
sex debit is `mating_effort_atp`).

### The extinction gap closes when the window is held fixed

At virulence 20 and at 32, four generations:

| Passage | Outcross extinct | Selfing extinct |
|---|---|---|
| coevolve | no | yes |
| frozen | no | no |
| absent | no | no |

The gap "outcross lives and selfing does not" is present only while the
antagonist window updates. Freezing the window, or skipping the debit,
removes it. Outcross itself does not die under the freeze, and its
`cycles` flag under coevolve stays false. At virulence 18 the one-copy
Holling cost is 9, below the birth account, and selfing × coevolve is not
extinct, so there is no gap there either. This is the passage contrast in
Morran et al. (2011) for the selfing death. It is not the flag.

### Twenty generations do not make the pure outcross arm start paying

Outcross × coevolve, virulence 20, 20 generations: match debits are `2`
followed by nineteen zeros. The two window sets still alternate, so
`frequency_cycles` is true and `debit_backed_cycle` is false. The unpaid
orbit is the exchange, not a short horizon. The same shape holds at
virulence 16 and 32.

### The extinction step is the Holling edge, not a fitted threshold

Birth ATP is 10. Holling type II on three copies is `virulence * 3/4`, and
on one copy is `virulence / 2`. A step of 2 from 8 through 32:

| Virulence | H=3 cost | H=1 cost | Selfing × coevolve | Selfing × frozen | Outcross × coevolve |
|---|---|---|---|---|---|
| 12 | 9 | 6 | 4 hosts | 4 hosts | alive, not a debit-backed cycle |
| 14 | 10.5 | 7 | 1 host | 1 host | alive |
| 18 | 13.5 | 9 | 1 host | 1 host | alive |
| 20 | 15 | 10 | extinct | 1 host | alive, `cycles` false |
| 22 through 32 | above 16 | at least 11 | extinct | 1 host | alive, `cycles` false |

The common window drops out once three-copy cost exceeds 10, which is
first seen at virulence 14. The chased selfing lineage dies once one-copy
cost reaches 10, which is virulence 20, and not at 18. No intermediate
regime sits between those two even steps. Outcross does not go extinct
anywhere on this step.

### A shared antagonist flips which codon remains, and the late orbit is unpaid

Founders in one population: three selfing tapes (`000111`, `000111`,
`111000`) and two outcross tapes (`000111`, `111000`). Eight generations.
Outcross pairs only with outcross. A single leftover outcross codon leaves
no child. That is mate limitation, not the two-fold cost.

At virulence 20:

| Passage | Outcross counts | Selfing counts | Match debits |
|---|---|---|---|
| coevolve | `2,2,2,2,2,2,2,2` | `1,1,0,0,0,0,0,0` | `2,0,1,0,0,0,0,0` |
| frozen | `2,1,0,0,0,0,0,0` | `1` eight times | window stays `000111`; the last host is `111000` |
| absent | `2` eight times | `3` eight times | all zero |

Under coevolution the selfing codon is gone by generation 2 and the
outcross count stays 2. Under a frozen window the outcross codon is gone
by generation 2 and one selfing host remains. With no debit, neither count
moves. `debit_backed_cycle` is true on the coevolve row because the debit
at generation 2 sits inside the first return of a window set. Generations
3 through 7 pay nothing. That true value is the transitional debit that
removes the last selfer, not a cost the sexual codon keeps paying.

At virulence 16 both codons stay (outcross 2, selfing 1) and match debits
continue under coevolve (`2,0,1,0,1,0,1,0`) and under frozen
(`2,1,0,1,0,1,0,1`). Ongoing payment here is not specific to a moving
window. That is the separation Ashby (2020) requires.

A lone outcross codon among selfers is unmated in generation 0 and its
count stays 0 even with the debit off. Four founders on one window
(`000111` twice selfing and twice outcross) all die at virulence 20 under
coevolve, and all four remain under `absent`. Exchange has nothing to
mismatch against. `red_queen_proved` on every shared record is false.

## What this cut does not contain

No diploid sex-modifier invasion of the kind in Agrawal (2009). No
two-fold cost of sex. No claim that a parasite maintained sex. No change
to `engine.py`. Morran et al. (Science 333:216–218, 2011,
doi:10.1126/science.1206360) is not repeated here.
