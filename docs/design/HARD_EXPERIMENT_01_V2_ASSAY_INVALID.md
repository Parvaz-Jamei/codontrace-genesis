# HARD_EXPERIMENT_01 v2 as `assay_invalid`

Wave 1b on `main` (`e58d983`, identity `0.3.0b4.dev0`) committed
[`../hard_experiment_01/results_v2.json`](../hard_experiment_01/results_v2.json).

v2 is a **runtime observation labeled `assay_invalid`**, not a scientific
null. All four arms produced bitwise-identical `terminal_mean_fitness`
`0.164375`. Adoptions were `169 / 169 / 0 / 169` (only `capsules_off`
differs). The capsule channel fired (treatment adoptions 169, extinction
0, `assay_failed=false`), but the intervention did not change the
fitness estimand — **manipulation not realized**. Paired contrasts stay
at dz = 0, CI `[0.0, 0.0]`, Holm p = 1.0 because the outcomes are
identical, not because a realized manipulation was shown to have no
effect.

ClaimGate on main granted `runtime_observation` (public level 1).
`intervention_supported` was not requested as a pass. The Wave 2
CodonTrace adapter wraps that same artifact; the auditor reproduces the
same public ceiling and emits
`assay_invalid_manipulation_not_realized`. That floor is not mechanism
support, collective intelligence, Tokyo Type 1, or Avida replacement.

See [`CLAIMGATE_STANDALONE.md`](../CLAIMGATE_STANDALONE.md) and
[`../HARD_EXPERIMENT_01.md`](../HARD_EXPERIMENT_01.md).
