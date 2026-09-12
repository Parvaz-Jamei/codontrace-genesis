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
| Replay | all arms × `seeds[0]` and `seeds[-1]`; campaign refuses a mismatch |
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

## Results: not yet recorded

Research-scale numbers are generated **after** the preregistration commit
and archived in [`hard_experiment_01/results_v1.json`](hard_experiment_01/results_v1.json)
when the research campaign has been run. Until that artifact exists, do
not copy informal local printouts into this section.

- Arm table (n, mean, sd, dz, CI95, p_holm): **not yet recorded**
- Dose table: **not yet recorded**
- Extinction per arm: **not yet recorded**
- Replay status: **not yet recorded**
- ClaimGate ceiling: **not yet recorded** (smoke stays `runtime_observation`)

This section must not be filled with intelligence, AGI, Tokyo Type 1, or
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
