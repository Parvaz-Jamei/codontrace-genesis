# Hard experiment 01 — capsule source-bias and next-generation fitness

One measurement question. Not a new Phase letter. Not intelligence.
Product name: **CodonTrace Genesis**.

**Question.** Does source-fitness-weighted capsule transfer raise last-tick
(next-generation) mean fitness relative to (a) the same capsule channel with
source-fitness gating ablated, (b) capsules off, and (c) the channel on with
content scrambled?

**Preregistration.** [`HARD_EXPERIMENT_01_PREREG.md`](HARD_EXPERIMENT_01_PREREG.md)
is frozen in an earlier commit. Campaign payloads record `prereg_digest`.

**Claim ceiling:** `runtime_observation` unless the treatment assay passes,
the preregistered decision rule holds, **and** ClaimGate allows existing
`intervention_supported`. Smoke (`n=12`) is `exploratory_only` and stays
`runtime_observation`. If the treatment arm has mean adoptions ≈ 0 or mean
extinction ≈ 1, `assay_failed` is recorded and the ceiling stays
`runtime_observation` even when paired CIs are numerically defined.

**Blocked:** `intelligence`, `collective_intelligence`, `agi`,
`tokyo_type1_passed`, `avida_replacement`, and related ClaimGate aliases.

## Causal DAG (Okasha & Otsuka 2020)

Price / covariance is a statistical identity. A causal reading needs an
explicit model:

```
gate → which capsule is adopted → action → ATP → terminal fitness
```

| Arm | Role | Edge intervention |
|---|---|---|
| `source_bias_on` | treatment | no edge cut (`min_source_fitness=2.0`, `FITNESS_WEIGHTED`) |
| `source_bias_off` | mechanism ablation | cuts `e1` (`min_source_fitness=0.0`, `THRESHOLD`) |
| `capsules_off` | channel off | cuts `e1` and `e2` (`enabled=False`) |
| `capsules_shuffled` | negative control | severs informational content of `e2` (`CapsuleShuffleMode.CONTENT`) |

Dose `min_source_fitness ∈ {0, 1, 2, 4}` with `FITNESS_WEIGHTED` modulates
`e1`. Dose `0` is not `source_bias_off`.

## Design

| Item | Choice |
|---|---|
| Product | CodonTrace Genesis |
| Smoke | 12 paired seeds (`11`…`22`), 6 ticks, pop 4, in CI (`exploratory_only`) |
| Research | 30 paired seeds (`11`…`40`), 40 ticks, pop 16 (CLAIMS.md §9 ticks/pop; research-grade n) |
| Substrate | Phase A `life_loop_world` overlay (does **not** change A–E pins) |
| Treatment | `source_bias_on`: capsules on, `min_source_fitness=2.0`, `FITNESS_WEIGHTED` |
| Ablation | `source_bias_off`: capsules on, `min_source_fitness=0.0`, `THRESHOLD` |
| Channel off | `capsules_off`: transfer disabled |
| Negative control | `capsules_shuffled`: channel on, content scrambled |
| Dose | `{0,1,2,4}` × `FITNESS_WEIGHTED`; Spearman + seed-fixed permutation trend |
| Outcome | last-tick `selection_mean_fitness` (missing dropped, never zero-filled) |
| Secondary | births, extinction rate, adoption count |
| Statistics | `paired_effect_size` (dz), `bootstrap_ci_paired` (BCa, 10000), `exact_sign_flip_permutation_p`, Holm on three primary contrasts, `PairedComparisonResult.claim_downgraded` when CI includes 0, `MultipleComparisonAudit(metric_count=3)` |
| Replay | all arms × `seeds[0]` and `seeds[-1]`; snapshot digest identity; campaign refuses a mismatch |
| Library | `codontrace.genesis.hard_experiment_01` |
| Example | `examples/genesis_hard_experiment_01.py` |

`CapsuleAblationPolicy.enable_source_fitness_weighting` is a digest-backed
policy object and is **not** the runtime gate. This experiment uses the
wired `CapsuleTransferConfig` knobs (`min_source_fitness`, adoption policy,
`shuffle_mode`).

## Interventions

