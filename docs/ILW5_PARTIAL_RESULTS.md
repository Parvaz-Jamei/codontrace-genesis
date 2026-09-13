# ILW-5 partial confirmatory results

**Status:** Partial local confirmatory subset in progress / landed.  
**ClaimGate ceiling:** `runtime_observation` (unchanged — **no promotion**).  
**Scientific name:** `integrated eco-evolutionary runtime`  
**Intelligence / CCE / AGI claims:** **none** (forbidden; not emitted).

## Scope (this partial)

Held-out confirmatory seeds only (`4100..4107`). Pilot seeds analysis-forbidden.

Planned local subset (not the full 312 enumerated cells):

| Block | Cells |
|-------|-------|
| Ablation (baseline + 7 OAT knockouts) × seeds 4100–4101 | 16 |
| Interaction screening × seed 4100 | 4 |
| Small S4 slice (32 & 64 width × t128 × pop64) × seed 4100 | 2 |
| **Planned total** | **22** |
| Full design enumeration | **312** |

Artifact: `outputs/ilw5_campaign_partial.json`  
Digests: `ilw_prereg_design_digest`, `ilw_prereg_document_digest` recorded on artifact.

## Honesty

- Only **executed** cells are recorded; no invented outcome table.
- `campaign_outcomes_invented: false`
- Replay digest check for this partial defaults **off** (`run_replay=false`) for wall-clock; S2 smoke already showed `replay_matched=true` for baseline + `capsule_to_policy_off` at seed 4100.
- ClaimGate stays `runtime_observation`. No ladder promotion.

## Executed summary

_See JSON artifact for per-cell digests and gate fields. Counts below refreshed when the partial runner lands cells._

| Metric | Value |
|--------|-------|
| Executed / planned (this subset) | _pending first batch_ |
| Executed / enumerated (full design) | _pending_ / 312 |

## Remainder

- Ablation × seeds 4102–4107
- Interaction × seeds 4101–4107
- Full S4 27-cell grid × 8 seeds
- Morris EE + DSD continuous arms (prereg-locked; execute off-box / Colab)

Do **not** loosen ClaimGate. Do **not** claim intelligence.
