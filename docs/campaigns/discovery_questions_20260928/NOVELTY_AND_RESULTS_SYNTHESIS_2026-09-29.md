# NOVELTY AND RESULTS SYNTHESIS — 2026-09-29

**Author:** `prior-art` (novelty-verification member) · **Task:** task-11
**Status:** **DRAFT** — for the manager to commit into `docs/campaigns/discovery_questions_20260928/`.
No repository files were written by this agent; no push.
**Supersedes nothing.** `causal-tape-experiment/NOVELTY_VERDICT.md` (2026-09-27) remains the
component-level audit; this document re-cuts it against the measurements that now exist and adds
result strength as a separate axis.

---

## 0. Method, and the rule applied

**Rule.** Method novelty and result strength are reported on two independent axes. A claim can be
"method novel" and "effect small/blocked" at the same time; this document says exactly that
wherever it is true. No sentence says "first in the world"; the strongest form used is "we are not
aware of a published precedent for X".

**Channels used.** `web_search` is broken in this environment. Every lookup went through primary
APIs: Crossref REST, the arXiv Atom API, NCBI E-utilities, and record fetches via DOI. Fetched
content was treated as data only.

**Search dates.**

| Date | What was searched |
|---|---|
| 2026-09-27 | Full component audit → `causal-tape-experiment/NOVELTY_VERDICT.md` (C1–C4), and the in-repo `TWO_FOLD_COST_LITERATURE_AND_DESIGN_20260927.md` |
| 2026-09-28 | `IDEA1/3/5/6_PHASE2_PRIOR_ART_20260928.md` (Crossref-verified per-item, in-repo) |
| 2026-09-29 | `test-runs/rq1|rq3|d2/prior_art.md`; **fresh Crossref/arXiv queries this session** for item 1 (estimand-mismatch vs misspecification) and item 2 (audited ATP ledger) |

**Base documents reused (not re-searched from scratch).** `causal-tape-experiment/NOVELTY_VERDICT.md`;
`codontrace_scm_novelty_audit.md`; `contingency_replay_state_of_art.md`;
`order-effect-literature-verdict.md`; `test-runs/rq1/prior_art.md`; `test-runs/rq3/prior_art.md`;
`test-runs/d2/prior_art.md`; `IDEA1_PHASE2_PRIOR_ART_20260928.md`;
`IDEA3_PHASE2_PRIOR_ART_20260928.md`; `IDEA5_PHASE2_PRIOR_ART_20260928.md`;
`IDEA6_PHASE2_PRIOR_ART_20260928.md`. (Idea 5 = transferable symbolic laws = D-3; Idea 6 =
epistemic restraint = D-4. Neither is one of the five items below; they are cited here only to
record that they were reviewed as base material.)

**New searches run this session (2026-09-29).** Two targeted Crossref/arXiv query sets, only where
a genuinely new claim needed a comparison: (i) estimand mismatch vs model misspecification in
counterfactual analyses; (ii) audited energy ledger / ATP cost of sex in a digital organism. Results
are folded into items 1 and 2 below. OpenAlex full-text search returned HTTP 429 throughout and is
listed as an open item in §10.

---

## 1. CausalTape exact `do()` on the mutation draw, and the estimand split

### 1.1 The exact novelty claim

Two separable claims:

* **(1a) Method.** `do(m := suppressed)` suppresses the drawn substitution while still consuming the
  RNG draw, so the stream digest is identical across arms and the counterfactual differs from the
  factual arm in that event alone. The intervention does not rewind or re-key the stream.
* **(1b) Estimand split.** `beta − ATT_whole_tape = (beta − ATT_onebit) + (ATT_onebit − ATT_whole_tape)`,
  i.e. the quantity previously reported as estimator bias separates into a **linear-model
  misspecification** term and a **whole-tape re-routing** term (the gap between a one-bit contrast
  and the whole-tape contrast that suppression actually produces).

### 1.2 Closest prior art

| Prior art | Relation | URL | Search date |
|---|---|---|---|
| Heckman 1979, *Econometrica* 47(1):153–161 | The naive-vs-ATT selection-bias decomposition is textbook; the identity is not new | https://doi.org/10.2307/1912352 | 2026-09-27 / re-verified 2026-09-29 |
| Marshall & Galea 2015, *Am. J. Epidemiol.* 181(2):92–99 | In simulation, exchangeability is free by construction; identifiability rests on ergodicity + specification | https://doi.org/10.1093/aje/kwu274 | 2026-09-27 |
| Díaz-Uriarte, Ríos-Arroyo & Johnston 2026, arXiv:2606.12597 | **Forecloses any "new application of the do-operator" framing**: conditioning on the absence of a mutation gives incorrect predictions | https://doi.org/10.48550/arXiv.2606.12597 | 2026-09-27 |
| Wahl & Agashe 2022, *Evolution* 76(6) | Selection bias in mutation-effect/DFE estimation, quantified and corrected, against a known true DFE | https://doi.org/10.1111/evo.14430 | 2026-09-27 |
| Klein, Abeysuriya, Stuart & Kerr 2024, arXiv:2409.02086 | Noise-free paired counterfactuals by aligning random-number realisations across interventions | https://doi.org/10.48550/arXiv.2409.02086 | 2026-09-27 |
| Buffalo, Pearson & Klein 2026, arXiv:2603.11084 | Formalises the SCM incoherence of execution-path-dependent draw indexing; remedy is event-keyed hashing. **Load-bearing: it is the published account of the failure mode the RNG-preserving `do()` avoids** | https://doi.org/10.48550/arXiv.2603.11084 | 2026-09-27 |
| Schruben & Margolin 1978, *JASA* 73(363):504–514 | Classical common-random-numbers assignment | https://doi.org/10.1080/01621459.1978.10480044 | 2026-09-27 |
| **"Missing the target in target trial emulation" 2025, *Critical Care*** | **New this session.** "Estimand mismatch" — a naive estimator biased because it targets a *different* estimand — is an occupied conceptual frame in clinical statistics | https://doi.org/10.1186/s13054-025-05515-3 | 2026-09-29 |
| ICH E9(R1) estimand-framework literature, e.g. *Stat. Biopharm. Res.* 2022 | The estimand/misspecification distinction is standardised outside evolution | https://doi.org/10.1080/19466315.2022.2081601 | 2026-09-29 |

