# Phase 7 review — Zaman freeze / replay / reciprocal

Human research review of the three-arm Zaman digital analogue (freeze ≠
replay ≠ reciprocal), host repertoire-richness trajectories, and ClaimGate
attach honesty. Two critique rounds each name a real defect, the fix, and
the retest.

## What Phase 7 delivers

- `run_zaman_three_arm_campaign` in `host_parasite_zaman.py` with arms
  `freeze_parasites`, `replay_parasite_schedule`, `reciprocal_coevolution`.
- Host repertoire-richness analogue: task-set cardinality trajectory,
  `final_richness`, per-arm and campaign digests.
- `attach_zaman_campaign` (prereg required); `complexity_emergence_proved`
  and `red_queen_proved` always False; ceiling max `candidate_evidence`.
- Tests in `tests/test_host_parasite_phase7.py`.
- Phase 4 `CAMPAIGN_ARMS` / collapsed `freeze_replay_parasites` left intact.

## Critique round 1

### Flaws found

1. **Private coupling to Phase 4 helpers.** The first draft imported
   `_ensure_overlap`, `_mean`, `_tasks_for_seed`, and related private names
   from `host_parasite_campaign`, so a campaign refactor could silently break
   Zaman digests.
2. **Freeze and reciprocal richness collapsed.** Both arms used the same
   single-task expansion budget, so mean final richness matched even when
   digests differed — too weak for a Zaman-style “reciprocal > freeze”
   repertoire contrast.

### Fixes

- Local helpers live inside `host_parasite_zaman.py` (no private campaign
  imports).
- `_host_expand(..., expansion_budget=...)`: freeze uses budget 1; reciprocal
  uses budget 2; replay schedule keeps `under_parasite_pressure=False` so
  cardinality stays flat.

### Retest

`pytest tests/test_host_parasite_phase7.py` — green; richness order
replay < freeze ≤ reciprocal on seed 3 / steps 4.

## Critique round 2

### Flaws found

1. **`candidate_evidence` could be granted on a single arm.** With only one
   Zaman arm, `arms_are_distinct` was False but the refusal path needed an
   explicit test so ceilings cannot launder from a lone freeze arm.
2. **Attach without preregistration** would have mirrored the Phase 6 campaign
   hole if Zaman attach skipped the prereg gate.

### Fixes

- `candidate_evidence` refused unless arm digests are pairwise distinct
  (tested with single-arm request).
- `attach_zaman_campaign` calls
  `require_preregistration_before_campaign_attach` and refuses overwrite /
  complexity-proved flags.

### Retest

Phase 7 suite green; Phase 1–6 host–parasite suites remain green. BAIC pins
unchanged; `engine.py` untouched; `population/` untracked.

## Honest limits after Phase 7

- Digital freeze/replay/reciprocal analogues only; not a wet replication of
  Zaman et al. 2014 and not a complexity-emergence proof.
- Repertoire richness is task-set cardinality, not genomic complexity.
- ClaimGate attach does not raise the public ladder above the campaign
  ceiling.