| Arm | Role | Knob | Applied value | Cuts |
|---|---|---|---|---|
| `source_bias_on` | treatment | `min_source_fitness` + `adoption_policy` | `2.0` / `FITNESS_WEIGHTED` | none |
| `source_bias_off` | mechanism ablation | same knobs | `0.0` / `THRESHOLD` | `e1` |
| `capsules_off` | channel off | `CapsuleTransferConfig.enabled` | `False` | `e1`, `e2` |
| `capsules_shuffled` | negative control | `shuffle_mode` | `CONTENT` | `e2` content |

See `hard_experiment_01_interventions()`. A null or small effect is valid.

## How to run

```python
from codontrace.genesis.hard_experiment_01 import (
    evaluate_hard_experiment_01_claim,
    run_hard_experiment_01,
)

campaign = run_hard_experiment_01()  # smoke: 12 seeds, 6 ticks, pop 4
# research = run_hard_experiment_01(scale="research")  # 30 / 40 / 16
print(campaign.mean_delta_vs_source_bias_off)
for contrast in campaign.paired_contrasts:
    print(contrast.baseline_arm, contrast.dz, contrast.ci_low, contrast.ci_high, contrast.p_holm)
print(evaluate_hard_experiment_01_claim(campaign).final_claim)
```

```bash
python examples/genesis_hard_experiment_01.py
```

A campaign object will not construct if replay digests fail to match.

## Results (research v1)

Prereg commit `135b2ac` precedes these numbers. Artifact:
[`hard_experiment_01/results_v1.json`](hard_experiment_01/results_v1.json).
Campaign digest
`37f7c447e332d557eb5a3641de01bbdd5c505c99620a361e7aa8c53024300579`.
`prereg_digest`
`cb4643a305a48a17250b4e38af3f423afc0c040b4ffac039c8b0ec1413b4fc40`.
Scale: 30 seeds (`11`…`40`), 40 ticks, population 16.
`StatisticalTestPolicy` tier: `research_grade_benchmark_candidate`.
Wall-clock: 76.0 s on the generating runner (one arm×seed probe 0.34 s).
Replay identity: snapshot digest (full `GenesisRunResult.digest()` is too
expensive at this scale).

This is an **invalid null for the causal question** (assay failure /
population crash), not a true null intervention effect. Last-tick mean
fitness was identically 0 on every arm. Capsule adoptions were 0 — the
source-bias gate never acted because the channel did not transfer.
Populations were extinct at the last tick (`extinction_rate = 1.0`).
Wave 1b documents the root cause below and re-runs confirmatory research
after a survival calibration that does not change the estimand.

### Primary contrasts (Holm, α = 0.05)

| Contrast | n | mean | sd | dz | CI95 | p_holm | claim_downgraded |
|---|---:|---:|---:|---:|---|---:|---|
| `on` vs `off` | 30 | 0.0 | 0.0 | 0.0 | [0.0, 0.0] | 1.0 | yes |
| `on` vs `capsules_off` | 30 | 0.0 | 0.0 | 0.0 | [0.0, 0.0] | 1.0 | yes |
| `on` vs `shuffled` | 30 | 0.0 | 0.0 | 0.0 | [0.0, 0.0] | 1.0 | yes |

`shuffled ≈ capsules_off`: yes (BCa CI [0.0, 0.0] includes 0). Vacuous
here because both arms are identically zero.

### Arm table

| Arm | n | mean | sd | births mean | adoptions mean | extinction |
|---|---:|---:|---:|---:|---:|---:|
| `source_bias_on` | 30 | 0.0 | 0.0 | 2.0 | 0.0 | 1.0 |
| `source_bias_off` | 30 | 0.0 | 0.0 | 2.0 | 0.0 | 1.0 |
| `capsules_off` | 30 | 0.0 | 0.0 | 2.0 | 0.0 | 1.0 |
| `capsules_shuffled` | 30 | 0.0 | 0.0 | 2.0 | 0.0 | 1.0 |

Missing last-tick outcomes: 0 per arm. None zero-filled.

### Dose table (`FITNESS_WEIGHTED`)

| `min_source_fitness` | n | mean |
|---:|---:|---:|
| 0 | 30 | 0.0 |
| 1 | 30 | 0.0 |
| 2 | 30 | 0.0 |
| 4 | 30 | 0.0 |

Spearman ρ is undefined (zero variance). Consecutive means are
non-decreasing (ties). `same_direction_as_h1` is false. Trend supported:
**no**.

### Replay

All four arms × seeds `11` and `40`: **matched**. Campaign constructed.

