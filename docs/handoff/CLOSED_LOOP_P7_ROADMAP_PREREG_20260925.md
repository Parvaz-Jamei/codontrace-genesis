# Closed-loop phases 7–13: preregistered roadmap, 2026-09-25

Status of the tree this document was written against: commit `a7dab14` on
`main` and `closed-loop-p5`. `engine.py` has no domain words.
`red_queen_proved` is false. `biological_red_queen_proved` is false.
`assert_claim_allowed("red_queen_proved")` still raises on the
`host_parasite` profile.

This file is the pre-registration for any later campaign. It was written
before confirmatory seeds 101–108 were run. Those seeds must not be
inspected, and the clauses below must not be edited, before that campaign
finishes. Nosek et al. (Proc. Natl. Acad. Sci. USA 115:2600–2606, 2018,
doi:10.1073/pnas.1708274114) separate prediction from postdiction. A rule
moved after the numbers are seen is a postdiction.

## Where the tree actually is

Phases 1–6 are on one ATP clock: `GenesisOrganism.atp_state`,
`assert_single_atp_owner`, mating codon `001` / `000`, Holling type II,
and a parasite stock. The measurements that still describe a
survivor-modal update are sections 3–5 of
[CLOSED_LOOP_MEASUREMENTS_20260925.md](CLOSED_LOOP_MEASUREMENTS_20260925.md).
That update aimed the parasite at the hosts that had escaped. It is not
what `run_match_arm` does now.

What `run_match_arm` does now, and what the accept tests lock:

- Twelve hosts: nine `000111`, three `111000`. Twelve parasites start on
  the ancestral modal `000111`.
- Each host contacts one parasite. A match debits that host's own ATP.
- `coevolve`: the next parasite generation is drawn from the parasites
  that matched, or from the whole stock if nobody matched, then each
  offspring flips one recognition bit with probability 0.7.
- `frozen`: the stock stays on `000111` and does not mutate.
- `absent`: no debit. This is not a pure zero-debit intervention, because
  it also skips the update (Pearl, Biometrika 82:669–688, 1995,
  doi:10.1093/biomet/82.4.669).
- Declared replay: `RNGManager` seed 7, 48 generations, mutation 0.7.
  On the grid `(0, 1, 4, 8, 16, 32, 64)` the digital predicate first
  holds at virulence 32. `pattern_holds` is true there.
  `debit_threshold` is 32. `low_debit_gap` is false. Selfing × coevolve
  is extinct. Outcross × coevolve is alive and `cycles` is true. Frozen
  outcross does not cycle. Frozen selfing is alive. Absent extincts
  nobody.
- Seed 1 on the same grid does not meet the predicate.
- Four generations at virulence 32 do not extinguish selfing.
- `red_queen_proved` is not copied from `pattern_holds`.

Seed 7 and mutation 0.7 were chosen after a scan of seeds and rates.
Kriegeskorte et al. (Nat. Neurosci. 12:535–540, 2009,
doi:10.1038/nn.2303) call it circular to select the analysis on the same
data used to confirm it. Seed 7 is a demonstration that the corrected
passage can meet the digital predicate. It is not the confirmatory
sample. Simmons, Nelson, and Simonsohn (Psychol. Sci. 22:1359–1366, 2011,
doi:10.1177/0956797611417632) are why the confirmatory seeds are listed
below before they are run, and why a failed clause is not repaired by
changing the mutation rate.

`run_shared_modifier` is a different function. It still sets the single
antagonist window from the modal living host. Section 6 of the
measurements file describes that function. It must not be reused as the
phase 9 census until it passages from matches, on the same rule as
`run_match_arm`.

`host_parasite_type2_rq.py` is still a separate Euler stepper. It cites
Rabajante et al. (Sci. Rep. 5:10004, 2015, doi:10.1038/srep10004), builds
a diagonally dominant specificity matrix, and keeps `red_queen_proved`
false even when `cycling_detected` is true. It does not construct a
`GenesisOrganism` and it does not debit the shared ATP ledger. Exact
equality of a 6-bit window is still the infection test inside
`run_match_arm`.

The two-fold cost of sex is not applied. The only sex debit is
`mating_effort_atp`. Hamilton, Axelrod, and Tanese (Proc. Natl. Acad.
Sci. USA 87:3566–3573, 1990, doi:10.1073/pnas.87.9.3566) treat that
two-fold cost as the claim that has to be met. A later true flag, if the
clauses below pass, still will not mean the two-fold cost was paid.

## Five reviews

### 1. Experimental evolution

Morran et al. (Science 333:216–218, 2011, doi:10.1126/science.1206360)
ran three treatments on *Caenorhabditis elegans* and *Serratia
marcescens*: coevolution, evolution (hosts change, the pathogen is not
passaged with them), and a control. Obligate selfing populations went
extinct within twenty generations under coevolution, and did not go
extinct under evolution or under the control. That is the extinction
knockout.

