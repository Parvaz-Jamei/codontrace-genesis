# ILW-5 campaign harness (factorial / ablation / scale)

**Status:** Harness landed + local confirmatory smoke (1–2 cells) + **partial confirmatory subset** (`outputs/ilw5_campaign_partial.json`).  
**ClaimGate ceiling:** `runtime_observation` (unchanged).  
**Scientific name:** `integrated eco-evolutionary runtime`  
**Prereq:** S2 pilot gates PASS (`docs/ILW_PILOT_S2_RESULTS.md` / `outputs/ilw_pilot_s2.json`).

## What this milestone is

ILW-5 encodes the locked prereg DoE as **executable cells**:

| Arm | Builder | Role |
|-----|---------|------|
| Baseline + OAT ablations | `build_ablation_cells` | Intact + each of 7 edge knockouts (still not inference-complete alone) |
| Interaction pairs | `build_interaction_screening_cells` | 2-factor offs for the four prereg interactions |
| S4 finite-size | `build_s4_scale_cells` | widths×horizons×pop-caps grid |

Seeds: **held-out confirmatory only** (`4100..4107`). Pilot seeds remain analysis-forbidden here.

Digests recorded on every artifact:

- `ilw_prereg_design_digest`
- `ilw_prereg_document_digest`

## Partial confirmatory (local)

See `docs/ILW5_PARTIAL_RESULTS.md` and `outputs/ilw5_campaign_partial.json`.

Runner: `scripts/run_ilw5_partial.py` / `run_ilw5_partial()` (resume-friendly checkpoints).

## Local smoke (executed)

See `outputs/ilw5_campaign_smoke.json`:

1. Confirmatory baseline at S2, seed `4100`
2. Single-edge ablation `capsule_to_policy_off` at S2, seed `4100`

Honest runtime_observation only — **no** invented full-campaign outcome table, **no** CCE/intelligence claim, **no** ClaimGate promotion.

## Remaining (Colab / Drive style)

Enumerate with `enumerate_campaign_design()`:

- Confirmatory seeds `4100..4107`
- Full ablation + interaction arms per seed
- Full S4 grid (3×3×3 per seed by default)
- Morris EE screening + three-level DSD continuous factors (design locked in prereg; execute off-box)

Do **not** loosen ClaimGate. Do **not** start ILW-6 until this harness stays solid.

## Code map

| Path | Role |
|------|------|
| `src/codontrace/genesis/ilw/pilot.py` | S2 pilot runner + gate artifact |
| `src/codontrace/genesis/ilw/campaign.py` | ILW-5 cell builders + smoke + partial runner |
| `src/codontrace/genesis/ilw/prereg.py` | Locked design + PilotHarness unlock |
| `tests/test_ilw_pilot_gates.py` | Fast gate/POM unit tests |
| `tests/test_ilw5_campaign.py` | Design enumeration tests |
