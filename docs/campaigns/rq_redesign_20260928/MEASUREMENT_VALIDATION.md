# Measurement validation: antagonist class frequency and realised conditional pressure

**Date:** 2026-09-28
**Base commit:** `7cfba3fc59b4d6dcd80895ea283eb5a69fdf7c72` (`7cfba3f`), `main`
**Campaign:** `rq_redesign_20260928`
**Status:** measurement specification, written before any confirmatory run
**Related:** `SCIENTIFIC_QUESTION_AND_DAG.md` and `PREREG_V2.md` in this directory;
`STATS_AND_NULL_DESIGN.md` in this directory for the interval method and the null models.

---

## 1. Why two quantities

The current implementation builds the lagged score from one kind of object. In
`closed_loop_hp_arm01_rq_earn_confirm.py` (lines 418–431) the host series is taken from each
snapshot's `joint_freq` and the "parasite pressure" series from `parasite_class_hist`; the
same extraction is repeated in `closed_loop_hp_arm01_rq_earn.py` (lines 140–155). The second
object is produced in `closed_loop_hp_arm01_structural_rq.py` (lines 705–711) by counting the
antagonist windows by match class and normalising, and it is then passed to
`lagged_nfds_score` in `measurements/rq_frequency_clocks.py`, whose docstring calls it
"parasite pressure on class c". It is not pressure. It is the composition of the antagonist
pool, and it carries no host information at all.

The contact rule of the same model is explicit about what pressure is. In
`_apply_hp_env_contact` (lines 551–623) each host is paired with one antagonist window,
`graded_affinity(host_window, parasite_window)` is evaluated as the mean of three
bit-disjoint two-bit agreement scores, and the debit is
`virulence × steal_fraction × affinity`, truncated at the host's available ATP. Damage on a
host class is therefore the product of how many contacts that class received, which
antagonist classes served them, how well those classes matched, and how much ATP the host
could actually pay. None of those four factors is read off `parasite_class_hist` alone.

The two quantities are separated below, given separate names, separate units and separate
storage, and are never substituted for one another. Section 4 gives two hand-computed
scenarios that fail if they are conflated: one in which the antagonist histogram is
constant while realised pressure differs between host classes, and one in which the reverse
holds.

---

## 2. Quantity one: antagonist class frequency

**Definition.** At generation boundary `g`, partition the antagonist pool into match classes
by `joint_match_class`, the class of a unit being its three two-bit sub-locus strings joined
by `|`. Then

```
F_j(g) = n_j(g) / N_p(g)          units: dimensionless share
Σ_j F_j(g) = 1
```

where `n_j(g)` is the number of antagonist units in class `j` and `N_p(g)` is the number of
antagonist units. `F_j(g)` is a share, on `[0, 1]`, and it is undefined when `N_p(g) = 0`.

**What it is for.** `F` is the transmission-side composition of the antagonist pool. It is
the right thing to record when the question is what the antagonist population looks like,
when the question is whether the update moves the pool, or as a covariate. It is the exact
object that the present score consumes.

**What it is not.** `F_j(g)` is not the probability that a host is attacked, it is not the
loss suffered by any host class, and it is not a measure of adaptation. A change in `F` says
that the pool changed composition; it does not say that any host class fared differently.

**Constraint to report.** `F` is a composition. Between classes within a generation there is
one degree of freedom, not `J`. Any statistic computed across pooled `(generation, class)`
pairs inherits this constraint, and the number of pooled pairs must never be reported as a
sample size.

---

## 3. Quantity two: realised conditional pressure on a host class

**Definition.** During generation `g`, for host class `i` and one host `k` of that class, let
`d_k(g)` be the ATP actually debited from `k` by contact in that generation, and let
`o_k(g)` be the number of contact opportunities assigned to `k` in that generation. Define

```
π_i(g) = Σ_{k in class i} d_k(g) / Σ_{k in class i} o_k(g)
```

Units: **ATP per host per contact opportunity**, division by zero excluded, and

```
c_i(g) = Σ_{k in class i} o_k(g) / n_i(g)        units: contacts per host per generation
```

so that `π_i(g) · c_i(g)` is the mean ATP debited per host of class `i` per generation. The
pair `(π, c)` is stored for every class, every generation, in the dense history, alongside
`F`, never merged with it.

**Two variants, stored separately because they can diverge.**