**Not found:** a published *measurement* of a whole-tape re-routing share as a fraction of an
estimator's bias, and a bit-reproducible evolution simulator whose `do()` preserves the RNG stream.

### 1.3 Measured result (verified against raw evidence)

| Quantity | Value | Evidence |
|---|---|---|
| Scale | 3 coupling draws × 9 epistasis levels × 3 depths, 1500 paired seeds/cell = 121,500 paired seeds | `codontrace-genesis/docs/campaigns/causal_tape_20260927/RESULTS.md` §1 |
| Stream digest | unchanged across arms (asserted equal); neutral fast path reproduces engine mutation operator exactly | same, §1 "Instrument" |
| Re-routing share, eps = 0.8, **published estimator** | **64.1 %**, 95 % CI **[55.8, 73.3]** (bootstrap median of the pooled ratio of medians) | `test-runs/verify/CLAIMS.json` → `claims.C`; `test-runs/verify/claim-c.md` |
| Raw pooled ratio of medians | **62.97 %** | `test-runs/verify/CLAIMS.json` (`ratio_of_medians.pooled_point_estimate_percent`) |
| Mean over draws of per-draw ratio of medians | **63.75 %** | same, `mean_over_draws_of_per_draw_ratio_of_medians` |
| Ratio of means (pooled) | **64.8 %**, 95 % CI **[59.9, 69.2]** | same, `ratio_of_means` |
| Per-draw heterogeneity (ratio of means) | **0.44 / 0.83 / 0.71** across the three coupling draws | same, `per_coupling_draw` |
| Fit health | rank 172/172, R² = 1.000000000000000, max residual ≤ 3.3e-13, identity residual 1.1e-16 | `claim-c.md` §"Fit health"; `RESULTS.md` §1 |
| Independent recompute | reproduced the published median and both CI endpoints **bit-exactly**; ACCEPT | `test-runs/verify/CLAIMS.json` `overall_verdict: "pass"`; `test-runs/verify/claim-c.md` |
| Independence caveat | 5.5 % of exposed seeds (up to 38 % for one locus) had the locus cleared by a later accepted reversal at eps = 0.8 | `RESULTS.md` §1 |

### 1.4 Verdict

| Axis | Verdict |
|---|---|
| **Method novelty** | **NOVEL (narrow).** We are not aware of a published precedent for a bit-reproducible digital-evolution simulator whose `do()` on a mutation draw suppresses the event while consuming the draw, so the random-stream digest is provably unchanged. |
| **Concept novelty of (1b)** | **PARTIALLY OCCUPIED.** "Estimand mismatch ≠ model misspecification" is old and occupied (§1.2, 2025 *Critical Care*). What is unoccupied is measuring the **whole-tape re-routing share** in an evolutionary simulator. |
| **Result strength** | **MODERATE, and estimator-sensitive.** The instrument result is strong (bit-exact independent recompute, 121,500 paired seeds, machine-precision specification check). The headline number is weaker than it looks: four defensible estimators give 62.97 %, 63.75 %, 64.1 % and 64.8 %; the quotient spans 0.44–0.83 across coupling draws; the CI is knife-edge sensitive to the bootstrap rank tolerance: **[56.02, 73.25]** under a Cholesky rank test vs **[55.78, 73.33]** under the published 1e-8 SVD test, because the admissibility test is a floating-point knife-edge and a rejection consumes an extra RNG draw (500 bootstrap draws; 6 resamples sit on the boundary per `claim-c.md`). |
| **Effect on the novelty claim** | **STRENGTHENS (method only).** The verified bit-exact recompute is what makes (1a) a real instrument claim, and (1a) is the part that is unoccupied. It does **not** strengthen (1b) as a conceptual claim, and it **weakens** the practice of quoting "64.1 %" as a single number without the estimator label. |

---

## 2. Two-fold cost of sex in an audited closed ATP ledger with a matched-allele antagonist

### 2.1 The exact novelty claim

Charge Maynard Smith's two-fold cost as an explicit ATP debit inside a conserved, audited ledger
(with an injected-leak negative control for the audit itself), in a matching-allele host–antagonist
system. The distinctive ingredient added to the classical 2× is an **irreversible per-mating
dissipation** `c_sex = 2c(1+δ)` that is destroyed rather than transferred between ledger accounts.

### 2.2 Closest prior art

