# CausalTape — experiment record (question, design, protocol, raw data, results)

**Record date:** 2026-09-29 (archive); **runs dated** 2026-09-27.
**Repo under test:** `codontrace-genesis` @ `5a161081`, working tree clean, no git writes, nothing pushed.
**Runtime:** Python 3.14.4 · NumPy 2.4.4 · 4 worker processes per heavy run.
**All paths are relative to `docs/experiments/2026-09-29/causal_tape/`.**
**Raw-data manifest:** `evidence_files.sha256` (one `sha256  size  path` line per archived file).
**Run-time artifact hashes** (SHA-256 prefixes, `RESULTS.md` line 5): harness `D68BC01A8EC41212`,
experiment `B5FEA4E0CDC5C210`, gates `FBAC6DA845BEFB10`.

---

## 1. Question, hypothesis and references

In a deterministic mutation-accumulation process, how wrong are the two estimators people actually use
for the causal effect of a single mutation — naive conditioning and regression adjustment — when the
true interventional contrast is computable exactly by replay?

The tape is deterministic and the counterfactual arm advances the **same** RNG stream as the factual
arm, so `Y(0)` is available for every lineage and the contrast needs no identification assumptions.
Seed is the only randomisation unit; the focal mutation set and every threshold were fixed in
`PREREG.md` before the confirmatory run. This is a benchmark on a specified substrate, not a
biological result. Six dated references bound the claim:

1. Díaz-Uriarte, Ríos-Arroyo & Johnston (2026), arXiv:2606.12597 — already formalises `do` and conditional interventions on evolutionary accumulation models and shows conditioning on mutation absence gives incorrect predictions; **this study does not claim that idea.**
2. Heckman (1979), *Econometrica* 47(1):153–161 — the naive-versus-ATT selection-bias decomposition is textbook; Marshall & Galea (2015), *Am. J. Epidemiol.* 181(2):92–99 — in simulation, exchangeability is free by construction, so identifiability rests on ergodicity and correct specification.
3. Wahl & Agashe (2022), *Evolution* 76 — selection bias in mutation-accumulation effect estimation, quantified and corrected.
4. Klein, Abeysuriya, Stuart & Kerr (2024), arXiv:2409.02086 — noise-free paired counterfactuals by aligning random-number realisations.
5. Buffalo, Pearson & Klein (2026), arXiv:2603.11084 — stateful-PRNG draw indexing makes paired counterfactuals causally incoherent; the published account of the failure mode the stream-preserving `do` here avoids.
6. Bajić, Vila, Blount & Sánchez (2018), *PNAS* 115(44):11286–11291 — noncommutative epistasis δ and the `FMAX` normalisation used by the order arm (`RESULTS2.md` §B).

Dated URLs are collected in `NOVELTY_VERDICT.md` in this directory.

## 2. Design and the causal object

**Substrate.** An 18-bit genotype (6 codons × 3 bits) with fitness `F(x) = Σ w_i x_i + ε · Σ_{i<j} J_ij x_i x_j`, `w_i ∈ [0.5, 1.5]`, symmetric `J_ij ∈ {−1, +1}`, diagonal zero, drawn once per coupling draw from `RNGManager(seed=ENV_SEED).fork("env")` (`PREREG.md` §2). The map is exactly quadratic, which is what makes the one-bit contrast exact.

**Intervention.** `do(m := suppressed)` means: when the drawn proposal *is* `m`, it is not applied. The RNG stream is **not rewound and not re-keyed**, so every later draw is identical to the factual arm; bootstrapping a fresh stream was explicitly rejected as the design (`PREREG.md` §2, §7).

**Estimands** (`PREREG.md` §3): `ATT_m` and `ATE_m` by exact paired replay; `naive_m` observational; `adjusted_m` the OLS coefficient on bit `i` over all 18 bits plus intercept; `τ_direct = w_i` analytic; `τ_epi = ATT_m − τ_direct`. The identity `selection_bias_m = naive_m − ATT_m = E[Y(0)|m] − E[Y(0)|¬m]` carries a 1e-12 residual bound.

**The estimand split (the second question).**

```
beta_j − ATT_whole_tape_j = (beta_j − ATT_onebit_j) + (ATT_onebit_j − ATT_whole_tape_j)
                             (i) linear misspecification   (ii) whole-tape re-routing
```