* `π_realised` is the definition above. It uses the debit actually paid, after the ATP
  truncation, and is the quantity that feeds survival and growth. This is the primary
  pressure measurement.
* `π_intended` is the same average taken over the intended debit
  `virulence × steal_fraction × affinity` before truncation, and it is undefined where the
  contact opportunity count is zero. The difference `π_intended − π_realised` is the
  saturation load, and it is recorded as its own series because it is the mechanism by which
  a class can be equally attacked in terms of affinity and unequally damaged in terms of
  realised loss.

**Fitness-relevant layer.** Pressure maps to selection through host growth. For each class,
the run records the mean per-capita growth rate

```
λ_i(g) = log( n_i(g+1) / n_i(g) )        units: log count per generation
```

The causal expectation fixed in `SCIENTIFIC_QUESTION_AND_DAG.md` is that `π_realised` on a
class is negatively associated with that class' `λ` in the following generation, and that
the association of `π_realised` at `g+1` with `h_i` at `g` is positive. Neither of those
relations is inferred from a correlation of compositions.

**Time indexing.** `h_i(g)` and `F_j(g)` are boundary objects at generation `g`. `π_i(g)`,
`c_i(g)` and the debits are within-generation quantities for the generation that runs from
boundary `g` to boundary `g+1`. The lag is therefore counted in generation boundaries, and a
lag of 1 means: the composition at boundary `g` versus the contacts of the following
generation. All series cover every generation at unit stride; a subsampled series is never
used for the lag clock, because at stride 25 no `(g, g+τ)` pair exists for small `τ`.

### 3.1 Equal exposure

Class differences in `π` are only interpretable if every class had the same chance to be
attacked. Equal exposure is enforced and then verified, in this order.

**Enforced by the design.** Each run uses the equal-exposure contact policy: for the classes
declared in the design, the contact opportunities assigned per generation are the design
targets, so the intended opportunity count for class `i` is proportional to `h_i(g)` and the
intended pairing among antagonist classes is a fixed proportional mixture rather than a
fixed index alignment. Contact policy is a design variable and is held identical across all
arms compared in one contrast.

**Verified in the record.** Each generation stores `o_k(g)` per host and hence the per-class
opportunity counts `O_i(g) = Σ_{k∈i} o_k(g)`. The exposure audit compares `O_i(g)` against
its design target and reports, per run and per window:

* `exposure_ratio(i) = O_i / O_i^target`, the realised-to-target ratio of opportunities;
* `exposure_tolerance` = 0.05, a pre-registered relative tolerance on `exposure_ratio`;
* `contacts_per_host` = `c_i(g)`, with a pre-registered floor of 1.0 contact per host per
  generation averaged over the window — the value the contact policy provides when every seat
  is realised — so that a class is not declared unpressured because it was never contacted,
  and a shortfall is reported as a policy failure rather than absorbed;
* `paired_fraction` = the realised share of each designed host-class × antagonist-class
  pairing, against its design value.

**Gate.** A run whose `exposure_ratio` exceeds the tolerance, or whose `contacts_per_host` is
below the floor, is flagged `exposure_invalid` and contributes no contrast value to the
primary analysis; it is retained in the attrition table with the reason. An arm cannot lose
runs to this flag silently, because the flag depends only on the design and the recorded
counts.

**Why the histogram is not an exposure measure.** Because `O_i` is proportional to `h_i` by
design, two classes with relative frequencies 0.5 and 0.5 receive equal opportunity *by
construction*, and a change in `F` alone does not move `O_i` at all. The differences that
matter for damage are in the pairing and in the affinity between the paired windows, and
those are invisible to `F`.

---

## 4. Worked examples

All numbers below use the constants of the existing structural design and the documented
affinity rule: `virulence v = 8.0`, `steal_fraction s = 0.15`, so
`debit per contact = v · s · affinity = 8.0 × 0.15 × affinity = 1.2 × affinity`, in ATP.
Affinity is the mean of three two-bit sub-locus agreement scores and therefore takes values
in multiples of `1/6`.

### 4.1 Affinity table

The host windows are the design's distinct 6-bit founders; antagonist classes are represented
by their match windows. Affinity values follow from the mean-of-sub-loci rule.
On 2026-09-29 three rows of this table, and the example-1 difference 0.700, did not
match that rule. The contact rule was not changed. The corrected difference is 0.800.
The withdrawn 0.700 is not a threshold and is not a result.