### ClaimGate ceiling

**`runtime_observation`** (CLAIMS.md public level 1).

Decision-rule failures:
`ci_on_vs_off_includes_0`,
`holm_on_vs_off_not_below_alpha`,
`ci_on_vs_shuffled_includes_0`,
`holm_on_vs_shuffled_not_below_alpha`,
`dose_trend_not_monotonic_same_direction`.
`intervention_supported` was **not** requested. Null finding is valid.

### Limitations / Diagnostics (Wave 1b, 2026-09-12)

v1 is not a valid test of source-fitness-weighted transfer. The DAG
path `gate → which capsule is adopted` never received a capsule.

Instrumented seed `11`, treatment, research scale (40 ticks, pop 16),
**uncalibrated** `life_loop_world` overlay:

| Tick | N | Food cells | Mean ATP | Births | Deaths | Max fitness |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 16 | 1 | 12.97 | 0 | 0 | 3.0 |
| 1 | 18 | 2 | 5.43 | 2 | 0 | 9.0 |
| 4 | 7 | 3 | 5.74 | 0 | 9 | 1.0 |
| 10 | 0 | 3 | — | 0 | 5 | −4.5 |
| 11–39 | 0 | 3 | — | 0 | 0 | — |

Totals: 2 births, 18 starvation deaths, **0** `EMIT_NEXUS` events, **0**
adoptions, **0** source-fitness records. Some agents did reach
fitness ≥ `min_source_fitness` (2.0) on ticks 0–1 (`max_fit` 3.0 / 9.0)
before the crash. Last-tick `selection_mean_fitness` is 0 because the
population is empty, not because a living channel had no effect.

Root causes (Avida / digital-evolution ecology, not Avida-parity):

1. **Energy budget vs COPY_SELF.** Initial ATP 14.0, basal 1.2 / tick,
   `COPY_SELF` codon cost 8.0, eat credit 6.0. Even an eater on food has
   a negative net budget. Mean ATP falls 13 → 5 after the two early
   births; everyone is gone by tick 10.
2. **Resource × population mismatch.** Two food cells, `max_resources=3`,
   respawn 0.4, sixteen organisms on a 16×4 world. After extinction,
   three food cells remain unused. Harsh resource/energy budgets with a
   large *N* produce carrying-capacity collapse (literature constraint 1).
3. **No movement.** Eater genome `101111000` is EAT / COPY / WAIT. Row-major
   spawn puts at most the first two organisms on food.
4. **Channel never emits.** No `EMIT_NEXUS` codon, so Goldsby-style
   isolation is vacuous: scramble vs treatment cannot differ when
   neither arm adopts (literature constraints 2–3).
5. Waiters (5/16) never eat. Death floor is ATP ≤ 0 after one
   consecutive tick.

This is assay failure, not a true null on `e1`. Okasha & Otsuka still
apply: the DAG is unchanged.

### Calibration (Wave 1b; not a prereg estimand change)

Survival knobs only, overlay-only (`_apply_survival_calibration`).
Phase A `life_loop_world(seed=7, tick_count=12, population=6)` pins
must stay green. No new signaling pathway.

| Knob | v1 / life-loop default | Wave 1b overlay |
|---|---|---|
| Index-0 genome | `101111000` (EAT, COPY, WAIT) | `101110000` (EAT, EMIT, WAIT) |
| Other eaters | `101111000` | `101000000` (EAT, WAIT, WAIT) |
| Waiters | `000000000` | `000000000` |
| Initial runtime ATP | 14.0 | 48.0 |
| Basal ATP / tick | 1.2 | 0.4 |
| Food amount | 6.0 | 12.0 |
| Respawn rate | 0.4 | 1.0 |
| Food layout | 2 cells | even *x* on first two rows |
| Starvation consecutive ticks | 1 | 3 |

Seeds, *n*, ticks, population, arms, dose, DAG, and the §8 statistical
decision rule are unchanged. Dated operational note: confirmatory
`intervention_supported` is not requested when `assay_failed` is true.
That is a quality gate in front of §8, not a new estimand.

### Results (research v2)