`ATT_whole_j` = mean over exposed seeds of `fitness − counterfactual[:, j]`. `ATT_onebit_j` = mean over
exposed seeds of the fitted **quadratic** model (intercept + 18 main effects + 153 pairwise products)
when locus `bit_of[j]` is set to 1 versus 0 with all other loci held at their observed values. The
quadratic model is exactly correctly specified here — `results/estimand_split.json` →
`reproduction_check.fitted_quadratic_rank` = 172 (full design), `fitted_quadratic_r2_min` =
`fitted_quadratic_r2_max` = 1.0, `fitted_quadratic_max_abs_residual` = 5.808686864838819e-13,
`max_abs_identity_residual` = 1.1102230246251565e-16 — so component (ii) is **pure re-routing**, not
further misspecification. Implemented in `estimand_split.py`; independently re-derived by
`verify_estimand_split.py`.

## 3. Instrument

* **Gate A — bit-identical replay.** A recorded seed reproduces events, bits, fitness and the RNG digest exactly (`results/harness_gates.json` → `gate_a`, seeds 3/11/29, `identical: true`).
* **Gate B — intervention minimality.** Suppressing a drawn event leaves the stream digest unchanged, moves exactly one bit, and matches the closed-form delta to 1e-12, also with selection active (`gate_b_neutral`, `gate_b_selection`; natural fitness 16.963678523352797 versus intervened 16.34311039755934).
* **Gate C — fast-path equivalence.** The neutral fast proposal path reproduces the engine mutation operator exactly over 12 tapes (`events_equal`, `bits_equal`, `fitness_equal`, `rng_equal` true at ε = 0.0 and 0.4).
* **Gate D — seed sensitivity.** Six of six perturbed seeds give unique digests (`gate_d`).
* **RNG manager and digest contract.** Streams come from `codontrace.rng.RNGManager` with named forks (`"env"`, `"tape"`), so a re-keyed stream is detectable. `telemetry.py` defines the manifest contract: `config_digest(config)` = SHA-256 of the canonical JSON config (lines 43–45), a `runs/<run_key>.json` manifest per run key (65–79), and a `done.jsonl` line carrying `run_key`, `status`, `seconds`, `config_digest` (117–129). Each result JSON also carries its sweep header (`experiment`, `eps_grid`, `depths`, `env_seeds`, `seeds_per_config`, `workers`, `elapsed_seconds`).
* **Provenance caveat.** The 57 archived files are the result JSONs, the `.npz` arrays, the scripts and the reports. The per-run `runs/<run_key>.json` manifests and `done.jsonl` from `telemetry.py` are **not** among them, so the archive preserves the digest *contract* and the run-time artifact hashes but not the per-run `config_digest` values.

## 4. Protocol and provenance

* **Pre-registration:** `PREREG.md` (and `PREREG_FA.md`), written before any confirmatory number was
  inspected; rules R1–R8 and the honest-FAIL path are in §5–§6.
* **Design extension:** `SCALE_DESIGN.md` (latency and volume budget, run-key layout, resume
  protocol, per-test telemetry policy).
* **Code:** experiment scripts `heavy1.py`, `heavy2.py`, `scale1.py`, `order_arm.py`, `replicate.py`,
  `estimand_split.py`; shared `harness.py`, `telemetry.py`, `workers.py`; verifier
  `verify_estimand_split.py`; smoke tests `smoke_api.py`, `smoke_benchmark.py`, `smoke_workers.py`,
  `smoke_telemetry.py`.
* **Seeds.** Confirmatory replay seeds are archived per configuration under the `.npz` key `seeds`
  (shape `(3000,)`). Gate-D perturbation seeds: 3/11/29. Order-arm order seeds: `[3000, 3119, 120]`
  (`results/order_results.json`). Coupling draws (`ENV_SEED`): 20260927, 20260928, 20260929. Grids are
  in each sweep header (§5).
* **Report revisions:** `RESULTS.md`, `RESULTS2.md`, `RESULTS3.md`, `RESULTS4.md`, `RESULTS_FA.md`,
  plus the two critique rounds `BRAINSTORM_R3_ROUND1.md` and `REDTEAM_R3_ROUND2.md`.

## 5. What ran, with n and wall time

