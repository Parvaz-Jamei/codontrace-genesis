# Pearl-pair knockouts and debit-stream capability gates

Revision `xf-wp1-20260926`. Tip baseline for this note is
`610f46f` (`codontrace==0.3.0b10`). Sealed confirmatory seeds 101–108 on
that tip returned an honest FAIL (0/8 separate, 0/8 mixed). Both
`red_queen_proved` and `biological_red_queen_proved` stayed false.
ClaimGate still refuses `red_queen_proved` on the `host_parasite`
profile. The P7 preregistration was not edited after that run.
`engine.py` was not edited.

## Why this note exists

The sealed confirmatory pass rule used passages `coevolve`, `frozen`, and
`absent`. Pearl (Biometrika 82:669–688, 1995, doi:10.1093/biomet/82.4.669)
asks for a pure pair of interventions on the two actuators that matter
here: type-update and match debit. On this stack those cuts already have
names:

- `frozen`: update off, debit on.
- `costless`: debit off, update on.

`absent` removes the antagonist. That is not the same cut as
`do(debit=0)` with the stock still allowed to update. Do not merge
`absent` ≡ `frozen` ≡ `costless` / `zero_debit`.

New campaign cells that need the pure Pearl pair should score knockouts
on `frozen` and `costless`. The sealed 101–108 rule is left untouched so
the negative result stays the record of that preregistration.

## Debit-stream capability gates

Name-set return with a paid match inside the repeat remains the primary
cycle detector (`debit_backed_cycle` in `closed_loop_p6.py`). Optional
gates may only refuse a cycle clause; they cannot invent one:

1. Shewhart in-control on the match-debit series (center ± kσ). Empty
   series or non-positive σ fail closed.
2. One-sided CUSUM onset for naming a debit shift. Empty series or
   non-positive decision interval fail closed. Limits are locked before
   a campaign runs; they are not fitted on confirmatory seeds after the
   fact (Kriegeskorte et al., Nat. Neurosci. 12:535–540, 2009,
   doi:10.1038/nn.2303).
3. Observer residual: predicted Holling type II cost × specificity
   weight versus realized `p6_match_cost` writes. The residual audits
   the ledger; it is not a second population.

All three stay at claim ceiling `runtime_observation`. Passing a gate
does not set `red_queen_proved`.

## Code

Additive module: `src/codontrace/genesis/closed_loop_pearl_spc.py`.
Accept tests: `tests/closed_loop/test_closed_loop_pearl_spc.py`.

Out of scope here: frequency clocks and Slowinski invasion (later
ecology path), graded soft-refit of 101–108, MFA / CRN / R2R / ATP
carryover / queue-timing stacks, infection language in `engine.py`,
loosening ClaimGate.

## Claim posture

| Item | Status |
|---|---|
| Sealed 101–108 | honest FAIL; not reopened |
| `red_queen_proved` | false; not promoted |
| `biological_red_queen_proved` | false |
| ClaimGate refuse | holds |
| Ceiling | `runtime_observation` |
| `absent` vs Pearl pair | documented distinct |