| Pair (host window, antagonist window) | Sub-locus agreements | Affinity | Debit per contact (ATP) |
|---|---|---|---|
| `000000` vs `000000` | 2/2, 2/2, 2/2 | 3/3 = 1.000 | 1.200 |
| `000000` vs `000001` | 2/2, 2/2, 1/2 | 5/6 = 0.833 | 1.000 |
| `000000` vs `000011` | 2/2, 2/2, 0/2 | 4/6 = 0.667 | 0.800 |
| `000000` vs `010101` | 1/2, 1/2, 1/2 | 3/6 = 0.500 | 0.600 |
| `000000` vs `100000` | 1/2, 2/2, 2/2 | 5/6 = 0.833 | 1.000 |
| `000000` vs `111100` | 0/2, 0/2, 2/2 | 2/6 = 0.333 | 0.400 |
| `111100` vs `000001` | 1/2, 0/2, 0/2 | 1/6 = 0.167 | 0.200 |
| `111100` vs `000011` | 0/2, 0/2, 0/2 | 0/6 = 0.000 | 0.000 |
| `111100` vs `111100` | 2/2, 2/2, 2/2 | 3/3 = 1.000 | 1.200 |

### 4.2 Example 1 — the antagonist histogram is constant, the realised pressure is not

One generation. Two host classes, `A` (window `000000`) and `B` (window `111100`), one host
each. Two antagonist classes, `P_a` (window `000001`, well matched to `A`) and `P_b`
(window `000011`, mismatch to `B` but not to `A`). Equal exposure gives each host one
contact from each antagonist class: host `A` receives `o_A = 2` contacts, host `B` receives
`o_B = 2` contacts.

Antagonist histogram, constant by construction: `F_(P_a) = 0.5`, `F_(P_b) = 0.5`.

Realised debit, host `A`:

```
contact 1: affinity(000000, 000001) = 0.833   →  1.2 × 0.833 = 1.000 ATP
contact 2: affinity(000000, 000011) = 0.667   →  1.2 × 0.667 = 0.800 ATP
total d_A = 1.800 ATP over o_A = 2 contacts
π_A = 1.800 / 2 = 0.900 ATP per host per contact opportunity
```

Realised debit, host `B`:

```
contact 1: affinity(111100, 000001) = 1/6 = 0.167   →  1.2 × 0.167 = 0.200 ATP
contact 2: affinity(111100, 000011) = 0/6 = 0.000   →  1.2 × 0.000 = 0.000 ATP
total d_B = 0.200 ATP over o_B = 2 contacts
π_B = 0.200 / 2 = 0.100 ATP per host per contact opportunity
```

```
π_A − π_B = 0.900 − 0.100 = 0.800 ATP per host per contact opportunity
F_(P_a) − F_(P_b) = 0.5 − 0.5 = 0.000
```

Both host classes had the same exposure and the antagonist histogram was exactly balanced,
yet the realised pressure on class `A` is 9 times the realised pressure on class `B`, a
difference of 0.800 ATP per contact opportunity. The histogram cannot represent that
difference at all, because it contains no host information: `P_a` and `P_b` are equally
frequent and the asymmetry lives entirely in the affinity of each pairing.

*Role in the design.* This scenario is the sensitivity core of the adversarial unit test
required by the campaign. A test built on `F` must return "no class difference" here; a test
built on `π` must return the difference above. If the two agree on this scenario, the two
quantities are not separated in code and the campaign is not run.

### 4.3 Example 2 — the realised pressure is equal, the antagonist histogram is not

Same one-generation structure, but the affinity matrix is flat: every host window is equally
matched to every antagonist window, with affinity exactly `0.5` (`= 3/6`), hence
`1.2 × 0.5 = 0.600` ATP per contact for every pair.

Case (a): `n_(P_a) = 2` and `n_(P_b) = 2`, so `F_(P_a) = F_(P_b) = 0.5`. Each host receives
one contact from each class:

```
π_A = (0.600 + 0.600) / 2 = 0.600
π_B = (0.600 + 0.600) / 2 = 0.600
π_A − π_B = 0.000
```