| run | n | grid | wall | evidence |
|---|---|---|---|---|
| `heavy1` (estimator benchmark, depth sweep) | 1500 seeds/config × **81 configs = 121,500 paired-seed runs** (derived from the header: 9 ε × 3 depths × 3 draws, each × 1500) | ε {0, 0.02, 0.05, 0.1, 0.2, 0.3, 0.4, 0.6, 0.8} × depth {20, 40, 80} × 3 `ENV_SEED` | **9867.7 s** (≈164.5 min) | `results/heavy1_results.json` |
| `heavy2` (per-seed datasets for the split) | 3000 seeds/config × 18 configs (derived: 6 ε × 3 draws × depth 40) | ε {0.0, 0.05, 0.1, 0.2, 0.4, 0.8}, depth 40 | **4074.3 s** (≈67.9 min) | `results/heavy2_results.json`; the 18 `results/e2026*_eps*_G40.npz` |
| `estimand_split` | 18 configs × 16 focal mutations; **`fits_used`: 1500**, **`rank_deficient_resamples_redrawn`: 6** | as `heavy2` | **151.05 s** | `results/estimand_split.json` |
| order arm | 120 seeds/ε × 4 permutations; gate F: 40 seeds × 4 = 160 schedules; gate G: 20 seeds | ε {0.0 … 0.8}, depth 40 | — | `results/order_results.json`; `RESULTS2.md` §B |
| environment replication | depth-40 grid on a second coupling draw | ε {0.0 … 0.8}, depth 40 | — | `results/replication_results.json`; `RESULTS2.md` §C |
| `scale1` (round-2 scaled benchmark) | 600 paired seeds, 2 environments, 3 depths | ε {0 … 0.8} | **1810.6 s** | `results/scale1_results.json`; `RESULTS3.md` §1 |
| two-fold cost of sex | 100 paired seeds/arm, 400 generations | 11 arms + 8-arm sweep + 4-cell factorial | **1706.1 s** (previous run: 2344.9 s) | `results/sex_arms_results.json`; `results/sex_arms_results_prev.json` |
| biotic vs abiotic turnover | 100 paired seeds/cell, 400 generations | 4 factorial + 2 tax cells | **414.0 s** | `results/rjcj_results.json` |
| turnover diagnostics | — | differential infection risk, permutation null | **1065.9 s** | `results/rjcj_diag_results.json` |

Two pre-registered rules failed as literally worded and are recorded as failures, not relaxed: R3's predicted sign was wrong (naive conditioning *under*-estimates) and R4 failed only at a floating-point tolerance (largest value 1.565e-15 versus a literal `== 0`), both in `RESULTS.md` §4.2. The order-effect threshold did not replicate across coupling draws — first non-zero at ε = 0.2 in draw A and ε = 0.05 in draw B (`replication_verdict.order_threshold_agrees: false` in `results/replication_results.json`).

## 6. Raw data

Full per-file hashes and sizes are in `evidence_files.sha256`. The source arrays are the **18 `.npz`
files** under `results/` (3 coupling draws × 6 ε levels at depth 40). Representative rows from the
manifest:

| file | sha256 (from `evidence_files.sha256`) |
|---|---|
| `results/e20260927_eps0.8_G40.npz` | `a8f38d740990a70c4c2ed249da2641ad36e0feb45fc8200eafe9aeddfb394251` |
| `results/e20260928_eps0.8_G40.npz` | `40abccd580a41fe57e9d9683556eab696d2524908609debb1e99dd8c4af1bcab` |
| `results/e20260929_eps0.8_G40.npz` | `87af9dd6d54b305ef2eed064e22bd65e857a58806330c4c1cbc16fcfc09fbedf` |
| `results/estimand_split.json` | `c45aabf90792478b9e5fa92e797e93a93f5954af53dbf2f0a6fff220293bf016` |
| `results/heavy1_results.json` | `4cdab5777f629ca51c47e10f4c219dfbb696bd844630319319d7ec6f1669b16c` |
| `results/heavy2_results.json` | `b091601d54337bc9aa2fa365839bb958dc7a81be0e2b0a037913068fff743c4a` |
| `results/order_results.json` | `4cb2793a46339aa4ef66d63194bf795231a8cad12c532f514360f639b69c2dc8` |
| `results/replication_results.json` | `bff2368ffcf6fd225a5ad5ab3189c37c494318596f6caa3513299351baf70a30` |
| `results/harness_gates.json` | `b35c1798ea5dbca007b2e34a566774ce2c9016836d8aad6d9a68b505fb44acec` |
| `results/scale1_results.json` | `9445a41d2378a19b2ae91aaceed10f9f0fa3d1b55c6c5775f47b5314f46e2092` |
| `results/benchmark_results.json` | `7ebeaf87a066bf2f1132b3b227da91865306e7962be7de32d27ac3efc1cc651b` |
| `results/sex_arms_results.json` | `98541f72968d1f46861c1d3901be8e065d0e5f2a35b750aa82688e38b20770f7` |
| `results/rjcj_results.json` | `8d1eccc6b211556ad3724b9ce0854e6fa90cd59da66b8a0db027174adebb1dc0` |
| `results/rjcj_diag_results.json` | `c424c79b7559583ac43c6f7d0b3fd4a844567ebdb0665be706d8a107f8a2a9b3` |

