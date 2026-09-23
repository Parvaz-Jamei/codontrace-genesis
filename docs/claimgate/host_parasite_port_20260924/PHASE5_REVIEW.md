# Phase 5 review — spatial structure, vertical/mixed transmission, range diagnostics

Human research review of local-neighborhood inject, real vertical transmission
on host replication, mixed-mode H+V blending, resource-productivity modulation,
and ARD/FSD-like range diagnostics. Two critique rounds each name a real defect,
the fix, and the retest result.

## What Phase 5 delivers

- `spatial_mode="local_neighborhood"` with Chebyshev-neighborhood
  `try_local_inject` (well-mixed still allows any target).
- `replicate_host` with configurable `vertical_transmission_probability`.
- Mixed transmission **actually blends** horizontal inject + vertical
  replication (no `not_implemented` stub for advertised mixed).
- `seed_parasite_seat` setup helper for vertical-only assays.
- `resource_productivity` modulates effective steal impact.
- `diagnose_coevolution_ranges` → `ard_like` / `fsd_like` / `mixed_like` /
  `undeclared` with `red_queen_proved=False` always.
- `attach_coevolution_diagnostics` on host_parasite bundles (no ladder raise).
- Tests in `tests/test_host_parasite_phase5.py` (10 cases) plus updated mixed
  env test.

## Critique round 1

### Flaws found

1. **Monotonic escalation mislabeled `mixed_like`.** Raw standard deviation on
   a steadily climbing infectivity/resistance series is nonzero, so the first
   classifier treated every ARD-like climb as mixed whenever fluctuation
   threshold was met.
2. **Phase 2 mixed-mode test still expected `not_implemented`.** Leaving that
   assertion would greenwash a stub after Phase 5 claimed real blending.

### Fixes

- Fluctuation metric is now **detrended** residual stdev (linear end–start
  trend removed) so pure escalation classifies as `ard_like`.
- Env mixed-mode test rewritten to require successful horizontal inject **and**
  vertical replicate, asserting `vertical_component == "mixed_mode_enabled"`.

### Retest

`pytest tests/test_host_parasite_phase5.py tests/test_host_parasite_env.py` —
green.

## Critique round 2

### Flaws found

1. **Snapshot overclaimed “active” vertical in mixed mode.** Even with
   `vertical_transmission_probability=0` and no replication events, snapshot
   said `mixed_horizontal_and_vertical_active`, implying transmission fired.
2. **Vertical-only campaigns could not seed a parent.** Horizontal inject is
   correctly blocked in vertical-only mode, but without a setup seat helper
   vertical replication could never start.

### Fixes

- Snapshot labels become capability flags:
  `vertical_mode_enabled` / `mixed_mode_enabled`; actual fires live in
  `replication_events`.
- Add `seed_parasite_seat` (setup-only, structure-null still blocks, no claim
  ceiling raise).

### Retest

Full host–parasite suites (Phase 1–5) — all green. BAIC pins unchanged;
`engine.py` untouched; `population/` untracked.

## Honest limits after Phase 5

- ARD/FSD-like labels are digital diagnostics, not Red Queen proofs.
- Local neighborhood is a Chebyshev grid knob, not a wet spatial ecology.
- Vertical transmission is a replication-copy probability, not Symbulation
  physiology or CRISPR identity.
- Public ClaimGate ladder is not raised by diagnostics attach.