Case (b): the antagonist pool is shifted, `n_(P_a) = 6` and `n_(P_b) = 2`, so
`F_(P_a) = 0.750` and `F_(P_b) = 0.250`. Equal exposure still gives each host one contact
from each class in the designed mixture:

```
π_A = (1.2 × 0.5 + 1.2 × 0.5) / 2 = 0.600
π_B = (1.2 × 0.5 + 1.2 × 0.5) / 2 = 0.600
π_A − π_B = 0.000
```

```
F_(P_a) shift: 0.500 → 0.750      (change of +0.250)
π_A − π_B shift: 0.000 → 0.000    (change of 0.000)
```

A large change in the antagonist class histogram produced no change in realised pressure on
either host class, because the affinity matrix is class-blind. The reverse of Example 1
holds, and it holds for the same reason: `F` and `π` measure different things.

### 4.4 Example 2b — equal exposure, equal affinity, unequal realised pressure

A third contrast isolates the ATP truncation, and it is the reason `π_intended` and
`π_realised` are stored separately. Flat affinity `0.5` as in section 4.3, so the intended
debit is 0.600 ATP on every contact for both classes. Host class `A` holds two hosts with
runtime ATP available of 10.0 each; class `B` holds two hosts with 0.500 each. One contact
each:

```
class A: intended 0.600 per host, available 10.000 → paid 0.600
         π_intended,A = 0.600,  π_realised,A = 0.600
class B: intended 0.600 per host, available 0.500  → paid 0.500 (truncated)
         π_intended,B = 0.600,  π_realised,B = 0.500
π_A − π_B: intended = 0.000,  realised = 0.100
```

Equally attacked, unequally damaged. Only the realised measure reports the class difference,
and only the intended measure reports that the attack was symmetric. Both are needed, which
is why the campaign stores both.

### 4.5 What these examples commit the implementation to

* Two stored quantities with two names and two units: `F` (dimensionless share) and `π`
  (ATP per host per contact opportunity), plus `c` (contacts per host per generation), plus
  `π_intended` and the saturation load.
* An exposure audit with the pre-registered tolerance of 0.05 and the floor of 1.0 contact per
  host per generation.
* A unit test that runs all three of sections 4.2, 4.3 and 4.4 on a scripted generation and
  asserts the hand-computed numbers above to within floating-point tolerance. The numbers are
  the test's expected values; a discrepancy is a defect in the implementation, not a licence
  to change the expectation.
* No scenario in this section may be used to choose a threshold in `PREREG_V2.md`. The
  numbers here are mechanics of the contact rule.

---

## 5. The sign of the lagged score under the mechanism hypothesis

**Convention of the existing score.** `lagged_nfds_score` pairs
`x = host frequency of class c at generation t` with
`y = antagonist histogram weight of class c at generation t + τ`, with `τ = 4` in the
campaign configuration, and requires `corr(x, y) <= -0.3` and at least 20 pooled pairs.

**Expected sign under the mechanism hypothesis.** From the causal graph in
`SCIENTIFIC_QUESTION_AND_DAG.md`, the links L5, L6 and L2 together say: the class that was
common at generation `g` is over-represented in the antagonist pool at `g+1`, and the
antagonist pool at `g+1` supplies the contacts of generation `g+1` with a debit proportional
to affinity. The association between *past host frequency of a class* and *later realised
pressure on that same class* is therefore **positive**, peaking at a lag of 1 to 4
generations. Under the mechanism hypothesis, `lagged_nfds_score` as currently defined should
be **positive**, not negative. A value of `corr <= -0.3` would mean that the classes a host
had recently been rare in are the classes now under the strongest attack; no step of the
contact rule or of the update rule produces that.

### 5.1 Why `corr <= -0.3` is not justified by the mechanism — in plain words

Three separate things are wrong with the threshold, and none of them is a matter of taste.

1. **The two series are both compositions, so the correlation is a geometric artefact as much
   as a measurement.** Each antagonist histogram sums to one and each host frequency vector
   sums to one. Within one generation the class pairs are exact negatives of each other, and
   across generations both vectors wander in a bounded region. The pooled Pearson coefficient
   therefore has a strong contribution from the constraint, a weaker one from shared
   autocorrelation, and only whatever is left from the adaptation the study is about. Under
   the mechanism the residual should be positive, which is the opposite sign from the gate.