Prereg commit `135b2ac` still precedes these numbers (prereg file
bytes unchanged). Artifact:
[`hard_experiment_01/results_v2.json`](hard_experiment_01/results_v2.json).
Campaign digest
`2ba450ef1f2eb80f6860b865d91a15c52f506cad6e80811b6be1307ff2e158ae`.
`prereg_digest`
`cb4643a305a48a17250b4e38af3f423afc0c040b4ffac039c8b0ec1413b4fc40`.
Scale: 30 seeds (`11`…`40`), 40 ticks, population 16.
`StatisticalTestPolicy` tier: `research_grade_benchmark_candidate`.
Wall-clock: 745.8 s on the generating runner. Replay identity: snapshot
digest. `assay_failed`: **false**.

This is **`assay_invalid`**, not a scientific null. All four arms
produced bitwise-identical `terminal_mean_fitness` `0.164375`. Adoptions
were `169 / 169 / 0 / 169` (only `capsules_off` differs). The treatment
arm kept survivors (`extinction_rate = 0.0`) and the capsule channel
fired, but the intervention did not change the fitness estimand
(manipulation not realized). Public ClaimGate level remains 1. It is
not mechanism support and not intelligence.

### Primary contrasts (Holm, α = 0.05)

| Contrast | n | mean | sd | dz | CI95 | p_holm | claim_downgraded |
|---|---:|---:|---:|---:|---|---:|---|
| `on` vs `off` | 30 | 0.0 | 0.0 | 0.0 | [0.0, 0.0] | 1.0 | yes |
| `on` vs `capsules_off` | 30 | 0.0 | 0.0 | 0.0 | [0.0, 0.0] | 1.0 | yes |
| `on` vs `shuffled` | 30 | 0.0 | 0.0 | 0.0 | [0.0, 0.0] | 1.0 | yes |

`shuffled ≈ capsules_off`: yes (BCa CI [0.0, 0.0] includes 0). Both
arms share the same last-tick fitness; only adoptions differ
(`169` vs `0`).

### Arm table

| Arm | n | mean | sd | births mean | adoptions mean | extinction |
|---|---:|---:|---:|---:|---:|---:|
| `source_bias_on` | 30 | 0.164375 | 0.0 | 0.0 | 169.0 | 0.0 |
| `source_bias_off` | 30 | 0.164375 | 0.0 | 0.0 | 169.0 | 0.0 |
| `capsules_off` | 30 | 0.164375 | 0.0 | 0.0 | 0.0 | 0.0 |
| `capsules_shuffled` | 30 | 0.164375 | 0.0 | 0.0 | 169.0 | 0.0 |

Missing last-tick outcomes: 0 per arm. None zero-filled.

### Dose table (`FITNESS_WEIGHTED`)

| `min_source_fitness` | n | mean |
|---:|---:|---:|
| 0 | 30 | 0.164375 |
| 1 | 30 | 0.164375 |
| 2 | 30 | 0.164375 |
| 4 | 30 | 0.164375 |

Spearman ρ is undefined (zero variance). Consecutive means are
non-decreasing (ties). `same_direction_as_h1` is false. Trend supported:
**no**.

### Replay

All four arms × seeds `11` and `40`: **matched**. Campaign constructed.

### ClaimGate ceiling

**`runtime_observation`** (CLAIMS.md public level 1).
The Wave 2 standalone auditor must reproduce this public level from
`results_v2.json` ([`CLAIMGATE_STANDALONE.md`](CLAIMGATE_STANDALONE.md)).

Decision-rule failures:
`ci_on_vs_off_includes_0`,
`holm_on_vs_off_not_below_alpha`,
`ci_on_vs_shuffled_includes_0`,
`holm_on_vs_shuffled_not_below_alpha`,
`dose_trend_not_monotonic_same_direction`.
`intervention_supported` was **not** requested. Label: **`assay_invalid`**
(outcomes bitwise-identical across arms on the fitness estimand;
manipulation not realized). That is not a scientific null finding.
The source-bias gate *was* exercised (treatment adoptions > 0;
`capsules_off` adoptions = 0).

### Results (research v3) — Wave 1c

