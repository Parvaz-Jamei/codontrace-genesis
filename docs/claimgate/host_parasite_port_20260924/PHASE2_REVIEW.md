# Phase 2 review — HostParasiteEnv + dual-null

Human research review of the optional host–parasite environment outside the
engine core, plus the dual-null campaign template. Two critique rounds each
name a real defect, the fix, and the retest result.

## What Phase 2 delivers

- `src/codontrace/genesis/host_parasite_env.py` — optional env **outside**
  `engine.py`: task-overlap eligibility, one seat per host, horizontal inject,
  configurable steal fraction (Fortuna et al. 2021 analogy, default 0.8).
- Dual-null template: `content_null`, `structure_null`, `dual_null`, and
  `none`, with `run_dual_null_contrast` proving nulls change outcomes.
- Transmission-mode knob (`horizontal` / `vertical` / `mixed`) with honest
  labeling that vertical components are not implemented as full physics.
- Claim ceiling fixed at `runtime_observation`; `red_queen_proved` stays false
  on snapshots.
- Tests in `tests/test_host_parasite_env.py`.

The Genesis engine tick path is unchanged. This module does not import the
engine and does not certify clinical, CRISPR-identity, or epidemic claims.

## Critique round 1

### Flaws found

1. **Score-only contrast lied under zero steal.** With `steal_fraction=0.0`,
   retained-CPU scores tied across arms even though structure-null blocked
   injection. `nulls_change_outcomes` reported `False`, hiding a real null
   effect.
2. **Empty host task sets were accepted.** A host with no tasks can never be
   infection-eligible; allowing it made “no overlap” failures ambiguous.
3. **`mixed` transmission looked fully implemented.** Horizontal inject
   succeeded under `mixed` with no snapshot note that vertical transmission
   physics are not implemented.

### Fixes

- Contrast now records `injected` / `reasons` and sets
  `nulls_change_outcomes` when either scores or injection flags diverge.
- `add_host` requires at least one task.
- Snapshots declare `vertical_component: not_implemented` for `mixed` and
  `vertical` modes.

### Retest

`pytest tests/test_host_parasite_env.py` — green, including regressions for
zero-steal injection divergence, empty tasks, and mixed-mode labeling.

## Critique round 2

### Flaws found

1. **Host and parasite could share an id.** `try_horizontal_inject` allowed
   `parasite_id == host_id`, collapsing identity in audit records.
2. **No-overlap contrasts silently “proved” nothing.**
   `run_dual_null_contrast` with disjoint task sets produced identical scores
   and `nulls_change_outcomes=False`, which a careless caller could read as
   “nulls are inert” rather than “intact arm never infected.”

### Fixes

- Require `parasite_id != host_id`.
- Fail closed unless the intact arm has task overlap before running the
  contrast.

### Retest

Same pytest file — green, including id-collision and overlap-requirement
tests.

## Honest limits after Phase 2

- Still no executed ClaimGate intervention falsification ladder (Phase 3).
- Vertical / spatial Symbulation physics are knobs and labels only.
- Steal fraction is a digital analogy, not a measured CodonTrace energy map.
- BAIC pins remain untouched; `population/` junk stays untracked.
