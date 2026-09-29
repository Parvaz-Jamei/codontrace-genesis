# ROUND-2 RED TEAM — verdict: REJECT AS PREREGISTERED

Three probes were run against the real code (all in `causal-tape-experiment/`): `rt2_aj_check.py` (env 20260927, G40, 300 seeds, natural + 8–16 suppressed tapes per eps), `rt2_boot_coverage.py` (Monte Carlo coverage, calibrated to heavy1's three observed slopes), `rt2_agent_resolution.py` (agent outcome resolution and per-step cost). Numbers below are measured, not asserted.

## 1. A_j(eps): not circular — self-refuting

External to the ensemble: only `J` (J_ij ∈ ±1 from `env_seed`) and the assertion that bias is linear in eps. `E[|c_j(x)|]`, the OLS beta, and ATT all come from one ensemble, so this is not a prediction but a re-description of two summaries of one dataset. It is **not** trivially satisfiable; it is trivially refuted, on three independent grounds.

* **Factor 2 arithmetic error.** ATT_j − w_j = eps·Σ_{k≠j} J_jk x_k = **2**·eps·c_j(x) with the design's own c_j = 0.5·ΣJx. If the relation were exact, the design's algebra gives slope ≈ 2, not 1.
* **Wrong functional.** `E|·|` is a dispersion functional; the estimand's eps-term is a mean functional, conditional on exposure (x_j=1), not unconditional.
* **Wrong estimand.** Suppression re-routes the downstream acceptance path, so the measured bias uses a whole-tape ATT while A_j describes a one-bit contrast on the natural background. At eps=0.8, locus 11:0>1: one-bit bias −1.078 vs tape bias −0.253.

Measured regression of |tape bias| on A_j (n=8 mutations, 300 seeds, env 20260927): **slope = 0.004, 0.121, 0.415, 0.112; intercept = +0.011, +0.031, +0.102, +0.698; r = 0.03, 0.61, 0.63, 0.13** at eps = 0.05, 0.2, 0.4, 0.8. Required 1 and 0. The design's own control sinks it.

Required null: (a) exact 18! permutation of the A_j→bias_j pairing; (b) coupling sign-flip J → SJS, S=diag(±1), **with re-simulation** (the ensemble is J-dependent, so permuting stored rows is not a null). The prediction must beat the 97.5th percentile of both, and must also hold with the background frozen at the J-free eps=0 natural arm. That held-out-background version is the only non-circular predictor.

Also: the "median lands on a 0.5 mass point" diagnosis is factually wrong. At eps=0.3 the sorted |bias| values are 0.034, 0.109, 0.185, 0.190, 0.263, 0.268, 0.287, 0.368 — continuous, no lattice. The dip is an order-statistic crossover on a heavy right tail. The n(M) ≥ 24 prescription rests on a false mechanism.

## 2. "Variation across coupling draws" is a restatement

J is 153 i.i.d. ±1 coins; the ensemble and hence S(eps) are a deterministic function of them, so P(zero between-draw variance) ≈ 0. It is already true in the existing data: per-draw slopes **1.316 / 0.814 / 0.626** (median) and **1.333 / 0.868 / 0.890** (mean). Falsifier must be explicit: CI of the between-draw variance component excludes 0 AND all E per-draw slopes > 0. E ≥ 20 (relative SE of a variance component = sqrt(2/(E−1)): 47% at E=10, 32% at 20, 22% at 41). To be about evolution and not about coin flips, the generator **class** must vary (i.i.d. ±1 vs sparse vs block-correlated J) and class differences must be tested. Unit of inference = the coupling draw. Tape seeds must stay paired across draws (heavy1 already uses 1000..1499 for every config — do not change it). M must be one fixed global set, crossed with draws; if M is re-picked per environment, mutations are nested and the two-level bootstrap is invalid.

## 3. E=10 two-level bootstrap

Simulated at the observed calibration (between-draw slope spread 0.385, ~4× mutation spread, heavy1's 9-eps trend): at E=10 the percentile two-level CI covers 0.93 (M=8) / 0.94 (M=24) for a true slope 1.32, but the **median CI width is 1.56 / 0.96** — it spans 0 and 2·slope. B=10,000 is theatre at E=10 (the env-level resample has 92,378 distinct compositions; the 2.5th percentile is a tail order statistic of 10 points). Worse, §1's "one-sample across those slopes" and the bootstrap's slope-of-mean-S are **different estimands** (Jensen): t-intervals on mean-of-per-env-slopes covered 0.63 (E=10), 0.49 (E=20), 0.34 (E=40) in the same simulation. Pick one, use BCa/studentized, report the discreteness.

Cost, calibrated on heavy1 (9868 s / 81 configs / 4 workers): 9 eps × 1500 seeds × 25 arms ≈ **28 min per environment**; E=20 ≈ 9.3 h, E=25 ≈ 11.6 h. At 500 seeds (validated by a variance-component pilot) E=20 ≈ 3.1 h.

## 4. AIPW/DML: does not apply

Reject, not close. There is no confounding: the SCM is deterministic given the seed, Y and every X are fully observed, and both potential outcomes are recorded per unit, so the augmentation term is identically zero. The "confounders" are the other final bits — **descendants** of the treatment (the treated bit changes which later proposals are accepted) — so conditioning on them is exactly the collider error the study exists to measure, and e(x)=P(x_j=1|x_{−j}) is a selection rule, not an assignment mechanism. Orthogonalisation would launder the collider into an "identification" device. heavy2 already ran the intended positive control and it fails: the exactly-saturating quadratic g-computation (1+18+153 columns, `heavy2.py:66`) gives ≤1e-3 bias at eps≤0.1 but 0.02–0.25 at eps=0.4 and ±0.49 at eps=0.8. A correctly specified model cannot recover the tape-level contrast. Replacement: a seed-level wild/multiplier sup-t band on the exact paired contrast vector over the eps grid — no nuisance models, no cross-fitting.

## 5. (D) is not implementable and has no resolution

`agent_outcome` (`harness.py:119`) has no eps; `run_tape(substrate="agent")` (`harness.py:254`) never touches `Env`; `run_agent_instance` (`run_benchmark.py:194`) has no eps parameter. The only eps in the codebase is `Env.eps` on the synthetic map. The port is already documented as failed (`RESULTS.md:120-123`): identical outcome for all 100 seeds, sd 0.0000, zero focal mutations. Resolution: outcome = `len(visited) + 5·credit + 1e-6·ATP` is integer-quantised (~30 levels); over 200 random genomes I measured 121 unique values, sd 4.29, and uniqueness is carried by the 1e-6 ATP dust — acceptance is decided on floating-point residue. `agent_steps` is also inconsistent: 8 in `run_tape`, 24 in `agent_outcome`/`run_scheduled_tape`.

Minimum change: an explicit eps on a genotype×resource interaction; ≥15×15 world with ≥40 continuous-amount resources; ≥64 steps; ATP tie-breaker dropped or scaled ≥1e-2·credit; pilot resolution gate (≥80% unique outcomes over 1500 genomes). Cost, measured (0.46–0.72 ms per agent step): a depth-40 tape at 64 steps ≈ 1.3 s ≈ 65× a synthetic tape; minimal D (300 seeds × 6 eps × 10 draws × 19 arms) ≈ 8 h at 8 workers; full-fidelity ≈ 30 h.

## REQUIRED CHANGES

1. **Split the estimand.** Report `beta_j − w_j = [beta_j − ATT_j^one-bit] + [ATT_j^one-bit − ATT_j^tape]` per mutation, and call only the first term "specification bias". The second is a re-routing/mediation gap that grows with eps and is what the current S(eps) mostly measures.
2. **Fix or delete A_j(eps).** Delete the slope=1/intercept=0 preregistration (its own algebra implies 2, and it measures slope 0.004–0.415 with intercept up to +0.70). If kept, define it against the matching one-bit estimand, with the 2× factor explicit.
3. **Add the permutation null.** Exact 18! A_j→bias_j label permutation plus J→SJS sign-flip **with re-simulation**; require the observed fit to exceed the 97.5th percentile of both. Cheap: 300 seeds × 200 flips ≈ 1 h.
4. **Add the held-out-background test.** Predict bias at eps>0 from the eps=0 (additive, J-free) natural-arm background. Only this version is non-circular.
5. **Correct the diagnosis.** Replace the "0.5 mass point" mechanism with the order-statistic crossover on a heavy right tail; re-derive the n(M) prescription from that.
6. **Drop n(M) ≥ 24.** The genotype is 18 bits (6 codons × 3), mutation ids are `bit:0>1`, so at most 18 gain loci exist; the union over all 81 heavy1 configs is 16. Either set M = all loci with presence ≥ 0.05 at eps=0 (**≤18**), or raise `CODONS` to ≥10 (30 bits, ~2× cost/call, breaks comparability with heavy1). The sensitivity grid becomes {8, 12, 16, 18}.
7. **Make the mean primary, median descriptive**, chosen before seeing new draws (the median/mean choice is currently post-hoc on the three visible environments).
8. **Fix focal-set selection.** Select M once, from a single fixed pilot at eps=0 (J-free, pre-treatment presence), and hold it identical across all draws and eps; never re-select per environment. Otherwise the mutation level is nested and the crossed bootstrap is invalid.
9. **Raise E to ≥ 20**, keep seeds paired across draws, state the unit of inference as the coupling draw, and add ≥ 2 generator classes (i.i.d. ±1, sparse, block-correlated), with the class effect as the falsifiable part.
10. **Fix the bootstrap.** One estimand only; BCa or studentized; report the median CI width and the discreteness of the env-level resample; reduce B to 2,000 and spend the budget on draws. Report the t-interval route as the biased alternative it is (coverage 0.34–0.63).
11. **Fix the decision rule's units.** `CI lower bound > 0.05·S(eps_max)` compares a slope to a level. Normalise eps to eps/eps_max (then slope = total rise) or write the rule as `> 0.05·S(eps_max)/eps_max`. Anchor at the origin: S(0) is exactly 0 (3e-15 observed).
12. **Reject AIPW/DML.** Replace with a wild/multiplier sup-t band on the exact paired contrasts. Keep the quadratic g-computation only as a documented *failing* positive control, with the heavy2 numbers above as the reason.
13. **Walsh–Hadamard: enumerate, do not sample.** 2^18 = 262,144 genotypes is the whole space; a vectorised numpy sweep gives the exact spectrum in seconds and proves order ≥ 3 is exactly 0. State that this is a fact about the written-down generator, not a control for TEST 1.
14. **Make (D) executable before promising it.** Implement the eps-on-agent knob, raise world/steps, remove the ATP dust, fix `agent_steps` to one value, and gate on a resolution pilot. Note the cost (≈8 h minimal, ≈30 h full) and that the synthetic arm must be reported as the positive control it would otherwise silently become.
15. **Preregister the statistic on held-out draws.** Use env seeds outside {20260927, 20260928, 20260929} for statistic and M (all three are already inspected; the current design is a forking-paths artefact).

## REJECTION

1. The primary statistic, the focal-set size, and the eps floor were all chosen after inspecting the three environments whose failure motivated the change, and the preregistered requirement n(M) ≥ 24 exceeds the 18 loci that exist in an 18-bit genotype — the design cannot be executed as written.
2. The closed-form multiplier A_j(eps) is off by a factor of 2 by the design's own algebra, measures a different estimand from the one reported, and on 300 seeds at the reference environment yields slope 0.004–0.415 and intercept up to +0.70 against a preregistered 1 and 0 — the paper's one quantitative control refutes itself before the run.
3. Ten i.i.d.-coupling draws cannot falsify "the eps-slope varies", the AIPW arm conditions on post-treatment descendants and so re-imposes the collider error under study, and the load-bearing agent substrate has no eps parameter, already returned zero variance across 100 seeds, and decides acceptance on 1e-6 ATP dust.