**How to load an array.** Each `.npz` holds exactly seven keys (verified by loading
`results/e20260929_eps0.8_G40.npz` with NumPy):

| key | shape | dtype | meaning |
|---|---|---|---|
| `fitness` | `(3000,)` | float64 | final fitness of each paired seed |
| `bits` | `(3000, 18)` | int8 | final 18-locus genotype |
| `counterfactual` | `(3000, 16)` | float64 | `Y(0)` for each of the 16 focal mutations |
| `present` | `(3000, 16)` | int8 | exposure indicator `1[m occurred]` |
| `mutations` | `(16,)` | `<U6` | focal mutation ids of the form `"<bit>:<from>><to>"` |
| `seeds` | `(3000,)` | int64 | the paired replay seeds |
| `threshold` | `(1,)` | float64 | the innovation threshold fixed in `PREREG.md` §4 |

`ATT_whole_tape_j = mean((fitness − counterfactual[:, j])[present[:, j] == 1])`, and the bit index of
focal mutation `j` is `int(mutations[j].split(":")[0])`.

**Archived analysis scripts:** `estimand_split.py`, `verify_estimand_split.py`, `summarize.py`,
`run_benchmark.py`, `harness.py`, `telemetry.py`, `workers.py`.

**Path defect to note before replaying.** `estimand_split.py` (line 58) and `verify_estimand_split.py`
(line 53) load from `HERE / "datasets"`, but the archive stores the arrays in `results/`; there is no
`datasets/` directory here and no `DATASETS` override, so §10 stages them explicitly. This is an
archive-path mismatch, not a data defect — the arrays are present and hash-matched.

## 7. Analysis method

* **Rank admissibility.** The quadratic design is solved by SVD with the published rank tolerance
  `rank_tol = 1e-8` (`estimand_split.py`: `solve_via_svd` at line 125, `fit_checked` default at line
  165). A resample that fails the tolerance is rejected and redrawn; `estimand_split.json` records
  `rank_deficient_resamples_redrawn: 6` out of `fits_used: 1500`.
* **Bootstrap.** 500 seed resamples at fixed RNG seed **20261004**, resampling within each coupling
  draw (`BOOTSTRAP_DRAWS = 500`, `BOOTSTRAP_SEED = 20261004`; `estimand_split.json` → `bootstrap`).
  The bootstrap is deterministic for a fixed seed (`verify_estimand_split.py` lines 131–140).
* **Estimators reported.** Pooled **ratio of medians** (`med|ii| / med|total|`), pooled **ratio of
  means** (`Σ|ii| / Σ|total|`), the **mean of per-draw shares**, and two auxiliary accountings in the
  same JSON: the **gross** ratio (`Σ(ii)/Σ(i+ii)`) and the **carried-only** share. The record's
  headline uses the ratio-of-medians estimator and every quotation names it.
* **Independent recomputation.** `verify_estimand_split.py` recomputes β, `ATT_whole`, `ATT_onebit`,
  components (i) and (ii) and the total gap through a separate path and asserts the per-mutation
  identity `total = (i) + (ii)` below 1e-12 and agreement with the published `specification_bias`
  below 1e-9.
* **Rank-tolerance sensitivity is part of the result.** Under a Cholesky rank test the ratio-of-medians
  interval becomes `[56.02, 73.25]`; under the published 1e-8 SVD test it is `[55.78, 73.33]`.
  Switching only the rank criterion restores the published value, because a rejection consumes an
  extra RNG draw and shifts the whole resample stream.

## 8. Results

**Instrument and estimator comparison.** All four gates pass (`results/harness_gates.json` → `all_passed: true`). Specification bias is machine-zero at ε = 0 (maximum 1.13e-14, `RESULTS.md` §3 rule R2) and grows monotonically with ε (median `|spec bias|` 1.3e-15 → 0.7925, `results/replication_results.json`). Naive conditioning is biased even with no epistasis: median selection bias −0.246 at ε = 0 against an exact effect of 1.165. The exact per-lineage effect has zero spread at ε = 0 and a large spread at ε = 0.8 (`sd(ATT)` 1.2e-15 → 1.810); both from `RESULTS.md` §4.1.