2. **`n >= 20` is not 20 independent observations.** A run of any length produces far more
   than 20 pairs, and they are dependent in two ways at once: classes within a generation,
   and generations within a run. Passing or failing the gate is therefore governed by the
   length of the run and the number of retained classes, not by the strength of the
   mechanism. The floor of 20 pairs protects against nothing.
3. **The negative threshold as written would accept the wrong counter-sample.** In the
   nine-generation series of section 6, a system with a deliberately anti-phase antagonist and
   a flat, class-blind affinity matrix gives `corr = −1.00`, which passes `corr <= −0.3`
   comfortably, while the same system with true one-generation adaptation gives
   `corr = +1.00`, which fails. The gate is not merely underpowered; on the canonical pair of
   synthetic cases it is inverted.

A negative sign can be meaningful for a *different* quantity. If the intended construct is
alternation — whether the class that was common at `t` is the class under proportionally
heavy attack at `t + τ` — then the quantity has to be a ratio of realised pressure to
expected attack given the class' own share, `π_i(g+τ) / π̄(g+τ)`, paired against
`h_i(g)`, and its sign, lag and magnitude have to be derived from the mechanism before any run.
An anti-phase reading may also be carried by a different measured quantity entirely, such as
the sign of a lagged selection differential on the host class rather than by pressure. Either
choice is legitimate; neither may be improvised after seeing a result.

### 5.2 The locked statement on the sign

> The sign and the lag are fixed before the run. The expected sign of the association between
> past host class frequency and later realised pressure on that class is positive, with a
> peak lag between 1 and 4 generations. The expectation is not changed after seeing results.
> The existing `corr <= -0.3` gate is not a test of this hypothesis; it is retired from the
> primary pathway of this campaign and retained only as a descriptive comparator, reported
> with its correlation, its pooled pair count, its lag and the note that it is a
> composition-versus-composition statistic. If a signed threshold on a new quantity is
> adopted, its value is justified from the mechanism and from the pilot's between-run
> variance, fixed in `PREREG_V2.md` before the confirmatory runs, and reported as a new
> quantity with its own definition. A post-hoc sign change does not convert the sealed WAVE7
> outcome into a pass, and no result of this campaign is described as a confirmation of the
> WAVE7 design.

---

## 6. Aliasing, stride and autocorrelation sensitivity

The mechanism clock and the sampling clock must not alias. Three checks are required, and
each has a pre-registered expectation.

### 6.1 Stride

The lag clock uses every generation at stride 1. A series subsampled at
stride 25 contains no `(g, g+4)` pair at all, so the score computed on it is empty rather
than weak; `τ = 4` and `stride = 25` are mutually exclusive samplings, and any result built on
a sparse series is reported as unmeasured. The check asserts that the dense history length
equals the horizon and that the number of usable pairs equals the horizon minus the lag, once,
before scoring.

### 6.2 Aliasing of a periodic forcing with the window length

A fixed-period resource pulse
can resonate with the measurement window and manufacture an apparent cycle at the window
frequency. The periodic forcing arm therefore uses an aperiodic pulse with a pre-registered
mean interval of 25 generations and a recorded schedule digest, and the analysis is repeated
at window lengths that are not multiples of that mean interval. A periodic effect that
changes sign or magnitude when the window length changes is reported as aliasing.

### 6.3 Autocorrelation

The effective sample size of a run's series is far below its length.
The moving-block length is set from the pilot as the first lag at which the run-level
autocorrelation of the primary statistic falls below `1/e`, and the interval is computed as
specified in `STATS_AND_NULL_DESIGN.md`, section 2. The block-rotation null is the
discriminating check that any apparent lag structure is not simply "two autocorrelated
series correlate".

### 6.4 Discriminating pair for the sign

The following two series were constructed by hand so that both have identical marginal
distributions and identical autocorrelation structure, and differ only in the order of the
antagonist series. Nine generations; host class `A` share `h`, antagonism-appropriate
pressure `p_corr` (antagonist lags the host by one generation), anti-phase pressure `p_anti`
(antagonist leads by eight generations).

| `t` | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|
| `h` | 0.2 | 0.8 | 0.2 | 0.8 | 0.2 | 0.8 | 0.2 | 0.8 | 0.2 |
| `p_corr` | 0.8 | 0.2 | 0.8 | 0.2 | 0.8 | 0.2 | 0.8 | 0.2 | 0.8 |
| `p_anti` | 0.2 | 0.8 | 0.2 | 0.8 | 0.2 | 0.8 | 0.2 | 0.8 | 0.2 |

