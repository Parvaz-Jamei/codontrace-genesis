# Hard experiment 01 — capsule source-bias and next-generation fitness

One measurement question. Not a new Phase letter. Not intelligence.
Product name: **CodonTrace Genesis**.

**Question.** Does source-fitness-weighted capsule transfer raise last-tick
(next-generation) mean fitness relative to (a) the same capsule channel with
source-fitness gating ablated, (b) capsules off, and (c) the channel on with
content scrambled?

**Preregistration.** [`HARD_EXPERIMENT_01_PREREG.md`](HARD_EXPERIMENT_01_PREREG.md)
is frozen in an earlier commit. Campaign payloads record `prereg_digest`.

**Claim ceiling:** `runtime_observation` unless the preregistered decision
rule holds **and** ClaimGate allows existing `intervention_supported`.
Smoke (`n=12`) is `exploratory_only` and stays `runtime_observation`.

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

This is a **null finding**. Last-tick mean fitness was identically 0 on
every arm. Capsule adoptions were 0 — the source-bias gate never acted
because the channel did not transfer. Populations were extinct at the
last tick (`extinction_rate = 1.0`). A zero delta is not mechanism
support and is not intelligence.

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

### Limitations

- Life-loop overlay, not an Avida ISA.
- At 40 ticks / pop 16 the overlay reached last-tick extinction with
  zero capsule adoptions, so the confirmatory DAG edges `e1`/`e2` were
  not exercised. This is a substrate/horizon observation, not a proof
  that source-fitness weighting cannot matter in a living population.
- Terminal mean fitness is a last-tick observation.
- Replay identity is the snapshot digest, not the full run-result hash.
- Smoke (`n=12`) remains `exploratory_only`.
- Not knowledge-transfer proof. Not intelligence.

This section does not use intelligence, AGI, Tokyo Type 1, or
Avida-replacement language.

## Decision rule

Request existing `intervention_supported` only on the research campaign
when CI(`on` vs `off`) and CI(`on` vs `shuffled`) exclude 0, Holm p < 0.05
for both, `shuffled ≈ capsules_off`, and the dose trend is monotonic in
the H1 direction — with every required ClaimGate flag. If allowed,
ceiling = `intervention_supported` (CLAIMS.md level 3). Else
`runtime_observation`. Never invent a label. Never claim
`collective_intelligence*`.

## What this does not say

- Capsule adoption is not knowledge transfer.
- Source-fitness gating is not communication intelligence.
- Last-tick fitness is not evolved instinct, OEE, or AGI.
- This is not an Avida replacement study and not Phase L or Phase M+.
- A Price identity without the DAG is not a causal claim.

Honesty pointer: [`WHY_NOT_INTELLIGENCE_YET.md`](WHY_NOT_INTELLIGENCE_YET.md).
Phase letter index: [`PHASE_INDEX.md`](PHASE_INDEX.md).
Replay pins: [`ENGINE_REPLAY_CONTRACT.md`](ENGINE_REPLAY_CONTRACT.md).
