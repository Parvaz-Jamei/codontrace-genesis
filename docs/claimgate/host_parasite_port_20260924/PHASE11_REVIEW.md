# Phase 11 review — codon-entropy / Hamming dual-null

Human research review of the genotype diversity dual-null assay that can fail
`parasites_always_raise_codon_entropy` under abiotic stress / content-null /
structure-null controls (HE02 honesty; Scanlan/Buckling humility analogue).
Two critique rounds each name a real defect, the fix, and the retest.

## What Phase 11 delivers

- `run_genome_diversity_campaign` in `host_parasite_genome_diversity.py`.
- Arms: `biotic_intact`, `content_null`, `structure_null`, `abiotic_stress`.
- Metrics: `codon_usage_entropy`, `mean_genome_distance`, `unique_genome_count`.
- Identical founder hosts; biotic divergent flips raise entropy; null/stress
  keep clones flat so the universal claim fails.
- `attach_genome_diversity_campaign` (prereg + digest bind); RQ unproved.
- Tests in `tests/test_host_parasite_phase11.py`.

## Critique round 1

### Flaws found

1. **Arm-specific founders made entropy deltas incomparable** (first draft).
   Null/stress looked “positive” only because baselines differed per arm.
2. **Throwaway `GenomeDiversityCampaignResult`** was constructed solely to
   harvest `arm_digests`, duplicating digest logic and risking ceiling drift.

### Fixes

- Shared identical founder clones per seed; biotic arm applies divergent
  per-host flips; null/stress freeze hosts.
- Compute per-arm digests directly from outcome dicts (no throwaway object).

### Retest

`pytest tests/test_host_parasite_phase11.py` — green; biotic mean
`entropy_delta > 0`; null/stress ≤ 0; four distinct arm digests.

## Critique round 2

### Flaws found

1. **Falsified campaigns could attach with an empty `failure_reason`**,
   weakening ClaimGate honesty for the Scanlan-style refusal narrative.
2. **Tests under-asserted Hamming / unique-genome fields** on outcome payloads.

### Fixes

- Attach refuses falsified campaigns without a non-empty `failure_reason`.
- Tests assert `mean_genome_distance`, `unique_genome_count`, and
  `codon_usage_entropy` keys.

### Retest

Phase 11 suite green. BAIC pins unchanged; `engine.py` untouched.

## Honest limits after Phase 11

- Digital humility assay only; not a wet Scanlan/Buckling replication.
- Content/structure nulls are labeled genotype interventions, not wet gene
  knockouts.
- Does not prove Red Queen, gene identity, or major transitions.