Amendment 01 (`docs/HARD_EXPERIMENT_01_PREREG_AMENDMENT_01.md`, digest
`6d156e824b9b9c4d06be4eb6f4d35f265592eab7c41d35a6b8c0ca951dfc7de8`) was committed before these
numbers; the frozen v2 prereg bytes are unchanged (`prereg_digest`
`cb4643a305a48a17250b4e38af3f423afc0c040b4ffac039c8b0ec1413b4fc40`). Artifact:
[`hard_experiment_01/results_v3.json`](hard_experiment_01/results_v3.json).
Campaign digest `e71321fa60f4ed3a97e07d12e23a9e86275a102ffeadbea94124099fa3446aef`.
Scale: 30 seeds (`11`…`40`), 40 ticks, population 16 (4 good emitters,
4 poor emitters, 8 receivers). Primary outcome: `receiver_mean_terminal_runtime_atp`.
Tier: `research_grade_benchmark_candidate`. Replay matched: **True**.
`assay_failed`: **False** (no manipulation-check failure).

### Primary contrasts (Holm, α = 0.05)

| Contrast | n | mean Δ (ATP) | dz | CI95 | p_holm | claim_downgraded |
|---|---:|---:|---:|---|---:|---|
| `source_bias_on` vs `source_bias_off` | 30 | 7.4750 | — | [7.4750, 7.4750] | 0.000150 | yes |
| `source_bias_on` vs `capsules_off` | 30 | 50.0500 | — | [50.0500, 50.0500] | 0.000150 | yes |
| `source_bias_on` vs `capsules_shuffled` | 30 | 49.5625 | — | [49.5625, 49.5625] | 0.000150 | yes |

`shuffled − capsules_off`: mean Δ 0.4875, CI95
[0.4875, 0.4875] (rule: lower bound ≤ 0 → fail).

### Arm table (receiver mean terminal runtime ATP)

| Arm | n | mean | sd | adoptions | bias applied | gate rejects | payloads | legacy fitness |
|---|---:|---:|---:|---:|---:|---:|---|---:|
| `source_bias_on` | 30 | 78.050 | 0.000 | 559.0 | 386.0 | 91.0 | {'EAT_LUMEN': 11580} | 0.9257 |
| `source_bias_off` | 30 | 70.575 | 0.000 | 559.0 | 412.0 | 0.0 | {'EAT_LUMEN': 10470, 'SENSE_DANGER': 1890} | 0.9289 |
| `capsules_off` | 30 | 28.000 | 0.000 | 0.0 | 0.0 | 0.0 | {} | 0.5496 |
| `capsules_shuffled` | 30 | 28.488 | 0.000 | 559.0 | 409.0 | 229.0 | {'EAT_LUMEN': 2820, 'SENSE_DANGER': 9450} | 0.7722 |
| `oracle_capsule` | 30 | 78.375 | 0.000 | 559.0 | 412.0 | 0.0 | {'EAT_LUMEN': 12360} | 1.0015 |

Missing last-tick outcomes: {'capsules_off': 0, 'capsules_shuffled': 0, 'oracle_capsule': 0, 'source_bias_off': 0, 'source_bias_on': 0}. None zero-filled.

### Dose table (`FITNESS_WEIGHTED`, pattern `step_up_then_saturate`)

| `min_source_fitness` | n | mean |
|---:|---:|---:|
| 0 | 30 | 70.575 |
| 1.5 | 30 | 78.050 |
| 4 | 30 | 28.000 |

Pattern statistic S = 57.525, permutation p = 0.000100,
pattern matched: True, supported: **True**.

### Replay

All five arms × seeds `11` and `40`: **matched**.

### ClaimGate ceiling

**`runtime_observation`** (decision rule passed: False;
ClaimGate allowed: False; final claim `runtime_observation`).
Decision-rule failures: `dz_undefined`, `shuffled_better_than_capsules_off`.

**Reading (honest).** The manipulation was realized for the first time:
the gate rejected poor sources only in `source_bias_on` (91 rejects/seed),
`source_bias_off` adopted the poor payload, `capsules_off` was silent,
the positive control moved the outcome (78.4 vs 28.0), and the dose
pattern matched (70.6 → 78.1 → 28.0). Receivers gated on source fitness
ended with +7.5 ATP over ungated receivers. **But every arm has sd = 0
across the 30 seeds**: the v3 overlay is fully deterministic given the
role layout (fixed roles, fixed food, respawn only refills eaten cells,
no births/mutation), so the seed carries no variance. Paired dz is
undefined, the BCa interval is a point, and the permutation p-values are
degenerate. The 30 "seeds" are 30 replays of one run. Inference is
therefore **not available**; the campaign is a valid single-configuration
demonstration, graded `runtime_observation`. Fixing this is Wave 1d
(seed-dependent randomization of role placement / food, see
`AGENT_HANDOFF`), not a statistics change.

