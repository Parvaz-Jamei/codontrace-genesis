# Phase 20 review — resource × coevolution-dynamics factorial

Human research review of a Lopez Pascua honesty-map factorial: resource
productivity × parasite present/absent with ARD/FSD-like labels. Knobs outside
`engine.py`. No wet resource–virulence or clinical dosing claim.

## What Phase 20 delivers

- `run_resource_dynamics_factorial` in `host_parasite_resource_dynamics.py`.
- Uses `HostParasiteEnv.resource_productivity` (outside engine).
- Dual-null via biotic-absent cells; falsifies
  `higher_resources_always_increase_fsd_like_labels`.
- `attach_resource_dynamics_factorial` (prereg-bound).
- Tests in `tests/test_host_parasite_phase20.py`.

## Critique round 1

### Flaws found

1. **No resource × dynamics-label factorial** existed despite Lopez Pascua
   comparator rows in Wave 5 brainstorm.
2. **Hypothesis could not fail** if only one resource level were probed.

### Fixes

- Crossed low/high productivity with absent/present parasites.
- Counted FSD-like labels so high-resource increase is falsifiable.

### Retest

Phase 20 green; hypothesis falsified under honesty map; pins untouched.

## Critique round 2

### Flaws found

1. **Wet replication language** risked creeping into attach records.
2. **Missing prereg** would break ClaimGate campaign norms.

### Fixes

- Forced `wet_resource_virulence_proof=False` on payload and attach.
- Preregistration digest required before attach.

### Retest

Phase 20 green; BAIC pins and `engine.py` untouched.
