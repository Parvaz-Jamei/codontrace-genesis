# Phase 22 review — sequential Cornish multi-intervention deepening

Human research review of an ordered observational→intervention schedule.
Observational match alone never grants ``intervention_supported``. Not clinical
decision support.

**Experts:** A — digital evolution / ALife · B — microbial / phage honesty ·
C — ClaimGate / V&V / causal methodology.

## What Phase 22 delivers

- `run_sequential_cornish_campaign` in `host_parasite_cornish_sequential.py`.
- Ordered schedule with observational baseline first; ≥1 intervention.
- Cornish refusal: `intervention_supported=False` even when observational match
  and later interventions execute.
- `attach_sequential_cornish_campaign` (prereg digest must match bundle).
- Tests in `tests/test_host_parasite_phase22.py`.

## موج ۱ / Critique round 1 (experts A / B / C)

### A

1. **Phase 9 Cornish pack was a two-arm sketch**, not a sequential
   multi-intervention falsification suite reviewers can schedule.

### B

2. Digital intervention kinds must stay on the declared menu vocabulary; no
   wet clinical protocol cosplay.

### C

3. Observational-first ordering was not enforced, risking schedule theater;
   observational match must never unlock `intervention_supported`.

### Fixes (round 1)

- Default four-step ordered schedule; observational must be step 0.
- Step digests pairwise distinct; interventions recorded as executed without
  unlocking support.
- Hard `intervention_supported=False` in result and attach.

### Retest (round 1)

Phase 22 green; `intervention_supported` stays False.

## موج ۲ / Critique round 2 (experts A / B / C)

### A

1. Schedule without an intervention step should fail closed.

### B

2. Clinical decision-support language risked creeping into attach records.

### C

3. Attach without matching prereg digests could desync campaign from bundle.

### Fixes (round 2)

- Parser requires observational first + ≥1 intervention.
- Forced `clinical_decision_support=False` on payload and attach.
- Attach requires campaign prereg digest == bundle prereg digest.

### Retest (round 2) — sign-off

Phase 22 green; BAIC pins and `engine.py` untouched; Cornish rule held.
A/B/C sign-off: Phase 22 solid; Phase 23 earn-in allowed.