The mixed-mating result is not the same knockout. Outcrossing in
wild-type populations rose from about 20% to above 70% over eight
generations in both the evolution treatment and the coevolution
treatment (F(2,11) = 8.26, P = 0.006). A rise that also happens when the
pathogen is not coevolving is not, by itself, evidence that coevolution
maintained sex.

Gibson and Lively (Am. Nat. 192:537–551, 2018, doi:10.1086/699829) show
parasite-mediated selection that periodically favors sex and periodically
favors asex. One horizon on which an outcross codon is common is not
maintenance.

Consequence for the roadmap: a freeze control on separate outcross and
selfing populations (the old phase 8) is the extinction half, and on
seed 7 at virulence 32 it is already in the accept tests. It does not
license the flag. The mixed-population half has to be allowed to come
out negative, because that is a possible reading of the mixed Morran
result and it is the usual theoretical result reviewed next.

### 2. Population genetics

Agrawal (Evolution 63:2131–2141, 2009,
doi:10.1111/j.1558-5646.2009.00695.x) compared modifiers of sex and
modifiers of recombination in diploid hosts. In matching-allele
simulations, recombination modifiers were favored more often than sex
modifiers (about 53% against about 6%). The direction of selection on
sex was usually segregation, not recombination. A haploid tape whose
mating codon only switches a window exchange is not that diploid
modifier. Otto and Nuismer (Science 304:1018–1020, 2004,
doi:10.1126/science.1094072) found that species interactions usually
select against sex and recombination.

Consequence: phase 9 is a haploid mating codon sharing one parasite
stock. It is not an Agrawal modifier and it is not allowed to grow a new
birth engine to imitate one. If the outcross codon does not increase
under coevolution relative to freeze, the recorded result is that
negative. The flag stays false. The census must not self-pair a lone
outcross codon; an unmated codon leaves no offspring. That is mate
limitation, not Maynard Smith's two-fold cost.

### 3. Epidemiology and the specificity matrix

Ashby (J. Evol. Biol. 33:1795–1805, 2020, doi:10.1111/jeb.13718) showed
that a stable diversity advantage can maintain sex with no Red Queen
fluctuation. A survival gap without a debit-backed cycle, or a cycle
that also appears under a frozen window, is that other mechanism. The
existing predicate already rejects both. Graded overlap can create a
diversity advantage that looks like a gap. Phase 7 has to show that the
confirmatory result is not only that advantage.

Holling type II is already the debit shape: cost = virulence × H / (1 + H)
with H the count of the contacted window. On the old four-host arm the
extinction step sat on birth ATP 10. On the corrected passage, seed 7,
the digital predicate starts at virulence 32, not at 20. Phase 11 has to
be rerun on `run_match_arm`. Rerunning it on the withdrawn survivor-modal
numbers would certify a bug.

The type II file's Euler stepper is the wrong object to "wire in". It
integrates densities. The clock debits ATP of individuals. The piece that
belongs inside the clock is the specificity weight: a diagonally
dominant matrix, or the graded overlap already coded as
`graded_alpha_from_overlap`, multiplies the Holling debit. Super-host
and super-parasite rows stay forbidden by the checks already in that
file. The Euler loop, the carrying-capacity parameter, and a second
population of floats do not move into `closed_loop_p6.py`.

### 4. Causality and the confirmatory sample

The primary endpoint is one number: virulence 32, on the grid already
declared, at mutation 0.7, 48 generations, birth ATP 10, twelve hosts,
twelve parasites. Other virulences and other birth ATP values are
secondary. They cannot rescue a failed primary. If several virulences
are tested as a family, the adjustment is Holm (Scand. J. Stat. 6:65–70,
1979), not a silent look at the smallest P.

The frequency contrast in the mixed census, if it is estimated, uses the
seed as the independent unit. A BCa interval (Efron, J. Am. Stat. Assoc.
82:171–185, 1987, doi:10.1080/01621459.1987.10478410) is computed across
seeds, not across generations inside one trajectory. Generations in one
trajectory are not independent draws.

`frozen` holds the parasite stock at the ancestral window. That is the
evolution-treatment analogue. `absent` removes the debit and the update
together. Do not call `absent` a knockout of virulence alone. A pure
zero-debit arm, with the stock still allowed to update, is not in this
pre-registration and must not be added after the confirmatory run in
order to change the flag.

### 5. What may change in the code, and what may not

May change, and only this:

- The match debit inside `run_match_arm` and the mixed census may be
  multiplied by a specificity weight in `[0, 1]`, computed from the two
  windows, using the graded overlap or a diagonally dominant matrix
  already defined in `host_parasite_type2_rq.py`. The weight is applied
  where `debit_runtime` is called. No second ledger.
- `run_shared_modifier` may call the same contact-and-passage helpers as
  `run_match_arm`. It may not keep the survivor-modal assignment.
