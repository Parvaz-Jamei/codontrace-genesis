# Phase 15 review — genome × VT × spatial × continuum factorial

Human research review of the Wave-2 × Wave-3 cross factorial that places
SemanticGenome digests on every VT × spatial × interaction-value cell. Two
critique rounds each name a real defect, the fix, and the retest.

## What Phase 15 delivers

- `run_genome_vt_spatial_continuum_factorial` in `host_parasite_genome_factorial.py`.
- Per-cell host and parasite genome digests plus continuum score.
- Pairwise-distinct cell digests required for `candidate_evidence`.
- Mutualism never equals success; Red Queen / major transition unproved.
- `attach_genome_vt_spatial_continuum_factorial` (prereg-bound).
- Tests in `tests/test_host_parasite_phase15.py`.

## Critique round 1

### Flaws found

1. **Wave-2 continuum and Wave-3 genomes were siloed**, so reviewers could not
   see genotype digests under VT/spatial/continuum knobs.
2. **Mutualism risked being narrated as success** if only score rose.

### Fixes

- Crossed VT × spatial × interaction_value with host/parasite genome digests.
- Forced `mutualism_equals_success=False` on cells and attach payload.

### Retest

Phase 15 suite green; eight distinct cell digests on the default grid.

## Critique round 2

### Flaws found

1. **Attach without preregistration** would break Wave-3 discipline.
2. **High claim ceilings** could be requested without digest contrast.

### Fixes

- Attach requires prereg digest; refuses already-attached and proved flags.
- `candidate_evidence` refused unless cell digests are pairwise distinct.

### Retest

Phase 15 green; BAIC pins unchanged; `engine.py` untouched; one profile.
