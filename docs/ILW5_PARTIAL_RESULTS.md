# ILW-5 partial confirmatory results

**Status:** Partial local confirmatory subset **expanded** (30/38 planned cells; 30/312 enumerated).  
**ClaimGate ceiling:** `runtime_observation` (unchanged — **no promotion**).  
**Scientific name:** `integrated eco-evolutionary runtime`  
**Intelligence / CCE / AGI claims:** **none** (forbidden; not emitted).

## Scope (this partial)

Held-out confirmatory seeds only (`4100..4107`). Pilot seeds analysis-forbidden.

Planned local subset (not the full 312 enumerated cells):

| Block | Cells |
|-------|-------|
| Ablation (baseline + 7 OAT knockouts) × seeds 4100–4103 | 32 |
| Interaction screening × seed 4100 | 4 |
| Small S4 slice (32 & 64 width × t128 × pop64) × seed 4100 | 2 |
| **Planned total (expanded)** | **38** |
| Full design enumeration | **312** |

Artifact: `outputs/ilw5_campaign_partial.json`  
Digests: `ilw_prereg_design_digest`, `ilw_prereg_document_digest` recorded on artifact.

## Honesty

- Only **executed** cells are recorded; no invented outcome table.
- `campaign_outcomes_invented: false`
- Replay digest check for this partial defaults **off** (`run_replay=false`) for wall-clock; S2 smoke already showed `replay_matched=true` for baseline + `capsule_to_policy_off` at seed 4100.
- ClaimGate stays `runtime_observation`. No ladder promotion.

## Executed summary

Artifact counts (honest runtime observations only):

| Metric | Value |
|--------|-------|
| Executed / planned (this subset) | 30 / 38 |
| Executed / enumerated (full design) | 30 / 312 |
| By kind | `{'ablation': 21, 'baseline': 3, 'interaction': 4, 'scale_s4': 2}` |
| ClaimGate ceiling | `runtime_observation` |
| Outcomes invented | `False` |
| Intelligence claimed | `False` |
| Replay in this partial | `False` |

All executed cells: `conservation_passed=true`, `required_edge_coverage=1.0`, `scientific_claim_emitted=false`, `claim_ceiling=runtime_observation`.

### Completed cell ids

- `baseline-S2-4100` (birth=25, death=27, turnover=24, coverage=1.0, conservation=True)
- `ablation-toolchain_to_action_off-S2-4100` (birth=12, death=20, turnover=12, coverage=1.0, conservation=True)
- `ablation-experience_to_capsule_off-S2-4100` (birth=26, death=29, turnover=23, coverage=1.0, conservation=True)
- `ablation-capsule_transport_off-S2-4100` (birth=31, death=35, turnover=29, coverage=1.0, conservation=True)
- `ablation-capsule_to_policy_off-S2-4100` (birth=34, death=35, turnover=31, coverage=1.0, conservation=True)
- `ablation-mutation_off-S2-4100` (birth=0, death=36, turnover=32, coverage=1.0, conservation=True)
- `ablation-ecological_feedback_off-S2-4100` (birth=31, death=39, turnover=31, coverage=1.0, conservation=True)
- `ablation-lineage_inheritance_off-S2-4100` (birth=492, death=477, turnover=469, coverage=1.0, conservation=True)
- `baseline-S2-4101` (birth=27, death=34, turnover=27, coverage=1.0, conservation=True)
- `ablation-toolchain_to_action_off-S2-4101` (birth=11, death=19, turnover=11, coverage=1.0, conservation=True)
- `ablation-experience_to_capsule_off-S2-4101` (birth=32, death=35, turnover=29, coverage=1.0, conservation=True)
- `ablation-capsule_transport_off-S2-4101` (birth=25, death=27, turnover=23, coverage=1.0, conservation=True)
- `ablation-capsule_to_policy_off-S2-4101` (birth=29, death=32, turnover=27, coverage=1.0, conservation=True)
- `ablation-mutation_off-S2-4101` (birth=0, death=31, turnover=27, coverage=1.0, conservation=True)
- `ablation-ecological_feedback_off-S2-4101` (birth=36, death=44, turnover=36, coverage=1.0, conservation=True)
- `ablation-lineage_inheritance_off-S2-4101` (birth=211, death=205, turnover=197, coverage=1.0, conservation=True)
- `baseline-S2-4102` (birth=39, death=45, turnover=38, coverage=1.0, conservation=True)
- `ablation-toolchain_to_action_off-S2-4102` (birth=10, death=18, turnover=10, coverage=1.0, conservation=True)
- `ablation-experience_to_capsule_off-S2-4102` (birth=28, death=32, turnover=26, coverage=1.0, conservation=True)
- `ablation-capsule_transport_off-S2-4102` (birth=26, death=30, turnover=22, coverage=1.0, conservation=True)
- `ablation-capsule_to_policy_off-S2-4102` (birth=32, death=35, turnover=29, coverage=1.0, conservation=True)
- `ablation-mutation_off-S2-4102` (birth=0, death=32, turnover=28, coverage=1.0, conservation=True)
- `ablation-ecological_feedback_off-S2-4102` (birth=28, death=36, turnover=28, coverage=1.0, conservation=True)
- `ablation-lineage_inheritance_off-S2-4102` (birth=454, death=443, turnover=435, coverage=1.0, conservation=True)
- `interaction-toolchainxcapsule-S2-4100` (birth=10, death=18, turnover=10, coverage=1.0, conservation=True)
- `interaction-capsulexecology-S2-4100` (birth=22, death=30, turnover=22, coverage=1.0, conservation=True)
- `interaction-mutationxcapsule-S2-4100` (birth=0, death=35, turnover=30, coverage=1.0, conservation=True)
- `interaction-heterogeneityxpopulation_size-S2-4100` (birth=19, death=27, turnover=19, coverage=1.0, conservation=True)
- `s4-32x32-t128-p64-4100` (birth=25, death=28, turnover=23, coverage=1.0, conservation=True)
- `s4-64x64-t128-p64-4100` (birth=35, death=36, turnover=32, coverage=1.0, conservation=True)

### Remaining planned (this subset)

- `baseline-S2-4103`
- `ablation-toolchain_to_action_off-S2-4103`
- `ablation-experience_to_capsule_off-S2-4103`
- `ablation-capsule_transport_off-S2-4103`
- `ablation-capsule_to_policy_off-S2-4103`
- `ablation-mutation_off-S2-4103`
- `ablation-ecological_feedback_off-S2-4103`
- `ablation-lineage_inheritance_off-S2-4103`


## Remainder

- Ablation × seeds 4102–4107
- Interaction × seeds 4101–4107
- Full S4 27-cell grid × 8 seeds
- Morris EE + DSD continuous arms (prereg-locked; execute off-box / Colab)

Do **not** loosen ClaimGate. Do **not** claim intelligence.
