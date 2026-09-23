# Phase 20 review — resource × coevolution-dynamics factorial

Human research review of a Lopez Pascua honesty-map factorial: resource
productivity × parasite present/absent with ARD/FSD-like labels. Knobs outside
`engine.py`. No wet resource–virulence or clinical dosing claim.

**Experts:** A — digital evolution / ALife · B — microbial / phage honesty ·
C — ClaimGate / V&V / causal methodology.

## What Phase 20 delivers

- `run_resource_dynamics_factorial` in `host_parasite_resource_dynamics.py`.
- Uses `HostParasiteEnv.resource_productivity` (outside engine).
- Dual-null via biotic-absent cells; falsifies
  `higher_resources_always_increase_fsd_like_labels`.
- `attach_resource_dynamics_factorial` (prereg-bound).
- Tests in `tests/test_host_parasite_phase20.py`.

## موج ۱ / Critique round 1 (experts A / B / C)

### A

1. **No resource × dynamics-label factorial** existed despite Lopez Pascua
   comparator rows in Wave 5 brainstorm; continuum/factorial packs did not
   cross productivity with ARD/FSD labels.

### B

2. Literature often finds **higher resources decrease FSD-like dynamics**; a
   digital assay that cannot fail “higher resources always increase FSD” is
   theater.

### C

3. Knobs must stay **outside `engine.py`**; no clinical dosing language.

### Fixes (round 1)

- Crossed low/high `resource_productivity` with absent/present parasites.
- Counted FSD-like labels so high-resource increase is falsifiable.
- Env probe uses existing outside-engine productivity knob.

### Retest (round 1)

Phase 20 green; hypothesis falsified under honesty map; pins untouched.

## موج ۲ / Critique round 2 (experts A / B / C)

### A

1. Cells must be pairwise-distinct for ClaimGate attach under
   `candidate_evidence`.

### B

2. **Wet replication language** risked creeping into attach records.

### C

3. Missing prereg would break ClaimGate campaign norms; ladder must not rise.

### Fixes (round 2)

- Distinct cell digests required for attach / candidate_evidence.
- Forced `wet_resource_virulence_proof=False` on payload and attach.
- Preregistration digest required; ladder audit asserted stable.

### Retest (round 2) — sign-off

Phase 20 green; BAIC pins and `engine.py` untouched.
A/B/C sign-off: proceed to Phase 21.
