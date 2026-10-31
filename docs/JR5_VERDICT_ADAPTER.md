# JR5 verdict adapter (phase 2c)

Module: `codontrace.claimgate.adapters.jr5_verdict`. It is the only code path
that can set `red_queen_proved`. The rules it applies are the ones in
`docs/prereg/jr5/RED_QUEEN_CLAIM_PATH.md` and `PREREG.md` section 2; that
folder is locked, so this note records how the adapter maps onto it.

## Input

`Jr5Evidence.from_dict` takes summary statistics only: intervals, p-values,
estimates, seed counts and replay digests. It refuses unknown keys, any
`red_queen_proved` key and any outcome field. Seed and population counts must
match the prereg (40 E1 populations per sex ratio, 60 paired seeds per
contrast).

- E1 (`e1`): one `E1CostGateResult` per sex ratio at N = 200, filled by the
  phase 3 cost gate: `sex_ratio`, `n_populations`, `n_excluded`, the 90% TOST
  interval and the 95% interval, both on the ratio scale. The adapter does not
  fit or test E1; it only checks those intervals against the bounds.
- E2 (`e2`): the four Holm family tests, each a paired contrast with its
  two-sided t p-value and BCa intervals at the four Holm step levels.
- Condition (c): copassaged minus fixed and copassaged minus frozen replay.
- Condition (d): load (outcross minus self at host mutation 0.05, plus the
  grid trend), frozen minus fixed, tax minus fixed, and the E4 windows.
- Condition (e): one `ReplayCheck` per run and per sealed lock: expected and
  replayed digest, one-shot and resumed body hashes, ATP ledger residual.

## Decision

All thresholds are read from `jr5_prereg_constants.json` after `record.json`
is re-hashed from its files; the evidence must name the same record digest.
Holm is a step-down: tests are ordered by p and stop at the first retained
step. A test counts only when the t test and the BCa interval of its step
agree in direction. An alternative is ruled out only by equivalence (90%
interval inside the margin) or by a 95% interval on the opposite side, never
by a non-significant result. The typed outcome follows PREREG section 2, and
the flag is `True` only when (a) to (e) all hold.

## Claim path

- `assert_claim_allowed` in the host_parasite adapter is unchanged and still
  refuses `red_queen_proved` for every caller.
- `assert_jr5_red_queen_claim_allowed(record, evidence)` recomputes the
  verdict, requires the record to equal it, and requires the flag.
- The auditor ban on `red_queen_proved` stays in `audit_bundle`. It is lifted
  only through `audit_bundle_with_jr5_verdict`, for a bundle whose
  `jr5_verdict` and `jr5_evidence` pass that same check. The auditor itself
  does not import the adapter, so the import contracts are unchanged.

The prereg folder is looked up next to the source tree by default
(`default_prereg_dir()`); pass `prereg_dir` when running elsewhere.
