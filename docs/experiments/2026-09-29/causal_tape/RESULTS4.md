# CausalTape — round-2 verification addendum

## #2 re-run with the pairing defect fixed

The red-team round found two defects in `sex_arms.py` that weakened the paired
contrast: host mutation and parasite mutation shared one RNG stream (so the host
mutation sequence diverged between parasite-on and parasite-off arms), and the
parasite was scored against a census taken before mortality. Both are fixed
(separate `host` / `parasite` forks; census recomputed after mortality), the
instrument re-validated, and the whole factorial re-run. Previous output kept as
`results/sex_arms_results_prev.json`.

| gate | before fix | after fix |
|---|---|---|
| ledger identity | 1.5e-10 | 1.2e-10 |
| injected leak 1e-3 detected | yes (17.1) | yes (17.1) |
| positive control (costless + parasite) | 0.472 | **0.478** |
| negative control (cost x2, no parasite) | 8.6e-5 | 8.6e-5 |
| P4 rescue at cost x2 | refused | **refused** |
| P5 rescue at cost x2 + delta 0.5 | refused | **refused** |

Cost sweep unchanged: cost 1.0 -> 0.478, cost 1.5 -> 0.0004, cost 3.0 -> 0.000
so **c\* in (1.0, 1.5]** and the classical 2.0 sits above it. The rescue sweep over
four parameter regimes (infection cost, host mutation rate, matching tolerance,
parasite pool) confirms `any_regime_with_costless_sex_persisting = true` while
**`any_regime_with_costly_sex_persisting = false`** — no setting tried rescues sex
while the two-fold cost is charged. A non-evolving parasite leaves infection at
3% and changes nothing, so coevolution rather than parasite presence is required.

## #3 required diagnostics (`rjcj_diag.py`)

The red-team round required three additions before the share could be claimed.
All three now exist:

| cell | differential infection risk V_diff | permutation null V_null | effective genotypes | infectable occupancy |
|---|---|---|---|---|
| b0_s0 (no parasite) | 0.0000 | 0.0000 | 25.1 | 0.000 |
| b1_s0 (parasite) | **0.1324** | 0.0177 | 24.8 | 0.832 |
| b1_s1 (parasite + shock) | 0.1313 | 0.0172 | 24.1 | 0.833 |
| tax_s0 (uniform 74% tax) | 0.0264 | 0.0264 | 27.8 | 0.000 |

* **`biotic_is_not_uniform_tax = true`**: infection risk varies across genotypes at
  7.5x the label-permutation null in the parasite cells, and the genotype-blind
  uniform-tax cell shows *exactly* the null (0.0264 vs 0.0264). The decisive
  control the reviewer demanded is satisfied, so the biotic factor is
  frequency-dependent selection, not a uniform energy tax.
* Effective genotype number ~25 (genotype space 64), so the metric is not
  saturated and has dynamic range.
* eta^2 decomposition: biotic exceeds abiotic at every window.
* Power: interaction sd = 0.0175, **MDE at n = 100 = 0.00049**; the observed
  interaction at w = 20 is -0.00106, about 2x the MDE.

## Status

All three innovations have results produced by instruments whose gates pass, with
the two critique rounds per design applied and the failures of the *hypotheses*
(P4/P5, and the "clean order-effect threshold" reading) reported as negatives.
No threshold was softened, no positive fabricated, nothing written to GitHub.
