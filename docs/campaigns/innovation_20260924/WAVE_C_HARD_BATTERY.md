# Wave C — Hard unsolved-style battery (2026-09-24)

## Design targets

1. **Refuse-safe Red Queen structure** — high β₁-proxy on reticulate phenotype graph + continuum coupling gradient; `red_queen_proved=False` on reciprocal contrast.
2. **Costly resistance tradeoff** — primary intervention contrast with dual_null arm; info-geometry distance between specialized vs disjoint maps; no therapy claim.
3. **Identifiable DiD** — pre/post × treat/control + dual_null post cell; `identifiability=observational_bounds`; refuses `intervention_supported` / `price_as_causality`.
4. **Full stack wiring** — HostParasiteWorld + HookMeter + MatchRule phenotype + skyline + allele assoc + FARM + CSV/JSON export + calibration suite + BAIC pin assert.

## Tests

Path: `tests/campaigns/innovation_20260924/test_hard_battery.py`

| Test | Result |
|---|---|
| `test_hard_rq_structure_without_proved_claim` | PASS |
| `test_hard_costly_resistance_tradeoff_dual_null` | PASS |
| `test_hard_did_identifiable_observational_bounds` | PASS |
| `test_hard_full_stack_skyline_allele_farm_export` | PASS |
| `test_hard_claimgate_ceilings_intact` | PASS |
| `test_hard_no_engine_infection_physics` | PASS |

## Explicit ClaimGate-honest refuses (not bugs)

- `red_queen_proved` (genesis analytics / calibration / reciprocal)
- `intervention_supported`
- `price_as_causality`
- `raises_claim_ladder`
- `epidemic_forecast_certified` (skyline)
- `gene_identity_proved` / `locus_identity_proved` (allele)
- `arms_race_proved` / `transition_proved` (topology life_loop)
- BAIC-HE01 pin digests unchanged (`assert_baic_pins_untouched`)

## Spectacular ≠ fake

Strong effect sizes observed (β₁-proxy cyclic ≫ disjoint; continuum proxy span > 0; JS/Fisher distances > thresholds) while all proved ceilings remain refused.
