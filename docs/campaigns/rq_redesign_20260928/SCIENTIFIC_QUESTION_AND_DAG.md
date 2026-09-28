# Scientific question and causal graph for the rare-class advantage in the host–antagonist life loop

**Date:** 2026-09-28
**Base commit:** `7cfba3fc59b4d6dcd80895ea283eb5a69fdf7c72` (`7cfba3f`), `main`
**Campaign:** `rq_redesign_20260928`
**Status:** design document, written before any confirmatory run
**Scope:** the open question of the host–antagonist submodule. This document fixes the
question, the competing explanations, the sign and lag of every causal link, the target
estimand, the unit of replication and the falsification conditions. It fixes no result.
`red_queen_proved` and `biological_red_queen_proved` remain false throughout, and nothing
here revises the sealed campaign `801–816` (`ABORT / sealed FAIL`) or the sealed design
`docs/handoff/WAVE7_RQ_EARN_CONFIRM_PREREG_20260926.md`.

---

## 1. The question

> Does delayed adaptation of the antagonist to the host class that was previously common
> produce a measurable rare-class advantage for the host, and under which conditions of
> passage mode, resource regime, population size and contact intensity is that advantage
> stable over time?

The question is asked inside one implemented system, and it is only meaningful there. The
system is a discrete-generation life loop. At each generation boundary the host census is
recorded, each host carries a six-bit recognition window partitioned into three independent
two-bit sub-loci, each antagonist unit carries a window of the same shape, and
host–antagonist contact deals an ATP debit that is a graded function of sub-locus agreement
between the two windows. Antagonist composition is updated at the end of a generation from
the windows that were realised in contact during it, with a keep fraction, a mutation rate
and a passage mode. The word "adaptation" therefore has a concrete, checkable meaning here:
the antagonist pool changes in the direction of the host windows that were common, because
those windows were the ones available to be copied, and the change is carried into the next
generation.

The question is *not* whether antagonism is present, whether a class frequency oscillates,
or whether genetic polymorphism is retained. Polymorphism and cycling are compatible with a
mechanism that contains no adaptation and no frequency-dependent loss at all (Ashby 2020,
DOI `10.1111/jeb.13718`, as used in the design record of this project), so they are treated
below as explanations to be excluded, not as evidence.

### 1.1 Reading the causal claim against the existing score

The current implementation builds one number, `lagged_nfds_score`
(`src/codontrace/genesis/measurements/rq_frequency_clocks.py`, lines 67–133): it pairs the
host class frequency at generation `t` with the antagonist class histogram at generation
`t + τ`, pools every `(generation, class)` pair into a single Pearson correlation, and
reports a preliminary pass when that correlation is at most `-0.3`. `lagged_nfds_score` is
computed in both places from the same kind of object: the host series comes from
`joint_freq`, the "pressure" series comes from `parasite_class_hist`, and line 430 of
`closed_loop_hp_arm01_rq_earn_confirm.py` routes the second directly into the first. The
two series are therefore two class-frequency histograms, and the score is a correlation
between two compositions.

A correlation between two compositions is not a directional claim. This document does not
re-use that score as the mechanism test. It fixes instead a directional claim, with signs
and lags, and a measurement that can carry it; the measurement itself is specified in
`MEASUREMENT_VALIDATION.md` in this directory. The consequence for the existing gate is
stated once and plainly: under the delayed-adaptation hypothesis the sign of the
lagged association between *past host frequency* and *later realised attack strength on
that same class* is expected to be **positive**, so a gate that accepts only
`corr <= -0.3` on a frequency-versus-frequency correlation is not testing this hypothesis.
If a negative threshold is retained, it must be attached to a different quantity with its
own derivation, and it must be fixed before the confirmatory runs. It is never changed
after seeing a result, and a sign change after the fact does not convert the sealed WAVE7
outcome into a pass.

---

## 2. Three competing explanations

Each explanation is a generative account of the same observable pattern: class shares that
move, a lagged association between host composition and antagonist composition, and
sometimes a growth advantage for the class that was rare. They differ in what carries the
association and in what a matched intervention does to it.

