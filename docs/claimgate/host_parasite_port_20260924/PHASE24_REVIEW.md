# Phase 24 review — Wave 6 journal packet integration smoke

Human research review of a one-bundle ClaimGate attach smoke covering Phases
18–23. Soft-complete inventory hygiene: ladder must not rise; representative
blocked claims stay fail-closed. No new biology claims.

**Experts:** A — digital evolution / ALife · B — microbial / phage honesty ·
C — ClaimGate / V&V / causal methodology.

## What Phase 24 delivers

- `run_wave6_journal_smoke` in `host_parasite_wave6_smoke.py`.
- Ordered attach of Phases 18–23 digests on one prereg-bound bundle.
- Ladder audit + blocked-claim spot check.
- `attach_wave6_journal_smoke` (prereg-bound; Red Queen block re-checked).
- Tests in `tests/test_host_parasite_phase24.py`.

## موج ۱ / Critique round 1 (experts A / B / C)

### A

1. Soft-complete was per-phase; reviewers lacked a single attach-order smoke.

### B

2. Therapy / CRISPR blocked claims must be re-checked on the integration path.

### C

3. Ladder rise during multi-attach would invalidate soft-complete.

### Fixes (round 1)

- Ordered ATTACH_ORDER smoke with Wave-5 wiring assert.
- Spot-check blocked matrix claims including phage therapy and CRISPR identity.
- Fail closed if ladder_before != ladder_after.

### Retest (round 1)

Phase 24 green; six digests attached; ladder unchanged.

## موج ۲ / Critique round 2 (experts A / B / C)

### A

1. Smoke must not silently rewrite Phase-18 Phases 1–17 soft_complete contract.

### B

2. Honesty flags (complexity emergence, intervention, gene identity) must stay False.

### C

3. Missing prereg or double-attach would break ClaimGate norms.

### Fixes (round 2)

- Reuses Phase-18 registry packet unchanged; WAVE6 keys are additive.
- Forced False on complexity / intervention / gene-identity / Red Queen flags.
- Prereg required; already-attached refused.

### Retest (round 2) — sign-off

Phase 24 green; BAIC pins and `engine.py` untouched. A/B/C sign-off for Phase 24.
