# Phase 22 review — sequential Cornish multi-intervention deepening

Human research review of an ordered observational→intervention schedule.
Observational match alone never grants ``intervention_supported``. Not clinical
decision support.

## What Phase 22 delivers

- `run_sequential_cornish_campaign` in `host_parasite_cornish_sequential.py`.
- Ordered schedule with observational baseline first; ≥1 intervention.
- Cornish refusal: `intervention_supported=False` even when observational match
  and later interventions execute.
- `attach_sequential_cornish_campaign` (prereg digest must match bundle).
- Tests in `tests/test_host_parasite_phase22.py`.

## Critique round 1

### Flaws found

1. **Phase 9 Cornish pack was a two-arm sketch**, not a sequential
   multi-intervention falsification suite.
2. **Observational-first ordering was not enforced**, risking schedule theater.

### Fixes

- Default four-step ordered schedule; observational must be step 0.
- Step digests pairwise distinct; interventions recorded as executed without
  unlocking support.

### Retest

Phase 22 green; `intervention_supported` stays False.

## Critique round 2

### Flaws found

1. **Attach without matching prereg digests** could desync campaign from bundle.
2. **Clinical decision-support language** risked creeping into attach records.

### Fixes

- Attach requires campaign prereg digest == bundle prereg digest.
- Forced `clinical_decision_support=False` on payload and attach.

### Retest

Phase 22 green; BAIC pins and `engine.py` untouched; Cornish rule held.