### 2.1 E1 — True frequency-dependent adaptation (the hypothesis)

The antagonist pool is replenished from the windows that were realised in contact, and the
antagonist thereby becomes, with a delay of about one generation, better matched to the
host class that was common. Attack strength is affinity-driven and therefore class-specific.
A host class that has recently been rare is attacked more weakly than it was when common, so
its per-capita growth exceeds that of the recently common class. The mechanism is
frequency-dependent and self-limiting: the advantage of rarity decays as the rare class
becomes common and the antagonist catches up.

Distinctive consequences: the cross-covariance of host frequency and realised pressure on
the same class peaks at a **positive** lag of about one to four generations; the advantage
survives when the antagonism is present and coevolving and disappears when passage is
frozen or the antagonist is absent, with matched demography and matched resource forcing;
the advantage is present in both the constant and the periodic resource regime, at the
appropriate population sizes.

### 2.2 E2 — Neutral oscillation and drift

Contact is realised through a rotation and equal-exposure policy that makes the number of
contact opportunities per class proportional to that class's share of hosts. The antagonist
update is unbiased in composition: it copies windows from the realised contact set plus
mutation, in proportion to their frequency in that set. Under this reading the antagonist
composition performs a bounded random walk on the simplex, and the host composition
drifts and oscillates through finite-population sampling. A lagged correlation then appears
for three reasons that have nothing to do with selection: both series are autocorrelated,
both are constrained to sum to one, and the pooled Pearson correlation mixes the
within-generation constraint with the between-generation movement.

Distinctive consequences: the frequency swap intervention of section 5 has no effect on
later attack strength beyond sampling noise; a frozen-passage arm reproduces the coevolving
arm's association; the block-rotation null and the label permutation null are not rejected.

### 2.3 E3 — Environmental forcing and demography

The resource bolus and the census cycle drive both host composition and the contact
opportunity available to the antagonist, so a lagged association appears without any
adaptation: the antagonist composition tracks the host composition only in the sense that
contact is the copying channel, and the contact set is itself forced by the resource clock.
The rare-class advantage, where it appears, is produced by the abiotic cycle and by
density-dependent survival rather than by class-specific attack.

Distinctive consequences: the effect concentrates in the periodic-forcing cells; a matched
forcing arm with a frozen antagonist reproduces most or all of the effect; the effect scales
with census amplitude rather than with attack asymmetry.

### 2.4 Discriminating predictions

| Prediction | E1 adaptation | E2 neutral oscillation / drift | E3 forcing / demography |
|---|---|---|---|
| Sign of cross-covariance between host frequency and later pressure on the same class | positive, peaking at lag 1–4 | near zero at every lag; apparent structure only under the frequency-versus-frequency score | positive but phase-locked to the resource clock; peak lag tracks the forcing period |
| Frequency-swap intervention (section 5) | large, signed, and itself sign-reversing | indistinguishable from zero | present, but no larger than in the frozen arm |
| Frozen-passage arm | no rare-class advantage | same association as the coevolving arm | same as the coevolving arm under matched forcing |
| Antagonist-absent arm | no attack, no advantage, no association | no association (no antagonist series) | host cycle persists, advantage absent |
| Resource regime | advantage in both regimes, largest where the class composition is unconstrained | no dependence on regime | advantage concentrated in the periodic regime |
| Population size | advantage largest where drift is weak | fastest loss of any pattern where drift is strong | amplitude-driven, not size-driven |

The design is chosen so that these three sets of predictions cannot all hold at once. A
result that matches E1 on the intervention and the frozen contrast but matches E3 on the
resource regime is reported as a boundary between mechanisms, not as E1.

---

## 3. The causal graph: sign and lag of every link

Notation. `g` indexes generation boundaries. `h_i(g)` is the frequency of host class `i`
among the host census at boundary `g`; `Σ_i h_i(g) = 1`. `a_j(g)` is the frequency of
antagonist class `j` in the antagonist pool between boundary `g` and boundary `g+1`;
`Σ_j a_j(g) = 1`. `π_i(g)` is the realised conditional pressure on host class `i` during
generation `g`, in ATP debited per host of class `i` per contact opportunity
(units and construction in `MEASUREMENT_VALIDATION.md`). `R` is the environmental regime
(bolus schedule), `N_e` the realised effective census, `v` the virulence multiplier,
`θ` the antagonist update parameters (keep fraction, mutation rate, passage mode), and
`U` the random draws.

