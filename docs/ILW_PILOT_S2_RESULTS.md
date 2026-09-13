# ILW S2 pilot artifact

**Status:** `PASS`
**Prereg:** `ilw_prereg_v1`
**ClaimGate ceiling:** `runtime_observation` (unchanged)
**Scientific name:** `integrated eco-evolutionary runtime`
**Design digest:** `ilw_prereg_design:998654e9d27f5f314b7fa587785dac76fef4d7c1cdeb08cfcc74a83ba369c673`
**Document digest:** `81dbfc057a7ff89e539940575bb51cbfb8db5f185fa282d9dd39963a3e9b125d`

## Gates

| Gate | Value |
|------|-------|
| `replay_ok` | `True` |
| `conservation_ok` | `True` |
| `edge_coverage_ok` | `True` |
| `pom_patterns_recorded` | `True` |
| `no_claim_promotion` | `True` |
| `claim_ceiling_ok` | `True` |
| `all_passed` | `True` |

## POM patterns

| ID | Verdict | Note |
|----|---------|------|
| `pom_1_toolchain_phenotype` | `pass` | required-edge coverage includes toolchain→phenotype→action chain |
| `pom_2_conservation` | `pass` | resource/energy conservation assays across pilot seeds |
| `pom_3_multigen_turnover` | `pass` | min generation_turnover=26 (need ≥3); min lineage_depth=2 |
| `pom_4_diversity` | `pass` | min unique_genome_count=33 |
| `pom_5_eco_evo_feedback` | `pass` | min niches_occupied=3; ecological_feedback edge covered |
| `pom_6_capsule_causal` | `pass` | capsule_to_policy applied>0 on each pilot seed (descendant fitness proxy via policy bias) |
| `pom_7_null_yoked_break` | `pass` | knockout probe: {'seed': 3100, 'knockout_id': 'capsule_to_policy_off', 'edge_id': 'capsule_to_policy', 'intact_applied': 662, 'knockout_applied': 0, 'knockout_blocked': 908, 'path_broke_as_predicted': True} |
| `pom_8_scale_direction` | `pass` | S1→S2 probe: {'seed': 3100, 's1_coverage': 1.0, 's2_coverage': 1.0, 's1_births': 20, 's2_births': 34, 'effect_direction_retained': True, 'note': 'Coverage+births retention S1→S2; not a finite-size S4 claim.'} |

## Seed metrics

| Seed | Replay | Cons | Cov | Turnover | Lineage | Genomes | Births | Deaths |
|------|--------|------|-----|----------|---------|---------|--------|--------|
| 3100 | True | True | 100% | 30 | 3 | 34 | 30 | 35 |
| 3101 | True | True | 100% | 27 | 2 | 36 | 28 | 31 |
| 3102 | True | True | 100% | 31 | 2 | 39 | 34 | 34 |
| 3103 | True | True | 100% | 41 | 4 | 46 | 41 | 48 |
| 3104 | True | True | 100% | 26 | 3 | 33 | 27 | 31 |
| 3105 | True | True | 100% | 29 | 4 | 39 | 32 | 34 |
| 3106 | True | True | 100% | 33 | 3 | 40 | 34 | 39 |
| 3107 | True | True | 100% | 31 | 3 | 37 | 32 | 38 |

## Knockout probe

```json
{
  "edge_id": "capsule_to_policy",
  "intact_applied": 662,
  "knockout_applied": 0,
  "knockout_blocked": 908,
  "knockout_id": "capsule_to_policy_off",
  "path_broke_as_predicted": true,
  "seed": 3100
}
```

## Scale probe (S1→S2)

```json
{
  "effect_direction_retained": true,
  "note": "Coverage+births retention S1\u2192S2; not a finite-size S4 claim.",
  "s1_births": 20,
  "s1_coverage": 1.0,
  "s2_births": 34,
  "s2_coverage": 1.0,
  "seed": 3100
}
```

## Honesty

- No ClaimGate ladder promotion.
- No CCE / intelligence / AGI claim.
- Confirmatory seeds untouched in this artifact.
- `regime_changes=0` (discrete regime shifter not wired yet; honest).