**The estimand split at ε = 0.8.** Every figure is quoted with its estimator.

| quantity | value | 95 % interval | in-repo source field |
|---|---|---|---|
| **bootstrap median of the pooled ratio of medians — the headline "64.1 %"** | **0.6407308901109312 (64.07 %)** | **[0.5577497815809901, 0.7332976037688598]** = **[55.8 %, 73.3 %]** | `results/estimand_split.json` → `bootstrap_reroute_share_eps_max.pooled_share_of_total_ratio_of_medians`; identical at `verdict.fraction_of_published_bias_that_is_rerouting` |
| **mean over draws of the per-draw ratio of medians** ("mean per-draw", 63.75 %) | **0.6374615629229631 (63.75 %)** | — | `verdict.reroute_share_by_eps_ratio_of_medians.eps0.8`; also `by_eps[]` for ε = 0.8 |
| **bootstrap median of the pooled ratio of means** | **0.6459426356173571 (64.59 %)** | **[0.5986521324031486, 0.6922986345929746]** = **[59.9 %, 69.2 %]** | `bootstrap_reroute_share_eps_max.pooled_share_of_total_ratio_of_means` |
| mean of per-draw shares | 0.6369209764800238 | [0.5597903659743666, 0.7286525072829015] | `pooled_...`/`mean_of_per_draw_shares` |
| gross ratio (alternative accounting) | 0.2754404395432509 | [0.25189146395841566, 0.2986494637786377] | `pooled_share_of_gross_ratio_of_medians` |
| carried-only share | 0.7200703609739275 | [0.6424439731749736, 0.818826401699775] | `pooled_carried_share_of_total_ratio_of_medians` |
| component (i), median absolute misspecification | 1.141015560262799 | — | `verdict.eps_max_median_abs_component_i_misspec` |
| component (ii), median absolute re-routing | 0.403189359602709 | — | `verdict.eps_max_median_abs_component_ii_reroute` |
| total gap, median absolute | 0.6597439481369137 | — | `verdict.eps_max_median_abs_total_gap` |
| share that is misspecification | 0.3592691098890688 | — | `verdict.fraction_that_is_misspecification` |
| fit health | rank **172**, R² = **1.0**, max residual **5.808686864838819e-13**, identity residual **1.1102230246251565e-16** | — | `reproduction_check` |

**Two numbers are recorded but are not fields of the archived JSON.** The **raw pooled point
estimates** — ratio of medians **0.6297458897128516 (62.97 %)** and ratio of means
**0.6481847098619269 (64.82 %)** — and the **Cholesky-rank-test interval [56.02, 73.25]** come from the
external verification record (`docs/experiments/2026-09-29/verification/CLAIMS.json` claim C, `docs/experiments/2026-09-29/verification/claim-c.md`)
and were carried in the pre-import `README.md` (sha256
`9d00dbeef2fa794d94fb52c806f641ce25d97a4ec6c53135ae5d67ffb4b89102` in `evidence_files.sha256`). They are
recomputable from the archived arrays with §6–§7, but **not** re-derivable from
`results/estimand_split.json` alone. The pairs must not be mixed: the ratio-of-means **point estimate**
is 64.82 %, while the ratio-of-means **bootstrap** is 64.59 % with interval [59.9 %, 69.2 %].

**The only admissible way to state the headline.** At ε = 0.8, **64.1 % is the bootstrap median of the pooled ratio of medians**, with a 95 % interval of **[55.8 %, 73.3 %]** belonging to *that* estimator. The raw pooled ratio of medians is 62.97 %; the mean over draws of the per-draw ratio of medians is 63.75 %; the pooled ratio of means is 64.59 % by bootstrap (64.82 % as a point estimate) with the narrower interval [59.9 %, 69.2 %]. Quoting "64.1 %" without naming the estimator, or pairing the ratio-of-means point estimate with the [55.8, 73.3] interval, is an estimator mismatch and appears nowhere in this record.

**Per-coupling-draw heterogeneity (ratio-of-medians bootstrap medians).** 0.3253440556643041
(`e20260927`), 0.8340790949817213 (`e20260928`), 0.7456257995056479 (`e20260929`)
(`verdict.reroute_share_by_coupling_draw`). The share is strongly draw-dependent.