The graph is stated in a table because the links are more useful with their reasons than
as a picture. Every link carries a sign and a lag in generations.

| # | Cause → effect | Sign | Lag (generations) | Reason for the sign and the lag |
|---|---|---|---|---|
| L1 | `h_i(g)` → `π_i(g)` via contact realisation | + | 0 | Contact opportunities are allocated by the equal-exposure policy, so the expected number of opportunities for class `i` is proportional to `h_i(g)`; the contact itself, the affinity evaluation and the debit all occur inside generation `g` |
| L2 | `a_j(g)` → `π_i(g)` | + | 0 | The debit magnitude for a pair is `virulence × steal_fraction × graded_affinity(host, parasite)`, and `a_j` is the probability that a given contact opportunity is served by class `j`. More antagonist units of the class that matches host class `i` means more debit on `i`. Strictly, the effect is on `Σ_j a_j · affinity(i,j)`, so this link is the composition-weighted average affinity |
| L3 | `π_i(g)` → realised debit paid on `i` | + | 0 | Where a host cannot pay, the debit is truncated at the ATP that is available, so the paid debit is a non-decreasing, concave function of the intended debit; the sign is preserved but the magnitude can be lost |
| L4 | realised debit → host survival and per-capita growth of `i` | − | 0 to 1 | ATP is drawn on for the birth process; debit reduces what remains, so growth falls and mortality rises within the same generation, with the demographic consequence visible at boundary `g+1` |
| L5 | `h_i(g)` → `a_i'(g+1)` (transmission of the common class into the antagonist pool) | + | 1 | The update copies windows from the realised contact set, which is dominated by hosts that were common in generation `g` (L1). This is the adaptation channel. The lag is one generation because the update happens at the generation boundary and is driven by that generation's contacts |
| L6 | `a_i'(g+1)` → `π_i(g+1)` | + | 1 (relative to `h_i(g)`) | Composition of the antagonist pool at `g+1` feeds the contacts of generation `g+1`; this is L2 delayed by L5 |
| L7 | `π_i(g+1)` → net selection on `i` | + strength / − growth | 1–2 | A class under stronger pressure grows more slowly and loses share over the following generations; this link is what converts attack asymmetry into a frequency change, and it carries the sign inversion that produces the rare-class advantage |
| L8 | `h_i(g)` → rare-class advantage of `i` over the next window | + | 1 to ≈`1/|selection|` | The rarely common class is attacked more weakly (L5–L6–L7), so its per-capita growth exceeds that of the recently common class for as long as the antagonist has not caught up. The lag is short; the duration is set by how fast the frequencies move |
| L9 | drift and finite census (through `N_e`) → any frequency trajectory | ± | cumulative | Sampling noise moves both compositions. Its magnitude falls as the effective census rises; it contributes no signed class-specific bias |
| L10 | `R` (forcing) → `h_i(g)`, `a_j(g)` | ± | 0 to one forcing period | The bolus schedule sets the census and thereby the exposure. It is exogenous and is applied identically to matched arms, so it cannot by itself create a signed class-specific attack asymmetry |
| L11 | `h_i(g)`, `a_j(g)` → registered histograms | +, definitional | 0 | `joint_freq` and `parasite_class_hist` are both normalised compositions. This link is the measurement channel and carries no causal content; treating it as a causal link is precisely the error of reading `lagged_nfds_score` as a mechanism test |
| L12 | shared autocorrelation of the two compositions → pooled correlation of any two shares | + artifact | 0 | Two autocorrelated bounded series correlate. The artefact is not attributable to class identity, frequency dependence or adaptation |

### 3.1 The signed commitments this campaign makes

Three of these links are the commitments that must be right or the campaign is void:

1. **L5 is positive with lag 1.** If the antagonist pool is replenished from realised
   contact, then a class that was common at `g` is over-represented in the update that
   becomes the pool at `g+1` relative to a class that was rare.
