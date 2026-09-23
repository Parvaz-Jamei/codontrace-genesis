# Phase 3 review — intervention falsification + claim ladder honesty

Human research review of digital intervention falsification hooks, the
multilevel transition worksheet gate, and optional ARD/FSD dynamics labels.
Two critique rounds each name a real defect, the fix, and the retest result.

## What Phase 3 delivers

- `run_intervention_falsification` — digital hooks against `HostParasiteEnv`
  (`remove_parasites`, content-null, structure-null, steal-fraction ablation,
  abiotic-only). Pass/fail reports stay at claim ceiling
  `runtime_observation` and never grant `intervention_supported`.
- `multilevel_transition_worksheet` + `assert_transition_claim_allowed` —
  Michod / Okasha caution: readiness documentation never unlocks transition
  claim language; proved aliases stay blocked.
- `declared_dynamics_labels` — optional `ard_candidate` / `fsd_candidate` /
  `ard_fsd_mixed_candidate` labels with `red_queen_proved` fixed false.
- `attach_phase3_honesty` — attaches falsification / worksheet / dynamics
  records to a host_parasite bundle without raising the public ladder.
- Tests in `tests/test_claimgate_host_parasite_phase3.py`.

## Critique round 1

### Flaws found

1. **Cleared worksheet unlocked soft transition strings.** After documenting
   multilevel readiness, `assert_transition_claim_allowed("major_transition")`
   succeeded. That treats a worksheet as a claim grant — the opposite of the
   honesty goal.
2. **Falsification without overlap silently assay-invalid.** Disjoint host /
   parasite tasks produced identical scores and a failed pass without telling
   the caller the control arm never infected.

### Fixes

- Transition aliases (including soft forms) stay blocked regardless of
  readiness; `transition_claim_allowed` is always false in the public dict;
  readiness is reported separately as `readiness_documented`.
- Require task overlap before running falsification so the control arm can
  infect.

### Retest

`pytest tests/test_claimgate_host_parasite_phase3.py` — green, including
readiness-without-unlock and overlap-requirement regressions.

## Critique round 2

### Flaws found

1. **No-op attach.** `attach_phase3_honesty(bundle)` with no records succeeded
   and returned an unchanged-looking bundle, inviting empty “honesty”
   attachments.
2. **Soft transition requests did not dirty readiness.** Asking for
   `requested_transition_claim="major_transition"` left
   `readiness_documented=True` when measurement flags were set, because only
   `*_proved` aliases were treated as blocking requests.

### Fixes

- Require at least one of falsification / worksheet / dynamics on attach.
- Treat soft transition aliases as blocking requests that open a
  `blocked_claim:` gap and clear readiness.

### Retest

Same pytest file plus Phase 1/2 suites — all green.

## Honest limits after Phase 3

- Digital falsification pass ≠ `intervention_supported` on the public ladder.
- ARD/FSD labels are candidates only; Red Queen is not proved.
- Multilevel readiness is not a major-transition certificate.
- Engine infection physics remain absent; BAIC pins untouched;
  `population/` junk untracked.
