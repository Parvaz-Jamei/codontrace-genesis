# Phase 23 review — Scanlan mutator / abiotic-constraint dual-null (earn-in)

Human research review of a genome-layer mutation-rate factorial under
coevolution vs abiotic arms. Scanlan et al. 2015 honesty map: coevolution can
constrain abiotic-beneficial acquisition. ``gene_identity_proved`` and CRISPR
identity stay False. Shipped only after Phases 18–22 were green.

## What Phase 23 delivers

- `run_scanlan_mutator_campaign` in `host_parasite_mutator.py`.
- Four arms: coevolution elevated / baseline mutation, abiotic elevated,
  content-null elevated.
- Falsification of `elevated_mutation_under_coevolution_always_improves_abiotic`.
- `attach_scanlan_mutator_campaign` (prereg-bound; CRISPR block re-checked).
- Tests in `tests/test_host_parasite_phase23.py`.

## Critique round 1

### Flaws found

1. **Phases 11/15 did not falsify mutator-driven abiotic constraint.**
2. **Elevated mutation without an abiotic contrast arm** could not isolate
   Scanlan-style constraint.

### Fixes

- Added coevolution-elevated vs abiotic-elevated contrast on abiotic fitness.
- Content-null elevated dual-null keeps content theater out.

### Retest

Phase 23 green; hypothesis falsified when coevolution elevated fitness < abiotic
elevated fitness.

## Critique round 2

### Flaws found

1. **Wet mutator-gene / CRISPR identity language** risked attach creep.
2. **Missing prereg** would break ClaimGate norms.

### Fixes

- Forced `gene_identity_proved=False`, `crispr_identity_proved=False`,
  `wet_mutator_gene_identity=False`; attach re-checks CRISPR block.
- Preregistration digest required.

### Retest

Phase 23 green; BAIC pins and `engine.py` untouched; no CRISPR/gene identity.