| Prior art | Relation | URL | Search date |
|---|---|---|---|
| Misevic, Ofria & Lenski 2006, *Proc. R. Soc. B* 273:457–464 | **Direct digital-organism sex-cost precedent.** Avida's cost is demographic; energy scales with genome length, not a closed ledger | https://doi.org/10.1098/rspb.2005.3338 | 2026-09-27 |
| Misevic, Ofria & Lenski 2010, *J. Heredity* 101(S1):S46–S54 | Digital organisms, evolvable reproductive mode; sex dominates only under rapid environmental change; no ledger audit | https://doi.org/10.1093/jhered/esq017 | 2026-09-27 |
| Goyal et al. 2023, *PNAS* 120(52):e2309387120 | Rigorous closed-ecosystem energy/closure framing — but no sex cost | https://doi.org/10.1073/pnas.2309387120 | 2026-09-27 |
| **Yasui & Hasegawa 2024**, Research Square preprint | **The most dangerous citation**: resource limitation removes the realised two-fold cost; a closed ledger is by construction resource-limited | https://doi.org/10.21203/rs.3.rs-4360051/v1 | 2026-09-27 |
| Yasui 2026, *J. Evol. Biol.* 39(9):1154–1168 | Peer-reviewed version; Red Queen alone insufficient | https://doi.org/10.1093/jeb/voag069 | 2026-09-27 |
| Otto & Nuismer 2004, *Science* 304:1018–1020 | Interactions "typically select against sex" — the a priori expectation the test confirms | https://doi.org/10.1126/science.1094072 | 2026-09-27 |
| Morran et al. 2011, *Science* 333:216–218; Slowinski et al. 2016, *Evolution* 70:2632–2639 | Empirical Red Queen / treatment structure precedent | https://doi.org/10.1126/science.1206360 · https://doi.org/10.1111/evo.13048 | 2026-09-27 |
| Fresh 2026-09-29 Crossref query ("audited energy ledger ATP cost of sex digital organism") | **No new hit.** The combination remains unoccupied | — | 2026-09-29 |

### 2.3 Measured result (verified against raw evidence)

**Instrument gates (all pass).**

| Gate | Result | Evidence |
|---|---|---|
| Ledger identity, all arms | max residual **1.2e-10** | `codontrace-genesis/docs/campaigns/causal_tape_20260927/RESULTS.md` §2 |
| Per-mating dissipation audit | exact, zero error | same |
| Injected leak 1e-3 / host / generation | **detected**, residual 17.1 | same |
| Positive control: costless sex + antagonist | **0.478** ± 0.158, no extinction | same |
| Negative control: 2× cost, no antagonist | **8.6e-5**, extinction in every run | same |

**Main confirmatory sweep — 100 paired seeds per arm, 400 generations.**

| Cost ratio | Sexual frequency | Evidence |
|---|---|---|
| 1.0 (costless + antagonist) | **0.478** | `causal-tape-experiment/results/sex_arms_results.json` (`A8a_sex_cost1.0_parasite`) |
| 1.5 + antagonist | **0.0004** | same (`A8b_sex_cost1.5_parasite`) |
| 3.0 + antagonist | **0.000** | same (`A8c_sex_cost3.0_parasite`) |
| 2.0 + antagonist | 0.0000, **100 % extinct**, median 125 generations | `RESULTS.md` §2 |
| 2.0 + added dissipation δ, + antagonist | 0.0000, extinct, median **80** generations | `RESULTS.md` §2 |
| 2.0 + **non-evolving** antagonist | 0.0000 (infection only 3 %) | `RESULTS.md` §2 |
| No cost, no antagonist | 0.391 | `causal-tape-experiment/RESULTS3.md` §2 |

→ The main evidence supports a critical cost **c\* ∈ (1.0, 1.5]**, and refuses both pre-registered
rescue rules (P4, P5). Across four further regimes, `any_regime_with_costless_sex_persisting = true`
while `any_regime_with_costly_sex_persisting = false`
(`sex_arms_results.json` → `regime_sweep`).

**The "~1.1–1.2" narrowing — demote to probe level.** The only artifact behind it is a
**single-seed probe**:

```
causal-tape-experiment/phase_probe.py   →   causal-tape-experiment/phase_probe.txt
  critical-cost probe, infection_cost=0.4, parasite_mutation=0.005   (seed 9000)
  turnover=1   c=1.0:0.267  c=1.1:0.203  c=1.2:0.012X  c=1.25:0.000X  c=1.5:0.000X
  turnover=6   c=1.0:0.422  c=1.1:0.079  c=1.2:0.053   c=1.25:0.003X  c=1.5:0.000X
  turnover=12  c=1.0:0.742  c=1.1:0.285  c=1.2:0.000X  c=1.25:0.009X  c=1.5:0.000X
```

There is **no `phase_results.json` anywhere in the workspace** (glob over the whole tree returned no
match), yet `codontrace-genesis/docs/campaigns/discovery_questions_20260928/TESTS_DONE_STATUS_2026-09-29.md:57–61`
cites `phase_results.json` as the evidence for the 1.1–1.2 narrowing. The narrowing is real as a
probe signal but it is **n = 1 seed, 5 cost values, 3 turnovers**, not a confirmed sweep.

### 2.4 Verdict

| Axis | Verdict |
|---|---|
| **Method novelty** | **PARTIALLY NOVEL / PARTIALLY OCCUPIED.** Each component is published (§2.2). We are not aware of a published precedent for the combination: an explicit irreversible ATP dissipation with no counterpart ledger entry, inside a conserved ledger that is audited every generation with an injected-leak control, in a matching-allele host–antagonist system. |
| **Result strength** | **NEGATIVE result, honest, and useful as a bound.** No regime rescues costly sex; the distinctive δ arm makes it *worse* (median extinction 80 vs 125 generations). A non-evolving antagonist does nothing, so coevolution — not antagonist presence — is required. |
| **Effect on the novelty claim** | **WEAKENS the scientific payload, leaves the method claim untouched.** The method claim does not rest on a positive effect, and the team already reports the negative. But the *distinctive* ingredient (irreversible dissipation) produced no positive effect anywhere, so novelty here is a methods/design niche, not a discovery. |
| **Must be fixed before this number is cited** | The `c* ≈ 1.1–1.2` narrowing must either be re-run at the confirmatory seed count (100 paired seeds over 1.0/1.1/1.2/1.25/1.5) or be quoted explicitly as "single-seed probe, `phase_probe.txt`". The `phase_results.json` reference in `TESTS_DONE_STATUS_2026-09-29.md` is a dangling citation. |

