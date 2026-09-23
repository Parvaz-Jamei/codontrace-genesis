# Phase 9 review — evolvability, Cornish, comparator, HE_HP

Human research review of the evolvability falsification assay, Cornish
observational-vs-interventional campaign, comparator matrix, and locked
HARD_EXPERIMENT_HP digests. Two critique rounds each name a real defect,
the fix, and the retest.

## What Phase 9 delivers

- `run_evolvability_falsification` — can *fail*
  `parasites_always_raise_host_repertoire` under abiotic stress.
- `run_cornish_intervention_campaign` + `attach_cornish_campaign` —
  observational match never grants `intervention_supported`.
- `COMPARATOR_MATRIX.md` — Avida / Symbulation / CRISPR-phage literature as
  comparison ≠ identity.
- `docs/hard_experiment_hp/locked_campaign_digests.json` — additive locked
  digests (BAIC pins untouched).
- Tests in `tests/test_host_parasite_phase9.py`.

## Critique round 1

### Flaws found

1. **Expansion budget was hard-coded to 0 on stress arms**, parallel to the
   productivity argument, so abiotic stress was not the actual driver of
   falsification — a silent label/behavior split.
2. **Unused `banned` variable** in the comparator test (lint / dead intent).

### Fixes

- Budget rule: `1` iff `productivity >= 0.5 * mild_productivity`, else `0`;
  stress productivity therefore collapses expansion.
- Comparator test asserts the “not claimed” phrases appear in the matrix
  text; ruff import order fixed.

### Retest

`pytest tests/test_host_parasite_phase9.py` — green; locked digests replay.

## Critique round 2

### Flaws found

1. **Cornish attach must bind prereg digest.** Without matching
   `preregistration_digest` to the bundle prereg record, a campaign could be
   attached under the wrong QOI/COU.
2. **Observational-only packs** needed an explicit path proving
   `observational_match=True` still yields `intervention_supported=False`
   (Cornish core refusal).

### Fixes

- `attach_cornish_campaign` requires prereg on the bundle and equality of
  digests; refuses any `intervention_supported=True` payload.
- Tests cover observational-only and intervention-executed packs; both keep
  `intervention_supported=False`.

### Retest

Full host–parasite Phase 1–9 suites green. BAIC pins unchanged; `engine.py`
untouched; `population/` untracked.

## Honest limits after Phase 9

- Evolvability falsification is a digital humility assay, not a wet
  Scanlan/Buckling replication.
- Cornish refusal is ClaimGate protocol honesty, not a causal proof engine.
- Comparator matrix rows are literature comparators only.
- HE_HP digests are additive replay locks; they do not edit BAIC pins.
