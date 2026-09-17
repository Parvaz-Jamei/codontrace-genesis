# Open-ended discovery ClaimGate campaign report

- campaign_id: `open_ended_discovery_campaign_v1`
- scale: `S1`
- proposals: **5**
- accept_count: **1** (20%)
- reject_count: **4** (80%)
- beat_all_negatives_count: **1**
- claim_ceiling: **`runtime_observation`**
- report_digest: `6dd6c7897bdede9d41faf7ff8101955952a122ee4cacd1d54db52a3bbbcd7e38`

## Honesty

100% reject is valid data — do not fabricate passes. Ceiling stays
`runtime_observation` unless a proposal is meaningfully better than
all three negatives (`proposer_random`, `proposer_shuffled_archive`,
`archive_no_op`). No AGI / collective-intelligence claims.

## Literature

- ASAL: Kumar et al., arXiv:2412.17799 / Artificial Life 2025
- Flageat, Janmohamed, Lim & Cully, IEEE TEVC 30(1):286–295 (2026), arXiv:2409.13315
- MAP-Elites (Mouret & Clune 2015); QD Chatzilygeroudis et al. 2021; OMNI-EPIC 2024
- HE01 lesson: weak negatives insufficient — need three discovery negatives

## Per-proposal

- `random:7:RAND:337731` accepted=False ceiling=runtime_observation score=0.5283244208 reasons=['not_better_than_proposer_random', 'not_better_than_proposer_shuffled_archive', 'held_at_runtime_observation']
- `random:8:RAND:871869` accepted=True ceiling=discovery_witness_candidate score=1.2154328218 reasons=['meaningfully_better_than_all_three_negatives']
- `stub:17:STUB:stub-novelty-v0:801118` accepted=False ceiling=runtime_observation score=0.6042539684 reasons=['not_better_than_proposer_random', 'not_better_than_proposer_shuffled_archive', 'held_at_runtime_observation']
- `stub:18:STUB:stub-novelty-v0:408000` accepted=False ceiling=runtime_observation score=0.5472902319 reasons=['not_better_than_proposer_random', 'not_better_than_proposer_shuffled_archive', 'held_at_runtime_observation']
- `random:9:RAND:764700` accepted=False ceiling=runtime_observation score=0.7062838667 reasons=['not_better_than_proposer_random', 'held_at_runtime_observation']