---

## 3. RQ-1 time-shift (past / present / future antagonist)

### 3.1 The exact novelty claim

**There is none, and none is made.** `test-runs/rq1/prior_art.md` states it directly: *"None that is
a novelty claim. RQ-1's design is the standard time-shift assay."* The pack's own two additions
(primary quantity = interaction contrast of `π_realised` with the frequency histogram excluded from
the estimand; negative control = random permutation of time labels) are described there as
measurement hygiene, not a scientific first.

### 3.2 Closest prior art (search date 2026-09-29)

| Prior art | Relation | URL |
|---|---|---|
| Decaestecker et al. 2007, *Nature* 450:870–873 | The original time-shift design: a past antagonist assayed against present vs past hosts | https://doi.org/10.1038/nature06291 |
| Gaba & Ebert 2009, *TREE* 24(4):226–232 | Reviews time-shift as a standard instrument; confirms a 3×3 cross-time matrix is not novel | https://hal.inrae.fr/hal-02667425v1/dc |
| Gibson et al. 2020, *Biology Letters* 16:20200210 | Experimental test of antagonist adaptation to common vs rare host genotypes | https://doi.org/10.1098/rsbl.2020.0210 |
| Buckingham & Ashby 2022, *J. Evol. Biol.* 35:205–224 | Short time-shift windows can look directional under fluctuating selection (why the interaction contrast is demanded) | https://doi.org/10.1111/jeb.13981 |
| Fortuna et al. 2016, *Nature Communications* 7:12462 | Digital host–parasite networks already exist in Avida | https://www.nature.com/articles/ncomms12462 |
| Zaman 2014 PhD thesis | Digital host–symbiont coevolution with archived lineages | http://diyhpl.us/~bryan/papers2/Host-symbiont%20coevolution%20in%20digital%20and%20microbial%20systems%20-%20Zaman%20-%20thesis%20-%202014.pdf |
| Yedid, Ofria & Lenski 2008, *Am. Nat.* 171(4):E128–E144 | Re-evolution of a complex digital trait is published | https://pubmed.ncbi.nlm.nih.gov/18564346/ |

### 3.3 Measured result

**Pilot (round 2).** 6 independent histories (2 calibration + 4 pilot seeds) × 3 arms × 40
generations. Evidence: `test-runs/rq1/decision.md`, `test-runs/rq1/analysis_live.json`.

| Arm | labels over 6 seeds | `I_contemp` mean [95 % run-level bootstrap] | `I_lag` mean [95 %] | supports |
|---|---|---|---|---|
| copassaged (coevolve) | `lagged_match`, `contemporary_match`, `other`×4 | **+0.005396** [+0.003430, +0.007602] | **−0.003454** [−0.005321, −0.001438] | 0/6 |
| fixed (frozen) | `flat`×6 | **0.0** [0, 0] | 0.0 [0, 0] | 0/6 |
| avirulent (host-only) | `flat`×6 | 0.0 [0, 0] | 0.0 [0, 0] | 0/6 |

Rotation control: **0 of 18** shuffled time-label permutations receive a support label.
Pilot verdict: `INCONCLUSIVE` (the full pre-declared pattern does not hold; 0/6 support labels).

**Confirmatory pack — LOCKED, IN FLIGHT.**

* Locked config: 8 unseen seeds 5701–5708 × 3 arms (contemporary / lagged / frozen) × **200
  generations**; config digest `rq1_confirmatory:d44a70140eeef5876ea68c838ca442de38f5e05cfeaeabd71bab2be38479c807`;
  provenance `6187ff4` (isolated extraction `test-runs/verify/full6187ff4`).
* **Completed and analysed: 2 of 8 seeds** (5701, 5702). `test-runs/rq1/confirmatory/run_manifest.json`
  → `seeds_completed: [5701, 5702]`, `seeds_remaining: [5703 … 5708]`, `status: "partial"`.
* **Seed 5703 is in flight**: `raw/events_seed5703.jsonl`, `raw/population_seed5703.jsonl`,
  `raw/summary_seed5703.jsonl` exist and are listed in `raw_artifacts`, but 5703 is **not** in
  `seeds_completed` and the analysis does not include it.

| Arm | n | mean | 95 % paired-t interval vs frozen | excludes zero |
|---|---|---|---|---|
| contemporary | 2 | +0.00679179935 | **[−0.0558017386, +0.0693853373]** | **No** |
| lagged | 2 | −0.00164865675 | [−0.0345598529, +0.0312625394] | No |
| frozen | 2 | 0.0 (exactly) | [0.0, 0.0] | — |
| contemporary − lagged | 2 | +0.0084404561 | [−0.087064278, +0.1039451902] | No |

Evidence: `test-runs/rq1/confirmatory/decision.md`, `analysis_confirmatory.json`,
`effect_table_confirmatory.json`. Integrity: `raw_recompute_matches_all_seeds = true`,
`frozen_exactly_zero = true`, shuffled labels **0/6** support labels.
Verdict: **`INCONCLUSIVE`** · `hypothesis_supported = false` · `red_queen_proved = false`.

