# Phase 21 review — multi-seed contingency / repeatability under parasitism (S1)

Human research review of seed-stratified contingency digests. Success criterion
is digest distinctness / variance report — not “complexity rose.”
``complexity_emergence_proved`` stays False.

**Experts:** A — digital evolution / ALife · B — microbial / phage honesty ·
C — ClaimGate / V&V / causal methodology.

## What Phase 21 delivers

- `run_multi_seed_contingency_campaign` in `host_parasite_contingency.py`.
- Parasite-present vs parasite-absent dual-null; contingent seeds can fail to
  raise richness.
- Falsification of `parasites_always_raise_complexity_across_seeds`.
- `attach_multi_seed_contingency` (prereg-bound).
- Tests in `tests/test_host_parasite_phase21.py`.

## موج ۱ / Critique round 1 (experts A / B / C)

### A

1. **S1 contingency lacked multi-seed ClaimGate attach** after Zaman
   freeze/replay; freeze proves schedule control, not repeatable complexity
   across seeds.

### B

2. **Success criteria risked being misread as complexity rise**, which would
   overclaim against Scanlan/Buckling humility.

### C

3. `complexity_emergence_proved` must stay False; attach must not raise ladder.

### Fixes (round 1)

- Required ≥3 seeds; seed-stratified digests with cross-seed variance.
- Documented success criterion as distinctness/variance, not complexity rise.
- Forced `complexity_emergence_proved=False` on payload and attach.

### Retest (round 1)

Phase 21 green; hypothesis falsified when contingent seeds appear.

## موج ۲ / Critique round 2 (experts A / B / C)

### A

1. Contingency trigger must reliably appear in multi-seed sets (digest-only
   trigger initially missed seeds 1–5).

### B

2. Without parasite-absent dual-null, contingency could be confounded with
   abiotic flatness.

### C

3. Cross-seed variance should be reported and positive when contingency fires;
   proved flags must remain False at attach.

### Fixes (round 2)

- Contingency mixes digest bit with seed parity so ≥3-seed sets include
  non-rise under parasitism.
- Dual-null arm always present.
- Tests assert contingent seeds, falsified hypothesis, and
  `complexity_emergence_proved is False`; attach forces proved flags False.

### Retest (round 2) — sign-off

Phase 21 green; BAIC pins and `engine.py` untouched; Zaman not treated as law.
A/B/C sign-off: proceed to Phase 22.