- Birth ATP may be a parameter of a secondary sensitivity table. The
  primary endpoint stays at 10.
- Tests and the measurements file may record the confirmatory outcome,
  including a negative one.

May not change:

- `engine.py`. A diff that adds a domain word is rejected even if a plot
  looks right.
- `assert_single_atp_owner`. Parasites and hosts are
  `GenesisOrganism` objects. Their ATP is the motor's ATP.
- Copying `pattern_holds` into `red_queen_proved`.
- Setting `biological_red_queen_proved` to true.
- Choosing a new mutation rate, a new seed, or a new generation count
  after seeing seeds 101–108.
- Treating seed 7 as one of the confirmatory seeds.
- Importing the Euler stepper into the closed loop.
- Claiming Morran et al. (2011) was repeated.

## Locked rule for `red_queen_proved`

The flag may be set true only if every clause below is true on the
confirmatory run. If one clause fails, the flag stays false and the
failure is the result. There is no second campaign inside the same
document.

Confirmatory seeds, in this order, not previously used for this passage:
101, 102, 103, 104, 105, 106, 107, 108.

Fixed inputs, primary endpoint: mutation 0.7, 48 generations, birth ATP
10, twelve hosts (nine `000111`, three `111000`), twelve parasites on
`000111`, virulence 32, passages `coevolve`, `frozen`, and `absent`,
matings `outcross` and `selfing`. Strict window equality is the primary
infection test. The graded-weight run is a separate clause, not a
replacement of this one.

A seed passes the separate-population block when all of these hold:

1. Outcross × coevolve is not extinct, and `debit_backed_cycle` is true.
2. Selfing × coevolve is extinct.
3. Outcross × frozen is not extinct, and `debit_backed_cycle` is false.
4. Selfing × frozen is not extinct.
5. Outcross × absent is not extinct, and selfing × absent is not extinct.
6. At virulence 8, with every other input unchanged, selfing × coevolve
   is not extinct.

The block passes if at least 6 of the 8 seeds pass all six lines. A 5/8
split fails.

The mixed census uses the same seeds, the same parasite passage, and
these founders: three selfing tapes (`000111`, `000111`, `111000`) and
two outcross tapes (`000111`, `111000`). A seed passes the mixed block
when the outcross count divided by the living count at generation 48 is
strictly greater under `coevolve` than under `frozen`, both denominators
are positive, and the unmated-outcross count at generation 0 is 0. If a
denominator is 0, the seed fails the mixed block. The mixed block passes
if at least 6 of 8 seeds pass. This contrast is allowed to fail. Failure
here keeps the flag false even if the separate-population block passes.

The graded clause: repeat the separate-population block with the Holling
debit multiplied by the graded overlap of the two windows, specificity
not refit. The same 6-of-8 rule applies. If graded overlap reverses the
block, the flag stays false. That is the Ashby check.

Replay: two calls with the same seed and the same inputs return equal
`to_dict()` values. A mismatch fails the campaign.

Only if the separate-population block, the mixed block, the graded
clause, and the replay check all pass, `red_queen_proved` may be set
true on that confirmatory record. `biological_red_queen_proved` stays
false. `claim_ceiling` stays `runtime_observation`. The measurements
file states that the two-fold cost was not applied, that the mixed
census is a haploid codon, and that seed 7 was not in the confirmatory
set.

## Order of work

Do these in order. Do not start a later step by widening an earlier one.

1. Move the match passage helpers so the mixed census cannot use a
   survivor-modal update. No new population class.
2. Multiply the existing Holling debit by a specificity weight. Default
   weight 1, so the primary endpoint is unchanged until the graded clause.
   Do not import the Euler stepper.
3. Run virulence 8 and virulence 32 on seeds 101–108 for the separate
   populations, strict equality, birth ATP 10. Write the eight outcomes
   before looking at a mixed frequency.
4. Run the mixed census on the same seeds. Record the frequency contrast
   and, across seeds, a BCa interval only as a description. The pass rule
   is the 6-of-8 count above, not whether the interval excludes zero.
5. Repeat the separate-population block with graded overlap.
6. Apply the locked rule. Set the flag only if every clause passed.
   Write the negative, if that is the outcome, with the same care.

Secondary tables, after the flag decision and not allowed to reopen it:
virulence steps of 2 from 8 to 40, and birth ATP in {8, 10, 12}, on the
same eight seeds. Label them sensitivity. Holm applies if those cells
are treated as a family of tests. They are not a new primary endpoint.

## What a finished campaign file contains

One table per seed for the primary endpoint, the virulence-8 check, the
mixed counts, and the graded block. The 6-of-8 tallies. The flag value
and the biological flag, side by side. The statement that `engine.py`
did not change. The citations in this document, not a new set chosen
because they agree with the outcome. No sentence that says a parasite
maintained sex in nature, and no sentence that says Morran et al. (2011)
was reproduced.