**Honest statement of the in-flight status.** At n = 2 the confirmatory interval **contains zero**;
one of the two completed seeds carries a support label. No support is claimed, and the pack must not
be described as trending either way.

### 3.4 Verdict

| Axis | Verdict |
|---|---|
| **Method novelty** | **NONE CLAIMED.** The design is the standard time-shift assay; the pack's own prior-art note says so. |
| **Result strength** | **INCONCLUSIVE, in flight.** The pilot's contemporary diagonal is small but positive with a seed-level interval excluding zero; the locked confirmatory interval at n = 2 contains zero. Neither is a result. |
| **Effect on any novelty claim** | **UNTOUCHED** — there is no novelty claim to strengthen or weaken. The measurement-hygiene additions (histogram excluded from the estimand; label permutation control) are defensible practice, not novelty, and the rotation control passing (0/6, 0/18) is a validation of the instrument, not a discovery. |

---

## 4. RQ-3 adaptation-route cut (heritable feedback removed, contact and energy cost retained)

### 4.1 The exact novelty claim

Not the phenomenon (rare-host advantage, time-shift reconstruction, and "cycling ≠ Red Queen" are all
published) but the **operational cut**: run the antagonist with real contact and real energy cost
while removing its heritable feedback in two independent ways — frozen composition, and an update
cut from the host labels — and measure whether the delayed frequency-to-pressure link and the
rare-class growth advantage survive. `test-runs/rq3/prior_art.md` frames this as a claim about *this
model's mechanism boundary*, not about biology.

### 4.2 Closest prior art (search date 2026-09-29, from `test-runs/rq3/prior_art.md`)

| Prior art | Relation | URL |
|---|---|---|
| Decaestecker et al. 2007, *Nature* 450:870–873 | Time-shift assay is not novelty | https://doi.org/10.1038/nature06291 |
| Gibson et al. 2020, *Biology Letters* 16:20200210 | Rare/common host-genotype advantage already tested empirically | https://doi.org/10.1098/rsbl.2020.0210 |
| Buckingham & Ashby 2022, *J. Evol. Biol.* 35:205–224; 2024, *J. Theor. Biol.* 579:111688 | Timescale separation is analytic; RQ-3's cut is an operational cut on a running population | https://doi.org/10.1111/jeb.13981 · https://doi.org/10.1016/j.jtbi.2023.111688 |
| Morran et al. 2011, *Science* 333:216–218; Ashby 2020, *J. Evol. Biol.* | Polymorphism and cycling are not by themselves Red Queen dynamics — the reason the control arm exists | https://doi.org/10.1126/science.1206360 · https://doi.org/10.1111/jeb.13718 |
| Schenk, Schulenburg & Traulsen 2020, *BMC Evol. Biol.* | Genetic drift limits Red Queen dynamics; demography matters | https://doi.org/10.1186/s12862-019-1562-5 |
| Acosta & Zaman 2022, *Front. Ecol. Evol.* 9:750772 | Digital host–parasite factorial is published; no new medium claimed | https://doi.org/10.3389/fevo.2021.750772 |
| Fortuna et al. 2016, *Nature Communications* 7:12462 | Digital coevolutionary ecology has precedent | https://doi.org/10.1038/ncomms12462 |

### 4.3 Measured result

**Round 3, on the landed opt-in `antagonist_ecology="population"`.** Evidence:
`test-runs/rq3/decision.md`, `test-runs/rq3/out_round3_contrast_tip.txt`,
`test-runs/rq3/out_r3_regression_tip.txt`.

Arms, with `antagonist_maintenance_cost = 0.15` pre-declared and **identical in every arm**:

| Quantity (seed 21051, 60 generations) | coevolve | frozen | shuffled-labels |
|---|---|---|---|
| Common-window share, generation 10 | 0.094 | 0.0625 | 0.0625 |
| **Common-window share, generation 60** | **0.172** | **0.0625** | **0.0625** |
| Final distinct classes / roster | 16 / 64 | 16 / 64 | 16 / 64 |
| Extinct | no | no | no |

The coevolving antagonist accumulates the window matching the common host class to 2.75× its
ancestral frequency; **both cut arms sit exactly at the ancestral 1/16 = 0.0625**, so the negative
control separates. Absolute margin: **0.109 share after 60 generations** — explicitly reported as a
**small** effect by the pack itself.

**Locked regression** (seed 43, copassaged, 50 generations, opt-in ON): `empty_hist_generations = 0`,
`parasite_n` at generation 25 = 64, histogram non-empty, final distinct classes 28
(`out_r3_regression_tip.txt`).

Decision: **`INCONCLUSIVE`** (behavioural separation in one pilot contrast, energy-confounded; corrected controls at n = 3 give intervals containing zero) · claim ceiling **`phase2_design`** ·
`hypothesis_supported = false` · `red_queen_proved = false`.

**Limitations the pack states and this document repeats.** The single contrast seed is 21051 (plus
regression seed 43); there is no interval and no multi-seed replication. `git` is not installed, so
the run is pinned by **checksum against a filesystem snapshot**, not by commit `913f18e`
(`decision.md` §6) — a reader must checksum-compare the two changed files before accepting the
numbers. The default-path pytest run was **22 passed, 1 failed**, the failure being a cwd-relative
`FileNotFoundError` in `test_p3_engine_has_no_hp_domain_physics_tokens`, not a code defect.

### 4.4 Verdict