`shuffled_better_than_capsules_off` fired on a +0.49 ATP point
difference with zero variance; with real seed variance this rule is
expected to be re-evaluated, not removed.

## Decision rule

Request existing `intervention_supported` only on the research campaign
when the treatment assay passes **and** CI(`on` vs `off`) and
CI(`on` vs `shuffled`) exclude 0, Holm p < 0.05 for both,
`shuffled` does not beat `capsules_off` (amendment 01), and the dose
pattern `step_up_then_saturate` is supported — with every required
ClaimGate flag. If allowed,
ceiling = `intervention_supported` (CLAIMS.md level 3). Else
`runtime_observation`. Never invent a label. Never claim
`collective_intelligence*`.

Assay gate (Wave 1b, 2026-09-12): if treatment-arm mean adoptions ≈ 0
or mean extinction ≈ 1 across seeds, record `assay_failed: true` and
keep `runtime_observation`. Primary contrasts may still be stored;
they are not claim-unlocking while the channel was not exercised.

Manipulation check (Wave 1c, amendment 01 §3): treatment bias applied
and gate rejects > 0; gate-off arm adopted the poor payload; channel-off
silent; shuffled channel active; positive control `oracle_capsule` above
`capsules_off`; arms not bitwise-identical. Any failure → `assay_failed`
with an `assay_failed_*` code, `assay_invalid` in the standalone auditor.

## Wave 1d″ — evidence honesty (no new claim)

See [`hard_experiment_01/WAVE_1D_DOUBLE_PRIME_HONESTY.md`](hard_experiment_01/WAVE_1D_DOUBLE_PRIME_HONESTY.md)
and [`../handoff/WAVE_1D_PRIME_REVIEW.md`](../handoff/WAVE_1D_PRIME_REVIEW.md).

The CONTENT shuffle control is a **cyclic peer-rotation that preserves the
payload marginal**, so `shuffled > capsules_off` is expected by construction
(~46.65% of the ~30.69 ATP treatment surplus is “channel with 50/50 pool”;
~53.35% is the gate). `capsule_adoptions` counts **attempts**, not successful
accepts; new runs expose `capsule_adoptions_accepted` and shuffle
`content_changed` / `source_changed` rates. Dose display for new runs is
`step_up_then_downturn` (Amd 01 frozen text unchanged): `dose(1.5)≡treatment`
and S is the algebraic sum of two primary contrasts (Hothorn 2020;
Simpson & Margolin 1986). ClaimGate stays **`runtime_observation`**. No
`results_v5.json` overwrite; Wave 1e content-null / activity-matched arms
are deferred to Amendment 04.

## Wave E6 (ODD + Morris screening)

Wave E6 documents the HE01 overlay in
[`HARD_EXPERIMENT_01_ODD.md`](HARD_EXPERIMENT_01_ODD.md) (Grimm 2020 ODD;
Claim level `runtime_observation`) and adds an exploratory Morris
elementary-effects screen
([`hard_experiment_01/morris_e6_design.md`](hard_experiment_01/morris_e6_design.md),
`codontrace.genesis.hard_experiment_01_morris`) on four post-Amd-03-safe
knobs (`read_radius`, `min_source_fitness`, basal cost, food amount).
Coverage and respawn stay Amd-03-frozen. Seeds are held-out exploratory
(2000–2009), never 11–40 or 1000–1009. Morris μ* is a qualitative rank,
not Holm/BCa and not a ClaimGate input. v5 remains assay PASS /
decision-rule FAIL (`shuffled_better_than_capsules_off`). E6 does not
claim `intervention_supported`. ODD ≠ intelligence.

## What this does not say

- Capsule adoption is not knowledge transfer.
- Source-fitness gating is not communication intelligence.
- Last-tick fitness is not evolved instinct, OEE, or AGI.
- This is not an Avida replacement study and not Phase L or Phase M+.
- A Price identity without the DAG is not a causal claim.

Honesty pointer: [`WHY_NOT_INTELLIGENCE_YET.md`](WHY_NOT_INTELLIGENCE_YET.md).
Phase letter index: [`PHASE_INDEX.md`](PHASE_INDEX.md).
Replay pins: [`ENGINE_REPLAY_CONTRACT.md`](ENGINE_REPLAY_CONTRACT.md).
