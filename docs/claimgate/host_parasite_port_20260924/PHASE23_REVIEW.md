# Phase 23 review — Scanlan mutator / abiotic-constraint dual-null (earn-in)

Human research review of a genome-layer mutation-rate factorial under
coevolution vs abiotic arms. Scanlan et al. 2015 honesty map: coevolution can
constrain abiotic-beneficial acquisition. ``gene_identity_proved`` and CRISPR
identity stay False. Shipped only after Phases 18–22 were green with two
critique waves each.

**Experts:** A — digital evolution / ALife · B — microbial / phage honesty ·
C — ClaimGate / V&V / causal methodology.

## What Phase 23 delivers

- `run_scanlan_mutator_campaign` in `host_parasite_mutator.py`.
- Four arms: coevolution elevated / baseline mutation, abiotic elevated,
  content-null elevated.
- Falsification of `elevated_mutation_under_coevolution_always_improves_abiotic`.
- `attach_scanlan_mutator_campaign` (prereg-bound; CRISPR block re-checked).
- Tests in `tests/test_host_parasite_phase23.py`.

## موج ۱ / Critique round 1 (experts A / B / C)

### A

1. **Phases 11/15 did not falsify mutator-driven abiotic constraint**; entropy
   dual-null ≠ Scanlan mutator honesty map.

### B

2. Elevated mutation without an abiotic contrast arm cannot isolate
   coevolution-constrained abiotic acquisition (Scanlan 2015).

### C

3. Earn-in only after 18–22 solid; gene identity / CRISPR must stay False /
   blocked.

### Fixes (round 1)

- Added coevolution-elevated vs abiotic-elevated contrast on abiotic fitness.
- Content-null elevated dual-null keeps content theater out.
- Forced `gene_identity_proved=False` and CRISPR flags False.

### Retest (round 1)

Phase 23 green; hypothesis falsified when coevolution elevated fitness < abiotic
elevated fitness.

## موج ۲ / Critique round 2 (experts A / B / C)

### A

1. Arm digests must be pairwise distinct under `candidate_evidence`.

### B

2. Wet mutator-gene identity language risked attach creep.

### C

3. Missing prereg would break ClaimGate norms; attach must re-check CRISPR
   block.

### Fixes (round 2)

- Distinct arm digests required for attach / candidate_evidence.
- Forced `wet_mutator_gene_identity=False` on payload and attach.
- Preregistration digest required; attach re-checks `crispr_identity_proved`.

### Retest (round 2) — sign-off

Phase 23 green; BAIC pins and `engine.py` untouched; no CRISPR/gene identity.
A/B/C sign-off: Wave 5 Phases 18–23 complete.
