# E6 Morris screening design (exploratory)

Product: **CodonTrace Genesis**. Overlay: HE01 / SCHEMA v5 / Amendment 03.
Harness: `codontrace.genesis.hard_experiment_01_morris`.
Sibling ODD: [`../HARD_EXPERIMENT_01_ODD.md`](../HARD_EXPERIMENT_01_ODD.md).
Tier: `exploratory_only`. Claim ceiling: `runtime_observation`.
Morris μ\* does **not** enter ClaimGate, Holm, BCa, or Amd text.

This is Grimm 2020 Supplement S7 (simulation experiments), not a
confirmatory prereg amendment.

---

## Method

Elementary effects (Morris 1991) on a \(p=4\) level grid, with Campolongo
et al. (2007) \(\mu^*\) as the primary rank, plus \(\mu\) and \(\sigma\):

\[
EE_i = \frac{Y(x_1,\ldots,x_i+\Delta,\ldots,x_k) - Y(x)}{\Delta}
\qquad
\Delta = \frac{p}{2(p-1)} = \frac{2}{3}
\]

Along \(r\) trajectories of length \(k+1\):

| Statistic | Formula | Reading |
|---|---|---|
| \(\mu_i\) | mean of \(EE_i\) | sign-cancelling mean effect |
| \(\mu^*_i\) | mean of \(\|EE_i\|\) | **primary screening rank** |
| \(\sigma_i\) | sample sd of \(EE_i\) | nonlinearity / interactions |

Sample size: \(N = r(k+1)\) model evaluations (times \(n_{\mathrm{seed}}\)
if \(Y\) is averaged over seeds). This is a qualitative screen, not Sobol
\(S_i/S_{Ti}\) (Saltelli et al. 2008). Ojha et al. (2022) is the nearest
EA-hyperparameter neighbor; E6 screens overlay ecology knobs, not CMA-ES.

Trajectories are generated with `RNGManager(design_seed,
namespace="hard_experiment_01/morris")` — a named stream **separate** from
`hard_experiment_01/roles`. Same `design_seed` replays the design.

---

## Primary factor set (\(k=4\))

Amd 03 locked roles, every-cell food, and `respawn_draws_per_tick =
max(1, pop)`. Those stay frozen. WAVE_1D_SCIENCE_BRIEF_v2 §6 candidates
are reclassified here.

| Factor | Levels (CALIBRATION-centred) | Overlay default | Screenable? |
|---|---|---|---|
| `read_radius` | {1, 3, 6, 10} | 6 | **Yes** |
| `min_source_fitness` | {0.0, 1.0, 1.5, 3.0} | 1.5 (treatment) | **Yes** (treatment knob; not the Amd 01 dose analysis) |
| `basal_runtime_atp_cost` | {0.2, 0.4, 0.6, 0.8} | 0.4 | **Yes** |
| `resource_amount` | {1.0, 2.0, 3.0, 4.0} | 2.0 | **Yes** |

**Explicitly frozen (not in primary \(k=4\)):**

| Factor | Amd 03 value | Why frozen |
|---|---|---|
| Role layout | `seed_permuted_v3_multiset` | Variance source for HE01; not a continuous screen factor |
| Food coverage | every-cell (`1.0`) | Amd 02 sparse food broke the oracle |
| `respawn_draws_per_tick` | `max(1, population_size)` | Coupled to food ecology; Amd 02 FAIL |
| Initial runtime ATP | 48.0 | Coupled to basal × ticks |
| Analysis seeds | 11–40 | Confirmatory; forbidden here |
| Pilot seeds | 1000–1009 | Calibration only; forbidden here |

Optional later block (coverage + draws) must be a **separate**
`exploratory_only` artifact, after this \(k=4\) screen, and must not feed
ClaimGate.

Dose H1 on confirmatory HE01 still uses {0.0, 1.5, 4.0}. Morris levels
around the treatment threshold must not rewrite that prereg.

---

## Outcome and seeds

| Item | Value |
|---|---|
| \(Y\) | `receiver_mean_terminal_runtime_atp` |
| Arm | `source_bias_on` only |
| Seeds | held-out exploratory **2000–2009** |
| Forbidden seeds | **11–40** (analysis), **1000–1009** (pilot) |
| Optional second \(Y\) | paired \(\Delta(\mathrm{on}-\mathrm{off})\) — not implemented in the primary harness |

Seeing a high μ\* on `resource_amount` does **not** authorize changing
food amount in a new Amd and re-running 11–40 (forking paths / Nosek).

---

## Budget and cost

| Parameter | Default design | Smoke executable (CI) |
|---|---|---|
| \(k\) | 4 | 4 |
| \(r\) | 10 | 10 (tests may use \(r=2\)) |
| \(p\) | 4 | 4 |
| \(N\) | \(10 \times 5 = 50\) | 50 |
| Scale | research 40 ticks × 16 pop | **8 ticks × 8 pop** |
| \(n_{\mathrm{seed}}\) | 10 (2000–2009) | 1 (2000) |
| Model runs | \(50 \times 10 = 500\) | \(50 \times 1 = 50\) |

**Research-scale cost (order-of-magnitude).** Wave 1d′ confirmatory
research (30 seeds × 5 arms × 40 × 16, plus dose + replay) was ~1500 s
on the generating runner. One treatment-arm 40 × 16 eval is a small
fraction of that (~1–2 s). A full E6 research screen at
\(r=10,\,n_{\mathrm{seed}}=10\) is therefore on the order of
**10–20 minutes**, not a new campaign. Smoke 8 × 8 is the CI default
so this harness does not inflate pull-request time.

Default `run_morris_e6()` is **smoke**, one held-out seed, \(r=10\).
Pass `scale="research"` and `seeds=EXPLORATORY_SEEDS` only for a
deliberate exploratory compute.

---

## Report

A result payload (`MorrisE6Result.to_dict` /
`docs/hard_experiment_01/morris_e6_smoke.json`) includes:

- factor levels, \(\Delta\), \(r\), \(k\), \(N\)
- seeds and `design_seed`
- table of \(\mu^*,\mu,\sigma\)
- frozen Amd 03 fields
- `tier=exploratory_only`, `claim_ceiling=runtime_observation`
- `claim_gate_unchanged=true`

No \(d_z\), no Holm family, no BCa interval from Morris trajectories.

---

## References

1. Morris (1991) https://doi.org/10.1080/00401706.1991.10484804
2. Campolongo, Cariboni & Saltelli (2007) https://doi.org/10.1016/j.envsoft.2006.10.004
3. Saltelli et al. (2008) *Global Sensitivity Analysis: The Primer.*
4. Campolongo, Saltelli & Cariboni (2011) https://doi.org/10.1016/j.cpc.2010.12.039
5. Gelman & Loken (2013); Nosek et al. (2018)
6. Ojha, Timmis & Nicosia (2022) arXiv:2207.04820