| Axis | Verdict |
|---|---|
| **Method novelty** | **NOVEL (narrow).** We are not aware of a published precedent for cutting an antagonist's heritable route in two independent ways at matched contact and matched energy cost on a running digital population. The two cuts behaving *identically* (both exactly 0.0625) while the coevolving arm moves is the mechanism-boundary evidence. |
| **Result strength** | **WEAK but decisive as a separation.** 0.172 vs 0.0625 is a clean negative-control separation, and the regression confirms the mechanism is live; but it is one contrast seed, no interval, and the pack itself calls the effect small. This is "method novel, effect small" — exactly the description the brief asks for. |
| **Effect on the novelty claim** | **STRENGTHENS (weakly).** The cut is the novelty, and the cut separated. It does **not** strengthen the general claim (cycling ≠ Red Queen is Ashby 2020 / Morran 2011), and it does **not** support any claim about sex, recombination or the two-fold cost — the pack says so explicitly. |

---

## 5. D-2 function-recovery window with contact structure

### 5.1 The exact novelty claim

A **causal mediation** claim: at fixed intervention time, function recovery differs between a
*named scaffold-edge cut* and a *degree/ATP/edge-count-matched random cut*, and the difference is
attributable to **which organisms held the cut contact edges** (endpoint-specific realised contact
loss) rather than to a **global cost penalty**. The refusal test is stated up front: if both cuts
have the same realised contacts and trajectory, or the only difference is penalty magnitude, the
mediation claim is dead.

### 5.2 Closest prior art (search date 2026-09-29, from `test-runs/d2/prior_art.md`)

| Prior art | Relation | URL |
|---|---|---|
| Yedid, Ofria & Lenski 2008, *J. Evol. Biol.* 21:1335 | Re-evolution of a complex digital trait after loss is published; no per-edge mediation | https://doi.org/10.1111/j.1420-9101.2008.01564.x |
| Yedid, Ofria, McKelvey & Lenski 2009, *Am. Nat.* | Delayed ecological recovery after press extinction; community diversity, not contact-topology membership | https://doi.org/10.1086/597228 |
| Blount, Lenski & Losos 2018, *Science* 362:eaam5979 | Replay divergence alone is not a result | https://doi.org/10.1126/science.aam5979 |
| Fortuna et al. 2016, *Nature Communications* 7:12462 | Whole-network robustness, not per-edge causal mediation | https://www.nature.com/articles/ncomms12462 |
| Wilkins-Reeves et al. 2026, single-network asymptotics | Causal estimation under network interference; unit is the node, not the independent history | https://raw.githubusercontent.com/mlresearch/v337/main/assets/wilkins-reeves26a/wilkins-reeves26a.pdf |
| Great-tit network removal experiment | Network removal changes function; field system, no cost-matched sham, no run-level randomisation interval | https://kops.uni-konstanz.de/server/api/core/bitstreams/b78b41f1-7b5d-45c5-bd5f-6d0e80c3ce8e/content |

### 5.3 Measured result — **`FALSIFIED_IN_MODEL`** (calibration tier)

Evidence: `test-runs/d2/decision.md`, `test-runs/d2/analysis_round4.json`,
`test-runs/d2/raw/round4/round4_raw.json` (round 4 supersedes the round-3 pack in
`analysis_round3.json` / `raw/round3/round3_raw.json`, whose contrasts are inadmissible).

Design (round 4): 6 independent histories (seeds 5501, 5502 × checkpoints t = 10, 20, 30) on the
persistence-safe ecology; each arm is built by **independent re-simulation** (`from_spec` per arm,
no `capture_fork`), so isolation holds: all 18 populations are distinct objects, `fork_used = false`,
same-arm interleaved runs are identical and different arms diverge only after the checkpoint.
Horizon 40 boundaries; **18 arm runs**.

| Arm | runs | P(recover, pre-registered) | P(digest return, exploratory) | mean n_alive at T | max yield / baseline |
|---|---|---|---|---|---|
| `cut_named_scaffold` | 6 | **0.00** | 0.00 | 2.0 | **0.059** |
| `cut_matched_random` | 6 | **0.00** | 0.00 | 2.0 | **0.573** |
| `sham` | 6 | **0.00** | 0.00 | 2.0 | 0.570 |

* **0 of 18 runs recovered** under the pre-registered endpoint `FI-RARECLASS-CONTACT-YIELD-V1`
  (locked 2026-09-28: yield ≥ 1.25× baseline for ≥ 3 consecutive boundaries within T = 40). The
  largest yield ratio anywhere is **0.573**, well below the locked 1.25×.
* The exploratory endpoint `GENOME-DIGEST-LOST-THEN-REGAINED-V1` (2026-09-29) is versioned separately
  and never pooled; it is also 0.00 in every arm.
* Recovery *opportunity* exists (`n_alive_end_zero_rate = 0.00` in every arm, vs 100 % extinction in
  round 2) — but the endpoint does not move.
* **Isolation now passes** (round 4): `fork_used = false`; the per-arm populations are distinct
  objects and a mutation in one arm does not move another arm's digests. Round 3's
  `population_object_shared_with_history = true` residual is therefore bypassed by design rather
  than papered over, and no engine change was needed for this result. The residual remains open
  only for consumers that need a self-contained serialisable fork (`capture_fork` carries live
  objects; `fork_audit_payload()` provides the serialisable audit view).

Verdict: **`FALSIFIED_IN_MODEL`** (calibration tier; 6 histories cannot exclude a rare recovery) ·
`hypothesis_supported = false` · `red_queen_proved = false`.

### 5.4 Verdict

