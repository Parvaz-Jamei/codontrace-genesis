# Hard experiment 01 — capsule source-bias and next-generation fitness

One measurement question. Not a new Phase letter. Not intelligence.

**Question.** Does source-fitness-weighted capsule transfer change last-tick
(next-generation) mean fitness relative to (a) the same capsule channel with
source-fitness gating ablated and (b) capsules off?

**Claim ceiling:** `runtime_observation` only.

**Blocked:** `intelligence`, `collective_intelligence`, `agi`,
`tokyo_type1_passed`, `avida_replacement`, and related ClaimGate aliases.

## Design

| Item | Choice |
|---|---|
| Product | CodonTrace Genesis |
| Seeds | 12 paired (`11` … `22`) is the **smoke / exploratory** default (`StatisticalTestPolicy.tier_for_n(12) == exploratory_only`). Research-grade n is **30**. |
| Substrate | Phase A `life_loop_world` overlay (does **not** change A–E pins) |
| Ticks / N | 6 ticks, population 4 |
| Treatment | `source_bias_on`: capsules on, `min_source_fitness=2.0`, `FITNESS_WEIGHTED` |
| Ablation | `source_bias_off`: capsules on, `min_source_fitness=0.0`, `THRESHOLD` |
| Control | `capsules_off`: transfer disabled |
| Outcome | last-tick `selection_mean_fitness` (terminal / next-generation population state) |
| Effect size | `estimate_effect_size_lite` on paired seed vectors |
| Replay | independent re-run of seed 11 treatment; spec + result digests must match |
| Library | `codontrace.genesis.hard_experiment_01` |
| Example | `examples/genesis_hard_experiment_01.py` |

`CapsuleAblationPolicy.enable_source_fitness_weighting` is a digest-backed
policy object and is **not** the runtime gate. This experiment uses the
wired `CapsuleTransferConfig` knobs (`min_source_fitness`, adoption policy).

## Interventions

Each arm is one explicit intervention. The treatment keeps source-fitness
bias on. The first ablation turns that bias off and leaves the capsule
channel. The second ablation turns the channel off.

| Arm | Role | Knob | Applied value |
|---|---|---|---|
| `source_bias_on` | treatment | `min_source_fitness` + `adoption_policy` | `2.0` / `FITNESS_WEIGHTED` |
| `source_bias_off` | mechanism ablation | same knobs | `0.0` / `THRESHOLD` |
| `capsules_off` | channel off | `CapsuleTransferConfig.enabled` | `False` |

See `hard_experiment_01_interventions()`. A null or small effect is valid.

## How to run

```python
from codontrace.genesis.hard_experiment_01 import (
    evaluate_hard_experiment_01_claim,
    run_hard_experiment_01,
)

campaign = run_hard_experiment_01()  # 12 seeds: exploratory / smoke
# research-grade language requires seed_count=30
print(campaign.mean_delta_vs_source_bias_off)
print(campaign.effect_vs_capsules_off.interpretation)
print(evaluate_hard_experiment_01_claim(campaign).final_claim)
```

```bash
python examples/genesis_hard_experiment_01.py
```

A null or small descriptive effect is a valid finding. The campaign object
refuses a claim ceiling other than `runtime_observation` and will not
construct if replay digests fail to match.

## What this does not say

- Capsule adoption is not knowledge transfer.
- Source-fitness gating is not communication intelligence.
- Last-tick fitness is not evolved instinct, OEE, or AGI.
- This is not an Avida replacement study and not Phase L.

Honesty pointer: [`WHY_NOT_INTELLIGENCE_YET.md`](WHY_NOT_INTELLIGENCE_YET.md).
Phase letter index: [`PHASE_INDEX.md`](PHASE_INDEX.md).
Replay pins: [`ENGINE_REPLAY_CONTRACT.md`](ENGINE_REPLAY_CONTRACT.md).