**Share by ε (ratio of medians).** 0.05 → 0.008766410253005574; 0.1 → 0.022385084077474495;
0.2 → 0.5980421821723528; 0.4 → 0.4410563923746185; 0.8 → 0.6374615629229631; ε = 0 undefined (both
components numerically zero) (`verdict.reroute_share_by_eps_ratio_of_medians`). **Re-routing is
negligible below ε = 0.2 and dominant above it.** Conditional on the landscape the two components are
only weakly correlated — within-configuration median signed Pearson 0.031, median within-ε |component|
Pearson 0.188 (`verdict.separable`) — so they carry distinguishable information.

**Order arm (`RESULTS2.md` §B).** `τ_order` is exactly zero at ε ≤ 0.1 and positive above a
landscape-dependent threshold: median absolute 0.1033 at ε = 0.2, 1.1717 at ε = 0.4, 3.7713 at
ε = 0.8; `|τ|/FMAX` 0.0065 / 0.0630 / 0.1464 against the published 0.01 and 0.1 floors
(`results/order_results.json`). The measured unmatched-arm inflation was only 1.06–1.57×, so the large
inflation reported by the red team did **not** reproduce here and is recorded as a measured null.

**Engine-native port.** Reported as uninformative, not as a negative: 100 seeds returned identical
outcomes (mean 19.20, sd 0.0000), so no mutation strictly improved the outcome and no counterfactual
contrast exists (`RESULTS.md` §6). A later fix reads the outcome from the trace (`RESULTS2.md` §A).

## 9. Interpretation and limits

* **Method novelty is narrow.** The exact, noise-free `do` on the mutation draw — suppressing the event while consuming the draw, so the stream digest is unchanged — is the defensible claim. The generic SCM framing is prior art (Díaz-Uriarte et al. 2026), the decomposition is textbook (Heckman 1979), and mutation-effect selection bias is published (Wahl & Agashe 2022).
* **The headline number is estimator-sensitive.** Defensible estimators span 62.97 %–64.82 %, the per-draw quotient spans 0.33–0.83 across coupling draws, and the interval moves between [56.02, 73.25] and [55.78, 73.33] with the rank criterion alone.
* **No discovery claim.** The synthetic fitness map is an instrument calibration, not an organism; nothing here transfers to mutation or selection in nature (`RESULTS.md` §7).
* **Both flags false.** `hypothesis_supported = false`, `red_queen_proved = false`; no ClaimGate refusal was relaxed and no ceiling was raised.
* **Tier limit.** The pre-registered "clean order-effect threshold" reading is refused: the threshold location is landscape-dependent while the qualitative pattern replicates (`RESULTS2.md` §C).
* **Archive limits.** Per-run `config_digest` values and `done.jsonl` are not archived (§3); the arrays sit under `results/` while the scripts load from `datasets/` (§6); the two-fold-cost bracket quoted elsewhere in this campaign now comes from the separate `sex_cost/` record, not from `results/sex_arms_results.json` alone.

## 10. Replay commands (in-repo paths only)

Run from the repository root. Stage the arrays where the archived estimators look for them (one-time):

```bash
mkdir -p docs/experiments/2026-09-29/causal_tape/datasets
cp docs/experiments/2026-09-29/causal_tape/results/e2026*_eps*_G40.npz \
   docs/experiments/2026-09-29/causal_tape/datasets/
sha256sum -c docs/experiments/2026-09-29/causal_tape/evidence_files.sha256
PYTHONPATH=src python docs/experiments/2026-09-29/causal_tape/estimand_split.py        # split + bootstrap
PYTHONPATH=src python docs/experiments/2026-09-29/causal_tape/validate_harness.py      # gates A-D
PYTHONPATH=src python docs/experiments/2026-09-29/causal_tape/heavy1.py               # ~2.7 h at 4 workers
PYTHONPATH=src python docs/experiments/2026-09-29/causal_tape/heavy2.py               # ~1.1 h at 4 workers
PYTHONPATH=src python docs/experiments/2026-09-29/causal_tape/order_arm.py            # order arm
PYTHONPATH=src python docs/experiments/2026-09-29/causal_tape/replicate.py            # env replication
cd docs/experiments/2026-09-29/causal_tape && PYTHONPATH=<repo>/src python verify_estimand_split.py
```

## 11. Files in this record

57 archived files. The scripts, both critique rounds (`BRAINSTORM_R3_ROUND1.md`,
`REDTEAM_R3_ROUND2.md`), the Persian translations (`PREREG_FA.md`, `RESULTS_FA.md`) and
`NOVELTY_VERDICT.md` sit alongside the data, so the critique rounds that preceded the confirmatory run
are part of the record rather than external to it.
