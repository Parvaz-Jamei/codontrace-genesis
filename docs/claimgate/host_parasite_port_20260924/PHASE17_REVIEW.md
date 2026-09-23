# Phase 17 review — Price≠causality refusal assay (S8, earn-in)

Human research review of a digest-backed Price-style caution assay. Okasha
multilevel / Price≠causality literature remains the comparator; major transition
is never proved.

## What Phase 17 delivers

- `run_price_causality_caution_assay` in `host_parasite_price_caution.py`.
- Price-style within/between covariance diagnostic digests.
- Refusal assay: summary present ⇒ `major_transition_proved` and causal flags
  stay False; blocked claim still raises.
- `attach_price_causality_caution` (prereg-bound).
- Tests in `tests/test_host_parasite_phase17.py`.

## Critique round 1

### Flaws found

1. **Worksheet-only multilevel caution** (Phase 3) lacked a digest-backed
   refusal assay reviewers could attach.
2. **Covariance summaries risk being misread as causal proof.**

### Fixes

- Added digest-backed assay with explicit `price_summary_is_causal=False`.
- Attach refuses if major-transition / causal flags are true.

### Retest

Phase 17 green; `major_transition_proved` remains blocked.

## Critique round 2

### Flaws found

1. **Attach without confirming the blocked claim still fails** would be weak.
2. **Missing prereg** would diverge from campaign attach norms.

### Fixes

- Attach re-checks blocked major-transition claim.
- Preregistration digest required.

### Retest

Phase 17 green; BAIC pins and `engine.py` untouched; never proves major transition.
