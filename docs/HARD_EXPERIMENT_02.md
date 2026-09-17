# HARD_EXPERIMENT_02 — food-patch signalling under deme/kin selection

Product: **CodonTrace Genesis** (`0.3.0b4`).

## Status

- Prereg draft-locked: [`HARD_EXPERIMENT_02_PREREG.md`](HARD_EXPERIMENT_02_PREREG.md)
- Science brief: [`hard_experiment_02/HE02_SCIENCE_BRIEF.md`](hard_experiment_02/HE02_SCIENCE_BRIEF.md)
- Knobs (default off): `FoodPatchSignalConfig`, `DemeSelectionConfig`, `SteppingStoneRewardConfig`
- Action `MOVE_TOWARD_CAPSULE_TARGET` is registered only on HE02 specs (not in the default action registry)
- ClaimGate ceiling starts at **`runtime_observation`**
- **Research `results_v1`: landed** under `docs/hard_experiment_02/results_v1.json`
  (seed rows frozen). Original contrast block stored `dz=None` because
  `paired_effect_size` was called with two arm vectors. Corrected analysis:
  [`hard_experiment_02/ANALYSIS_CORRECTION_v1b.md`](hard_experiment_02/ANALYSIS_CORRECTION_v1b.md).
  Ceiling stays `runtime_observation` (shuffled control not separated).
- Phase A–E `life_loop_world(seed=7, tick_count=12, population=6)` pins unchanged

## Arms

| Arm | Role |
|-----|------|
| treatment | E1 + E2 GERMLINE×CLONAL + E5 |
| content_null | cost-matched useless payloads |
| activity_matched | yoked escape-from-WAIT |
| channel_off | CapsuleTransfer disabled |
| capsules_shuffled | source↔payload ablation (MI≈0) |
| oracle_moderate | useful fraction f=0.5 |

## E2 ordinal prediction

`GERMLINE×CLONAL > GERMLINE×MIXED ≈ INDIVIDUAL×CLONAL > INDIVIDUAL×MIXED`

## Seeds / scale

- Pilot: 1000–1009
- Research: 30 seeds disjoint from pilot (2000–2029)
- Smoke in CI; research outside CI with committed `results_v1.json`

## Artifacts

- Pilot: [`hard_experiment_02/pilot_v1.json`](hard_experiment_02/pilot_v1.json)
- Research: [`hard_experiment_02/results_v1.json`](hard_experiment_02/results_v1.json)
- Analysis v1b: [`hard_experiment_02/analysis_v1b_contrasts.json`](hard_experiment_02/analysis_v1b_contrasts.json) (same seeds; not a new run)

## ClaimGate

Adapter: `codontrace.claimgate.adapters.bundle_from_hard_experiment_02`.
Ceiling is not raised by this document. Forbidden aliases unchanged.