| Axis | Verdict |
|---|---|
| **Method novelty** | **POTENTIALLY NOVEL, but unevidenced.** We are not aware of a published precedent for a degree/ATP/edge-count-matched random cut versus a named scaffold-edge cut with a cost-penalty refusal test on forked digital histories. The design is the novel object. |
| **Result strength** | **FALSIFIED_IN_MODEL (calibration tier).** 0/18 runs on the pre-registered 1.25× endpoint (max yield ratio 0.573). Round 4 builds each arm by independent re-simulation, so isolation passes and the falsification is admissible; the scope is honest — 6 histories cannot exclude a rare recovery. |
| **Effect on the novelty claim** | **WEAKENS (cannot be supported).** No evidence exists to attach to the mediation claim; per the pack, no window law, slope, |ΔP| or effect estimate is claimed. The claim stays a design claim until fork isolation lands. |

---

## 6. Summary — method novelty vs result strength

| # | Item | Method novelty | Result strength | Strengthens / weakens / untouched |
|---|---|---|---|---|
| 1 | CausalTape exact `do()` on the mutation draw + estimand split | **Novel (narrow)** for the RNG-stream-preserving `do()`; **partially occupied** for "estimand mismatch ≠ misspecification" | **Moderate, estimator-sensitive**; instrument verification is strong (bit-exact, 121,500 paired seeds) | **Strengthens** the instrument claim; **weakens** quoting "64.1 %" unlabelled (4 estimators: 62.97 / 63.75 / 64.1 / 64.8 %); **untouched** conceptually |
| 2 | Two-fold cost in an audited closed ATP ledger | **Partially novel / partially occupied** | **Negative** (no rescue; δ makes it worse) | **Weakens** the scientific payload; **leaves the method claim untouched**; **flags** the probe-only `c* ≈ 1.1–1.2` |
| 3 | RQ-1 time-shift | **None claimed** (standard assay) | **INCONCLUSIVE, in flight** — 2/8 seeds, interval contains zero at n = 2 | **Untouched** |
| 4 | RQ-3 adaptation-route cut | **Novel (narrow)** — the matched-cost heritable-route cut | **INCONCLUSIVE** — one pilot contrast, energy-confounded; at n = 3 both paired intervals include zero | **Strengthens weakly**; **weakens** any effect-size framing |
| 5 | D-2 recovery window | **Potentially novel, unevidenced** | **FALSIFIED_IN_MODEL** (calibration tier) — 0/18, max yield ratio 0.573 vs the locked 1.25×; isolation passes with per-arm re-simulation | **Weakens** (no recovery evidence to attach) |

**One-line honest summary.** Across the five items the pattern is consistent: **method novelty is
real but narrow, and the measured effects are either small, negative, or blocked.** Item 1 has the
strongest verification and the weakest single headline number; item 4 is the only positive
confirmatory result and it is small; items 2, 3 and 5 currently carry no positive result at all.

---

## 7. Flags the manager must carry into the campaign record

1. **RQ-1 confirmatory is IN FLIGHT, not complete.** 2 of 8 locked seeds (5701, 5702) analysed;
   seed 5703 raw files are being written; 5704–5708 not started. At n = 2 the contemporary-vs-frozen
   interval is **[−0.0558, +0.0694]** and **contains zero**. `hypothesis_supported = false`,
   `red_queen_proved = false`. Do not describe the pack as supported, trending, or near-threshold.
2. **D-2 is `FALSIFIED_IN_MODEL` on the calibration tier.** 0/18 recovery on the pre-registered
   1.25× endpoint (max yield ratio **0.573**). Round 4 supersedes round 3: each arm is built by
   independent re-simulation (`from_spec` per arm, `fork_used = false`), so isolation passes and the
   falsification is admissible. Scope, stated honestly: 6 histories cannot exclude a rare recovery.
   Nothing was tuned, and the `test-runs/d2/` pack retains the round-3 `BLOCKED_MEASUREMENT` record
   as superseded history.
3. **New dangling citation.** `TESTS_DONE_STATUS_2026-09-29.md` cites `phase_results.json` for the
   `c* ≈ 1.1–1.2` narrowing; that file does not exist in the workspace. The only evidence is
   `causal-tape-experiment/phase_probe.txt` (single seed 9000). Either re-run the fine sweep at
   confirmatory seed count or annotate the number as probe-level.
4. **RQ-3 provenance is a checksum snapshot, not a commit.** `git` is not installed in this
   environment; `913f18e` is asserted by manager confirmation. The two changed files must be
   checksum-compared before the round-3 numbers are treated as commit-pinned.
5. **Claim ceilings unchanged.** Every item above stays at `phase2_design` or lower.
   `hypothesis_supported = false` and `red_queen_proved = false` everywhere. No item here licenses a
   raise of any ClaimGate ceiling, and no item is a "first in the world".

---

## 8. Prior art that must be cited (consolidated, with URLs)

**Item 1 — estimand, estimator bias, noise-free replay.** Heckman 1979 https://doi.org/10.2307/1912352 ·
Marshall & Galea 2015 https://doi.org/10.1093/aje/kwu274 · Díaz-Uriarte, Ríos-Arroyo & Johnston 2026
https://doi.org/10.48550/arXiv.2606.12597 · Wahl & Agashe 2022 https://doi.org/10.1111/evo.14430 ·
Klein, Abeysuriya, Stuart & Kerr 2024 https://doi.org/10.48550/arXiv.2409.02086 · Buffalo, Pearson &
Klein 2026 https://doi.org/10.48550/arXiv.2603.11084 · Schruben & Margolin 1978
https://doi.org/10.1080/01621459.1978.10480044 · "Missing the target in target trial emulation" 2025
https://doi.org/10.1186/s13054-025-05515-3 · ICH E9(R1) estimand framework, e.g.
https://doi.org/10.1080/19466315.2022.2081601 · Cornish, Taufiq, Doucet & Holmes 2026
https://doi.org/10.48550/arXiv.2301.07210.

