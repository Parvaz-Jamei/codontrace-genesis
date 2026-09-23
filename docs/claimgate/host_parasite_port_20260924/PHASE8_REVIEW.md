# Phase 8 review — continuum + VT × spatial factorial

Human research review of the parasitism–mutualism interaction continuum and
the vertical-transmission × spatial-mode factorial. Two critique rounds each
name a real defect, the fix, and the retest.

## What Phase 8 delivers

- `HostParasiteEnv.interaction_value` in [-1, +1] modulating digital
  steal/benefit (default `-1.0` preserves Phase 2 antagonism semantics).
- Snapshot / ClaimGate extras declare `interaction_continuum` with
  `mutualism_equals_success=False`; blocked claims unchanged.
- `run_vt_spatial_factorial` — VT × spatial_mode cells with digests.
- `attach_interaction_continuum` / `attach_vt_spatial_factorial` (prereg
  required for factorial attach).
- Tests in `tests/test_host_parasite_phase8.py`.

## Critique round 1

### Flaws found

1. **Spatial factor was label-only.** Early VT×spatial cells placed H1 next to
   H0 in both modes, so local vs well-mixed digests differed only by the
   `spatial_mode` string while injection counts matched.
2. **Mutualism risked a success narrative** if attach/docs omitted an explicit
   `mutualism_equals_success=False` flag on every continuum payload.

### Fixes

- Shared topology adds `H_far` at Chebyshev distance > 1; local mode blocks
  far inject, well-mixed allows it — injection counts and mean scores diverge.
- Continuum declaration, env snapshot, factorial cells, and attach payloads
  all set `mutualism_equals_success=False`.

### Retest

`pytest tests/test_host_parasite_phase8.py` — green, including
`test_spatial_mode_changes_injection_counts`.

## Critique round 2

### Flaws found

1. **Default interaction_value had to preserve Phase 2 scores.** A default of
   `0.0` (neutral) would have silently broken dual-null and campaign contrasts
   that assume antagonism steal.
2. **Ceiling laundering:** `mechanism_support` (and above) must stay refused on
   the factorial runner.

### Fixes

- Default `interaction_value=-1.0` so `retained = 1 - steal_fraction` under
  default productivity; Phase 2–6 suites remain green.
- Factorial refuses ceilings above `candidate_evidence`; tested.

### Retest

Phase 8 + Phase 2/3/4 host–parasite suites green. BAIC pins unchanged;
`engine.py` untouched; `population/` untracked.

## Honest limits after Phase 8

- Continuum is a digital signed transfer, not a wet symbiosis certificate.
- Mutualism benefit (retained CPU up to 2.0) is not “success,” clearance, or
  therapy validation.
- VT×spatial factorial audits digital protocols; it does not prove Red Queen
  dynamics or major transitions.