2. **L2 and L6 together make realised pressure positively associated with the host class'
   own past frequency at lag 1–4**, and the currently implemented score therefore has the
   wrong sign for this hypothesis: the association it should show is positive, while it
   accepts only `corr <= -0.3`. A negative correlation between the two compositions would
   mean the antagonist is preferentially ranged against the classes that were recently rare,
   which no line of the update rule produces. The mechanism chain predicts the opposite
   sign from the gate. This is a sign commitment, not a claim about any observed result.
3. **L9 and L10 must be excluded before L5–L8 may be credited.** Drift has no sign; forcing
   has a sign but no class specificity. Both are neutralised by the factorial and by the
   matched-forcing arm, not by inferring their absence from a correlation.

### 3.2 What the graph does and does not claim

The substrate is a program, and the graph is a description of that program's generative
structure. It is not an identification claim about a natural population, and no
confounding-adjustment language is used. "Confounding is absent by construction" applies
only in this narrow sense: within one seed, arms differ only in the variables that the
design declares. Two traps follow, and both are guarded explicitly. First, the histogram
pair (L11) is definitional; a regression of one composition on the other estimates the
constraint on a simplex, not a mechanism. Second, the pair `(h_i(t), π_i(t+τ))` is
autocorrelated within a run (L6, L9, L12), so no nominal interval computed from the count
of pooled pairs is admissible. Both traps are handled in the measurement and uncertainty
specifications, not here.

---

## 4. Target estimand

All quantities are defined per run (one seed in one factorial cell), never per class and
never per generation.

**Primary estimand (rare-class advantage contrast).**
For a run `r`, let `A` be the designated *common* class and `B` the designated *rare* class,
both fixed by the pre-registered founder assignment and applied identically to every arm of the
design before the run, rather than chosen after observing the trajectory (see `PREREG_V2.md`,
section 3.3, for the assignment rule and the reason a trajectory-based rule cannot be used with
a symmetric founder slate). Define the run-level rare-class advantage

```
RA(r) = mean_{g in W} [ λ_B(g) - λ_A(g) ]
```

where `λ_c(g) = log( n_c(g+1) / n_c(g) )` is the realised per-capita growth rate of class
`c` over the generation starting at boundary `g`, in units of log count per generation, and
`W` is the pre-registered measurement window after the burn-in. The primary contrast is the
paired difference at the cell level,

```
Δ(passage, forcing, Ne, contact) = mean_r [ RA(r, passage=coevolve) ]
                                 - mean_r [ RA(r, passage=frozen) ]
```

with runs paired on seed so that the demographic and resource draws are held common.

*Interpretation.* `Δ` is the causal effect of a coevolving antagonist, relative to an
antagonist whose composition is held fixed by the same passage policy as the frozen arm, on the
growth advantage of the class that was rare. Units: log count per generation.

**Secondary estimand (mechanism, the intervention quantity, denoted `S`).**
Between the pre-registered swap snapshot and the matched baseline snapshot, with census,
resource state, host genotype multiset, contact count and random draws held fixed,

```
S(r) = [ π_A^(swap)(r) - π_A^(baseline)(r) ]
```

in ATP per host of class `A` per contact opportunity. Under `E1`, `S(r) < 0`: when the
class that was common at baseline is made rare, the antagonist's realised attack on it
falls. Under `E2`, `S(r) = 0`. Under `E3`, `|S|` in the frozen arm is comparable to the
coevolving arm.

**Tertiary estimand (association, with the sign fixed in advance).**
For each run and each class, the within-run cross-covariance of `h_i(g)` with
`π_i(g + τ)` for `τ ∈ {0, 1, 2, 4, 8}`, computed on the run's own series, with uncertainty
taken across runs. The pre-registered prediction under `E1` is that the cross-covariance is
**positive** and peaks at a positive `τ` in the range 1–4 generations. The prediction under
`E2` is no positive peak. This is the only estimand in the campaign that has anything
measurable in common with the existing `lagged_nfds_score`, and it is deliberately not
reduced to a single pooled correlation.

