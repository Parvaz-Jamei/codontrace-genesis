# Phase 16 review — virulence / resistance quality proxies (S7)

Human research review of qualitative vs quantitative digital resistance proxies
with dual-null controls. Challenge S7 (Gandon) is engaged as a literature
comparator; `virulence_optimized_for_humans` stays blocked.

## What Phase 16 delivers

- `run_virulence_resistance_quality_campaign` in `host_parasite_virulence_quality.py`.
- Arms: qualitative resistance gate, quantitative steal gradient, content-null,
  structure-null.
- Hypothesis `any_parasite_always_raises_host_cost` can fail.
- `attach_virulence_resistance_quality` refuses human-virulence unlock.
- Tests in `tests/test_host_parasite_phase16.py`.

## Critique round 1

### Flaws found

1. **ARD/FSD range labels alone did not separate resistance quality**
   (qualitative gate vs graded cost).
2. **Blocked human-virulence claim needed an attach-time refusal check**, not
   only a profile list entry.

### Fixes

- Implemented qualitative seat/overlap gate vs quantitative steal cost.
- Attach asserts `virulence_optimized_for_humans` remains blocked.

### Retest

Phase 16 green; hypothesis falsified under nulls/gate; claim stays blocked.

## Critique round 2

### Flaws found

1. **Without dual-null arms**, a rising cost could look universal.
2. **Prereg attach discipline** could be skipped.

### Fixes

- Content-null and structure-null arms included; distinct arm digests required.
- Attach requires preregistration digest.

### Retest

Phase 16 green; pins and `engine.py` untouched.
