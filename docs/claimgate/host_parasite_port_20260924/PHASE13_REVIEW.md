# Phase 13 review — declared task–gene map digests (earn-in)

Optional earn-in after Phases 10–12. Declared codon-window → task-label map
digests bridge repertoire labels to genomes without claiming gene identity.
Two critique rounds each name a real defect, the fix, and the retest.

## What Phase 13 delivers

- `build_task_gene_map` in `host_parasite_task_gene.py`.
- Non-overlapping declared windows with per-window digests + `map_digest`.
- `gene_identity_proved` / `crispr_identity_proved` / `major_transition_proved`
  always False.
- `attach_task_gene_map` (prereg + digest bind).
- Tests in `tests/test_host_parasite_phase13.py`.

## Critique round 1

### Flaws found

1. **Attach accepted an empty window list / empty `map_digest`** in principle,
   which would attach a vacuous phenotype link.

### Fixes

- Attach refuses empty `windows` and empty `map_digest`.

### Retest

Phase 13 suite green; maps with default length yield ≥2 uniquely labeled windows.

## Critique round 2

### Flaws found

1. **Builder could theoretically yield zero windows** for pathological
   `window_width` / `genome_length` combinations without a clear error.

### Fixes

- `build_task_gene_map` raises if `max_windows < 1`.

### Retest

Phase 13 suite green. BAIC pins unchanged; `engine.py` untouched.

## Honest limits after Phase 13

- Declared digital phenotype link only — not gene identity, wet loci, CRISPR
  genetics, or major-transition proof.