**Not estimands.** The count of pooled class-generation pairs; the number of retained
classes; the proportion of generations in which the dominant class alternates; the
magnitude of a Pearson correlation between two compositions. These are descriptive
summaries, they are reported under names that say so, and they carry no claim.

---

## 5. Unit of replication

**The independent unit is the run: one fresh seed in one factorial cell.** A run is one
independent realisation of the whole history from the fixed founder slate to the horizon.

Binding consequences:

* `N` in this campaign is the number of runs. It is never the number of classes, never the
  number of generations, and never the number of pooled class-generation pairs.
* The class shares within one generation are dependent by construction, because they sum to
  one. Two classes in the same generation carry one degree of freedom between them, not two
  independent observations.
* Successive generations of the same run are autocorrelated. The autocorrelation is a
  property of the system, and it does not vanish as the horizon grows.
* Seeds are the only axis of independent randomisation, so the paired contrasts are paired
  on seed and the factorial is complete on seeds. Every fresh seed is assigned to every cell
  of the design, so that each seed contributes one observation to each cell.
* The seed ranges are fresh and disjoint from every previously used block, including the
  sealed campaign `801–816` and the demography block `751–758`; the allocation is fixed in
  `PREREG_V2.md`. Re-using a previously run seed would break the assumption of independence
  and would also confound a new design with an old one.
* The previous practice of counting 20 or more pooled pairs as sufficient evidence is not
  repeated. A run contributes one summary value per estimand; where a within-run time series
  is required, it is used with an explicit dependence structure and the interval is taken
  across runs.

---

## 6. Falsification conditions

The question is falsifiable on paper in the following sense: there exist executable
synthetic systems, built from the same contact and update rules with known latent
structure, on which the pre-registered tests must give a specific answer. The mechanism
test is accepted only if it passes every positive case and rejects every counter-sample.
This section is the acceptance contract for the instrument; `PREREG_V2.md` adds stop rules
that quote it.

### 6.1 The mechanism test

Define the **swap-signal** statistic on a run or a synthetic system as the difference
between the realised pressure on the designated class `A` with the host class frequencies
swapped and with them unswapped, holding the census, the resource state, the host genotype
multiset, the contact count and the random draws identical:

```
S = π_A(swap) − π_A(baseline)
```

with `S` in ATP per host of class `A` per contact opportunity, the swap meaning that the class
designated common at baseline is given the baseline share of the designated rare class. Under
delayed adaptation the antagonist should attack the class that was common, so making that class
rare should reduce the pressure it receives: the pre-registered expected sign is `S < 0`, and
the magnitude must reach the mechanism floor of `PREREG_V2.md` (threshold T9). The swap is
applied in both directions, and the two directions must give the same magnitude with opposite
signs; this rules out an effect of the label rather than of frequency. The contrast is a
pre-declared constant of the design and is not re-drawn or re-selected from any trajectory.

### 6.2 Synthetic cases that must pass

Each synthetic case is a fixed script with a hand-checkable answer. The expected numbers
below are computed by hand in `MEASUREMENT_VALIDATION.md`, section 4, and the script must
reproduce them.

