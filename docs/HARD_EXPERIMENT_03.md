# HARD_EXPERIMENT_03 — task-switch costs and division of labor (E3)

Product: **CodonTrace Genesis** (`0.3.0b4.dev0`).

## Status

- Prereg draft-locked: [`HARD_EXPERIMENT_03_PREREG.md`](HARD_EXPERIMENT_03_PREREG.md)
- Science brief: [`hard_experiment_03/HE03_SCIENCE_BRIEF.md`](hard_experiment_03/HE03_SCIENCE_BRIEF.md)
- Knobs (default off): `TaskSwitchCostConfig`, `IsolationAssayConfig`
- Metric: `codontrace.genesis.metrics.division_of_labor.gorelick_nmi` (confirmatory; non-NMI proxies remain **legacy**)
- ClaimGate ceiling starts at **`runtime_observation`**
- Phase A–E `life_loop_world(seed=7, tick_count=12, population=6)` pins unchanged

## Arms

| Arm | Role |
|-----|------|
| cost_0 | control (`switch_cost_atp=0`, enabled) |
| cost_moderate | treatment (~25-cycle Goldsby analogue → 0.25 ATP) |
| cost_high | treatment (~50-cycle Goldsby analogue → 0.50 ATP) |
| channel_off | mechanism ablation (knob disabled) |
| isolation_probe | secondary IsolationAssay only |

## Seeds / scale

- Pilot: 1000–1009
- Research: 30 seeds disjoint from pilot (2000–2029)
- Smoke in CI; research outside CI with committed `results_v1.json` when cleared

## Artifacts

- Pilot / research JSON under `docs/hard_experiment_03/` when run (not fabricated here)

## ClaimGate

Adapter: `codontrace.claimgate.adapters.bundle_from_hard_experiment_03`.
Ceiling is not raised by this document. Forbidden aliases unchanged.
IsolationAssay is **secondary** and does not license `collective_intelligence*` claims.

## Literature (baked into design; not new science)

- Goldsby et al. 2012 *PNAS* — task-switch costs promote DoL + loss of lower-level autonomy
- Gorelick & Bertram 2007 / Gorelick et al. 2004 — NMI/NME for DoL
- 2023 bioRxiv multicellularity entrenchment — context only
- Montanier / Boumaza 2021 isolation literature — informs IsolationAssay design only
