# HE02 pilot / research status

Product: **CodonTrace Genesis** `0.3.0b4.dev0`.

## What ran here

- Smoke campaign: seeds `(11, 12)`, `tick_count=2`, `population=4`.
- Artifact: [`smoke_v1.json`](smoke_v1.json).
- ClaimGate ceiling: **`runtime_observation`**.
- `assay_failed=True` (manipulation not realized at this micro geometry — honest).
- `decision_rule_passed=False`.

## Deferred (environment too heavy)

- Full pilot seeds `[1000, 1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008, 1009]` at research-capable geometry.
- Research 30-seed campaign → `results_v1.json`.

Do **not** raise ClaimGate. Do **not** invent cleared pilot/research results.
When runnable locally/CI-nightly, commit `pilot_v1.json` / `results_v1.json`
only after manipulation checks and decision rule are evaluated honestly.

Pins A–E unchanged. Forbidden claim aliases unchanged.