| Case | Construction | Pre-registered required outcome |
|---|---|---|
| **P1 — antagonist with delay adapts to the common host (the directive's positive case)** | Two host classes `A`, `B`; two antagonist classes whose windows match `A` and `B` respectively; the update copies from the realised contact set with a one-generation lag; class `A` starts at share 0.6, `B` at 0.4 | `S < 0` with `|S|` at or above the mechanism floor; the cross-covariance of `h_A` with `π_A` is positive and peaks at a positive lag; the frozen-passage twin of the same seed gives `S = 0` within tolerance |
| **P2 — adaptation with frequency reversal** | P1, then the host shares are reversed at a pre-registered generation by symmetric intervention while census, resources, genotype multiset, contact count and draws are held fixed | `S` reverses sign relative to the pre-reversal window and keeps its magnitude; the rare class' growth advantage appears after the reversal and not before; a label-permuted twin gives zero |
| **P3 — flat-loss control (must not be credited as a mechanism)** | Every host class receives the identical affinity-weighted debit, so the loss is class-blind; class shares still cycle | `S = 0` within tolerance, and the rare-class advantage is not distinguishable from zero |

### 6.3 Counter-samples that must be rejected

| Case | Construction | Pre-registered required outcome |
|---|---|---|
| **N1 — anti-phase oscillation with no adaptation and no frequency-dependent loss** | Host and antagonist proportions move in anti-phase by construction; the affinity matrix is flat, so every class pays the same debit per contact and there is no frequency-dependent loss anywhere in the system | `S = 0` within tolerance; the rare-class advantage is not distinguishable from zero; the primary test must **fail to reject**. A statistic that reports a mechanism here is measuring oscillation and the campaign does not run |
| **N2 — constant-loss control** | A fixed debit of the same average magnitude is applied to every host class, independent of class and of contact | `S = 0`; no rare-class advantage; the effect must not be attributable to the added mortality |
| **N3 — frozen antagonist, matched forcing** | The identical resource schedule, census trajectory and contact count, with the antagonist pool held frozen at the ancestral multiset | `S = 0`; any rare-class advantage present in the coevolving arm must be absent, reduced, or explicitly reported as unexplained variance rather than as adaptation |
| **N4 — antagonist absent** | No antagonist, everything else matched | `S` undefined (no antagonist series); no attack; the host cycle may persist; no rare-class advantage attributable to attack |

### 6.4 Joint falsification

The hypothesis `E1` is **refuted** if any of the following holds:

1. A synthetic case in section 6.2 fails, or a counter-sample in section 6.3 is accepted.
   This is an instrument failure and blocks the confirmatory campaign; it is not a result
   about hosts and antagonists.
2. The swap-signal is not negative, or its magnitude is below the mechanism floor, in the
   coevolving cells, or it does not reverse sign under frequency reversal.
3. The cross-covariance of past host frequency with later pressure on the same class is not
   positive at any lag in 1–4 generations in the coevolving cells.
4. The rare-class advantage is absent, or present at a magnitude below the pre-registered
   absolute target `δ_min` of `PREREG_V2.md` (threshold T15), or indistinguishable from its
   frozen and matched-forcing controls.
5. The rare-class advantage in the frozen, forced or absent arms is as large as in the
   coevolving arm with matched demography and resources.

The hypothesis is **not** refuted, and is reported as a bounded positive, if the advantage
exists but decays at a horizon that can be located, or if it exists only inside a stated
region of the factorial. A cycle that disappears at long horizons is a valid finding about
the stability boundary, not a partial success that can be reported as a full mechanism.

The existing sealed outcome is unaffected by all of the above. The campaign `801–816`
remains `ABORT / sealed FAIL`, and a pass under this instrument is not a confirmation of the
WAVE7 design.

---

## 7. Relation to prior work, and the novelty boundary

This question is not new in general. Experimental tests of antagonist adaptation to common
versus rare host genotypes, of rare advantage, and of the effect of coevolution on mating
system are published, and the directive supplying this campaign lists them: Morran et al.
(2011), *Science*, DOI `10.1126/science.1206360`; Gibson et al. (2020), *Biology Letters*,
DOI `10.1098/rsbl.2020.0210`; Ashby (2020), *Journal of Evolutionary Biology*, DOI
`10.1111/jeb.13718`; Schenk, Schulenburg and Traulsen (2020), *BMC Evolutionary Biology*,
DOI `10.1186/s12862-019-1562-5`; Ramirez and Gibson (2026), *Ecology and Evolution*, DOI
`10.1002/ece3.73965`. The defensible contribution here is a boundary and a mechanism inside
one specified model, with drift, demography, environmental forcing and the contact rule all
controlled, and it is framed as such. A pass under this design is not "Red Queen proved",
the flags stay false, and the phrase does not appear in any result statement from this
campaign.

Two limits are recorded now, before the runs. First, a positive result here is a property of
this affinity rule, this contact policy and this update rule; whether the direction of the
effect survives under a matching, gene-for-gene or alternative affinity rule is a separate
question in the same submodule and is not answered by this design. Second, an asexual clone
estimand is not an estimand about sex. No claim about the maintenance of sex, about
recombination, or about a two-fold cost is made from this campaign.