**Item 2 — two-fold cost, digital sex, energy budgets.** Maynard Smith 1971
https://doi.org/10.1016/0022-5193(71)90058-0 · Williams 1975 (book) · Hamilton 1980
https://doi.org/10.2307/3544435 · Otto & Nuismer 2004 https://doi.org/10.1126/science.1094072 ·
Agrawal 2009 https://doi.org/10.1111/j.1558-5646.2009.00695.x · Morran et al. 2011
https://doi.org/10.1126/science.1206360 · Slowinski et al. 2016 https://doi.org/10.1111/evo.13048 ·
Misevic, Ofria & Lenski 2006 https://doi.org/10.1098/rspb.2005.3338 · Misevic, Ofria & Lenski 2010
https://doi.org/10.1093/jhered/esq017 · Goyal et al. 2023 https://doi.org/10.1073/pnas.2309387120 ·
Yasui & Hasegawa 2024 https://doi.org/10.21203/rs.3.rs-4360051/v1 · Yasui 2026
https://doi.org/10.1093/jeb/voag069 · Zaman et al. 2014 https://doi.org/10.1371/journal.pbio.1002023.

**Item 3 — time-shift.** Decaestecker et al. 2007 https://doi.org/10.1038/nature06291 · Gaba & Ebert
2009 https://hal.inrae.fr/hal-02667425v1/dc · Gibson et al. 2020
https://doi.org/10.1098/rsbl.2020.0210 · Buckingham & Ashby 2022 https://doi.org/10.1111/jeb.13981 ·
Fortuna et al. 2016 https://www.nature.com/articles/ncomms12462 · Blount, Lenski & Losos 2018
https://doi.org/10.1126/science.aam5979.

**Item 4 — heritable-route cut, Red Queen non-identity.** Buckingham & Ashby 2022
https://doi.org/10.1111/jeb.13981 and 2024 https://doi.org/10.1016/j.jtbi.2023.111688 · Ashby 2020
https://doi.org/10.1111/jeb.13718 · Morran et al. 2011 https://doi.org/10.1126/science.1206360 ·
Schenk, Schulenburg & Traulsen 2020 https://doi.org/10.1186/s12862-019-1562-5 · Acosta & Zaman 2022
https://doi.org/10.3389/fevo.2021.750772 · Decaestecker et al. 2007
https://doi.org/10.1038/nature06291 · Gibson et al. 2020 https://doi.org/10.1098/rsbl.2020.0210.

**Item 5 — recovery, network rewiring, causal mediation.** Yedid, Ofria & Lenski 2008
https://doi.org/10.1111/j.1420-9101.2008.01564.x · Yedid et al. 2009
https://doi.org/10.1086/597228 · Blount, Lenski & Losos 2018
https://doi.org/10.1126/science.aam5979 · Fortuna et al. 2016
https://www.nature.com/articles/ncomms12462 · Wilkins-Reeves et al. 2026
https://raw.githubusercontent.com/mlresearch/v337/main/assets/wilkins-reeves26a/wilkins-reeves26a.pdf.

---

## 9. Non-claims (repeated from the per-test prior-art notes)

* A passing fixture, smoke, or injected positive is not a result.
* Absence of a search hit is not proof of uniqueness.
* Item 3 makes no novelty claim; item 2's result is a negative; item 5's contrast is blocked.
* Nothing here licenses `red_queen_proved`, `biological_red_queen_proved`, `arms_race_proved`, or any
  ClaimGate ceiling raise.

---

## 10. Searches not completed (so they can be redone)

1. **OpenAlex full-text search was rate-limited (HTTP 429) for the entire session**, including with a
   `mailto` polite-pool parameter. Only two early calls succeeded. Redo — with a free API key or
   off-peak — the four full-text queries: (a) `"twofold cost of sex"` AND energy/ATP/ledger;
   (b) estimand mismatch AND re-routing AND simulation; (c) heritable-route cut AND matched contact
   cost; (d) function recovery AND network rewiring AND causal mediation.
2. **`web_search` is broken**, so Google Scholar / Scopus / Web of Science coverage is missing
   entirely. All negatives above are "no indexed-API hit", not proof of absence.
3. **No second in-directory literature report exists** under
   `docs/claimgate/host_parasite_port_20260924/`: only `TWO_FOLD_COST_LITERATURE_AND_DESIGN_20260927.md`
   matches the TWO_FOLD_COST/20260927 tokens. The earlier audits live at the workspace root.
4. **Full texts were not read** for the most load-bearing negatives: Acosta & Zaman 2022 (item 4's
   closest digital prior art), Ezard et al. 2011, Misevic et al. 2006/2010, Otto & Nuismer 2004.
   Verification is record-and-abstract level. Paywalled full texts were inaccessible.
5. **The exhaustive "intervened order-permutation designs" check remains unrun** (flagged in
   `order-effect-literature-verdict.md`), which keeps the C3/order-effect negative the weakest of the
   component audits.
6. **`phase_results.json` could not be located** anywhere in the workspace; the item-2 narrowing in
   `TESTS_DONE_STATUS_2026-09-29.md` has no matching artifact.
