# Phase 25 review — HE_HP locked-digest refresh note

Human research review of an honesty refresh that confirms HE_HP Phase 7–9
locked campaign digests still replay after Waves 5–6. Documentation / replay
hygiene only. BAIC pins remain byte-identical forever.

**Experts:** A — digital evolution / ALife · B — microbial / phage honesty ·
C — ClaimGate / V&V / causal methodology.

## What Phase 25 delivers

- `build_he_hp_locked_digest_refresh_note` in `host_parasite_he_hp_refresh.py`.
- Replay of zaman / VT×spatial / evolvability / Cornish locked digests.
- BAIC pin byte check.
- `attach_he_hp_locked_digest_refresh` (prereg-bound).
- Evidence note refresh under `evidence/he_hp_locked_digests.md`.
- Tests in `tests/test_host_parasite_phase25.py`.

## موج ۱ / Critique round 1 (experts A / B / C)

### A

1. Stacked main after Wave 5 could leave reviewers unsure which HE_HP digests remain locked.

### B

2. Refresh must not invent wet identity or therapy claims.

### C

3. Any BAIC pin drift would be a paper-safety failure.

### Fixes (round 1)

- Explicit campaign_lock_status for all four HE_HP campaigns.
- Forced red_queen_proved / intervention_supported False.
- SHA256 pin assert before note build.

### Retest (round 1)

Phase 25 green; all four locks replay; pins OK.

## موج ۲ / Critique round 2 (experts A / B / C)

### A

1. Wave-5 protocols must be documented as additive, not lock rewrites.

### B

2. Evidence pointer must stay title-honest about BAIC untouched.

### C

3. Attach without prereg would break ClaimGate norms.

### Fixes (round 2)

- `wave5_does_not_invalidate_he_hp=True` on payload.
- Evidence note updated with Wave-6 refresh sentence.
- Prereg required on attach; ladder unchanged.

### Retest (round 2) — sign-off

Phase 25 green; BAIC pins and `engine.py` untouched. A/B/C sign-off for Phase 25.