Means: `mean(h) = (4 × 0.8 + 5 × 0.2)/9 = 4.2/9 = 0.4667`; `mean(p_corr) = 0.4667`;
`mean(p_anti) = 0.4667`. Centred values: `h` deviates are four `+0.3333` and five `−0.2667`;
`p_corr` deviates are four `+0.3333` at `t ∈ {1,3,5,7}` and five `−0.2667` at
`t ∈ {2,4,6,8,9}`; `p_anti` is the reverse. Products:

```
Σ (h − h̄)(p_corr − p̄) = 4 × (0.3333 × 0.3333) + 5 × (−0.2667 × −0.2667)
                      = 4 × 0.1111 + 5 × 0.0711 = 0.4444 + 0.3556 = +0.8000
Σ (h − h̄)(p_anti − p̄) = 5 × (0.3333 × −0.2667) + 4 × (−0.2667 × 0.3333)
                      = −2 × (4 × 0.0889) = −0.7112 → exactly −0.8000
Σ (h − h̄)² = 4 × 0.1111 + 5 × 0.0711 = +0.8000
ρ_corr = +0.8000 / 0.8000 = +1.00        (delayed adaptation)
ρ_anti = −0.8000 / 0.8000 = −1.00        (anti-phase, no adaptation, no frequency-dependent loss)
```

The magnitude is exactly 1 in both cases, so magnitude cannot discriminate; the sign does all
the work, and it does it backwards relative to the gate. Two further remarks make the sharpness
of that point concrete rather than rhetorical. First, because the two classes are exact
negations of one another within each generation, a two-class system gives the same numbers per
class and the pooled correlation also equals ±1.00, so the pair above is not a contrived
two-point series. Second, the magnitude is uninformative in a wider sense: scaling the host
series towards its mean leaves a correlation at ±1 while removing the regulatory action that
NFDS denotes. A statistic that a change of scale holds fixed, while its sign is set by an offset
that no part of the mechanism produces, is not measuring frequency-dependent selection.

The anti-phase series is the counter-sample the design must reject
(`SCIENTIFIC_QUESTION_AND_DAG.md`, section 6.3, case N1), and the delayed-adaptation series is
the positive case it must accept (case P1). Under `corr <= -0.3`, the gate accepts the first and
rejects the second.

**Required behaviour of the corrected instrument.** Both series must be classified by the
swap-signal of `SCIENTIFIC_QUESTION_AND_DAG.md`, section 6.1, not by a pooled correlation:
`P1` must register a negative swap-signal at or above the mechanism floor, and `N1` must
register zero within tolerance and must not reject. Any instrument that separates these two
cases only by their correlation magnitude is rejected at the instrument gate.

---

## 7. Storage and naming contract

The two quantities are separated in the recorded history and in every report. This is a
naming contract, not a convention that can be relaxed in prose.

| Recorded field | Meaning | Unit | Never called |
|---|---|---|---|
| `antagonist_class_freq` | `F_j(g)`, composition of the antagonist pool | share | pressure |
| `host_class_freq` | `h_i(g)`, composition of the host census | share | exposure |
| `pressure_realised[i]` | `π_i(g)`, ATP actually debited per host per contact opportunity | ATP per host per opportunity | frequency |
| `pressure_intended[i]` | intended debit per host per contact opportunity, before truncation | ATP per host per opportunity | frequency |
| `saturation_load[i]` | `pressure_intended − pressure_realised` | ATP per host per opportunity | pressure |
| `contact_rate[i]` | `c_i(g)`, contacts per host per generation | contacts per host per generation | frequency |
| `exposure_ratio[i]` | realised-to-design opportunity ratio for the class | dimensionless | pressure |
| `host_growth[i]` | `λ_i(g) = log(n_i(g+1)/n_i(g))` | log count per generation | fitness |
| `lagged_nfds_composition` | the retired composition-versus-composition Pearson statistic | dimensionless | mechanism test |

Any existing artefact or document that labels `antagonist_class_freq` (or its ancestor
`parasite_class_hist`) as pressure is superseded for this campaign by the table above. The
sealed artefacts are not edited; the corrected naming applies to the new campaign's outputs and
is recorded in them.
