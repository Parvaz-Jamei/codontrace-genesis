# Phase 21 review — multi-seed contingency / repeatability under parasitism (S1)

Human research review of seed-stratified contingency digests. Success criterion
is digest distinctness / variance report — not “complexity rose.”
``complexity_emergence_proved`` stays False.

## What Phase 21 delivers

- `run_multi_seed_contingency_campaign` in `host_parasite_contingency.py`.
- Parasite-present vs parasite-absent dual-null; contingent seeds can fail to
  raise richness.
- Falsification of `parasites_always_raise_complexity_across_seeds`.
- `attach_multi_seed_contingency` (prereg-bound).
- Tests in `tests/test_host_parasite_phase21.py`.

## Critique round 1

### Flaws found

1. **S1 contingency lacked multi-seed ClaimGate attach** after Zaman freeze/replay.
2. **Success criteria risked being misread as complexity rise.**

### Fixes

- Required ≥3 seeds; seed-stratified digests with cross-seed variance.
- Documented success criterion as distinctness/variance, not complexity rise.

### Retest

Phase 21 green; hypothesis falsified when contingent seeds appear.

## Critique round 2

### Flaws found

1. **Without parasite-absent dual-null**, contingency could be confounded.
2. **`complexity_emergence_proved` could accidentally become True.**

### Fixes

- Dual-null arm always present; attach forces proved flags False.

### Retest

Phase 21 green; BAIC pins and `engine.py` untouched; Zaman not treated as law.
