# Wave B — Integrate + test feedback (2026-09-25 Round 2)

## Implemented (ADOPT → code)

| ID | Module / surface | Notes |
|---|---|---|
| INN-07 | `life_loop/persistent_entropy.py` | Shannon entropy of H0 merge lifetimes |
| INN-08 | `life_loop/mapper_cover.py` | Tag-count lens + nerve cover graph |
| INN-09 | `genesis/host_parasite_analytics.py` | `run_front_door_mediation_contrast` |
| INN-10 | `life_loop/spectral_structure.py` | Laplacian Fiedler + Jacobi spectrum |
| INN-11 | `life_loop/transfer_entropy.py` | Granger-lite MSE reduction + TE-lite bins |
| INN-12 | `life_loop/conformal_bands.py` | Split conformal + selective abstention |
| INN-13 | `life_loop/ess_invasion.py` | Invasion-fitness ESS-candidate indicator |
| INN-14 | `life_loop/sparse_recovery.py` | ISTA-lite soft-threshold sparse support |

life_loop refuse fields use domain-free names (`arms_race_proved`, `causality_proved`, `ess_proved`, `coverage_guaranteed_proved`, `gene_identity_proved`, `locus_identity_proved`). Analytics retain `red_queen_proved` / `intervention_supported` / `front_door_identified` refuse pins.

## Test results

### Campaign unit + hard battery
`pytest tests/campaigns/innovation_20260925_r2/` → **22+ passed** (Wave B units green first; Wave C included in same tree)

## Failing → fixed log

| Cycle | Defect class | Symptom | Fix | Progress |
|---|---|---|---|---|
| 1 | Indent / ablation preset | Front-door `match_off` invalid; IndentationError after patch | Use `structure_null`; fix indent | Import broken → smoke OK |
| 2 | Hard-battery API drift | `write_*` arg order, `suite_id`, `world_summary_row(world)` | Match Round-1 export/calib signatures; wire `apply_farm` | Hard battery red → green |

No ClaimGate ceiling loosened. No `engine.py` changes. No open engineering failures. Repair cycles ≤ 5.

## Accept gates

- [x] Adopted innovations implemented
- [x] Unit tests green
- [x] ClaimGate / BAIC pins untouched
- [x] Repair cycles ≤ 5 with measurable progress
