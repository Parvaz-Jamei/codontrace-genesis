# Life-loop digest migration: historical cause established

Audit base: `639287e` (pushed V4 merge). Probe: life_loop_world, seed 7,
population 6, 12 logical generations. This is a regression audit, not evidence
for Red Queen dynamics or a new scientific discovery.

## What bisect found

The Phase-B commit `3b1191b7ee7c307b1268b6ee8cc4f9f9ce58136f` reproduces the
original snapshot `76a5e62cb0123b20a089adde25acd1cfb6dc460bdfab52f33ee460533d76f43a`.
The first changed commit is
`aadc97062a1a3e03840bc85afb66414e613d559b` (2026-10-09),
“fix(phase3): resolve R09 QD descriptors, population capsule reconciliation,
and manifest chain wiring”. Its immediate parent
`ab81af94a28d29f1c7dfc38956ad3abd314c0350` still reproduces the old trajectory.
No probe revisions were skipped. The run was resumed once after a checkout
collision with untracked audit files; those files were moved to a separate
scratch folder. Both the interruption and successful completion remain in
`life_loop_digest_history/bisect_run.log`; `bisect.log` records the verdicts.

The changed snapshot is
`e9d404a0a50c5ac323a94306d582bd27596a752ecab00bd9406834947d27db78`.
The specification digest stayed
`7d199ae51345872215dbbb0c45cf8f141aacfb4c31d6537eda6de246c0cb7aac`.
This **does not** mean behavior stayed unchanged: engine source revision and
resolved runtime configuration must also accompany a scientific run.

## Mechanism and causal check

`GenesisEngineConfig.enable_capsules` already defaulted to True. The profile
provided `population_configs` with `capsule_transfer=None` and stigmergy False.
Before aadc970, from_spec used this population config verbatim, silently
ignoring the top-level capsule request. The R09 fix resolves the missing
capsule config and enables stigmergy. `step_population` then calls
`read_nexus_capsules`, which charges the configured 0.1 runtime ATP for a read
attempt, including an empty store. It writes `capsule_read_runtime_cost` to
the ATP ledger. Charging an attempted read is existing model behavior, not a
new mutation of the RNG or population identifiers in this commit.

At logical tick index 0, org-0 ends at 17.9 rather than 18.0 ATP. The same
0.1 difference occurs for all six organisms. Downstream state changes are
real: final population clock is 40 rather than 44, and world/population hashes
change. This is not a cosmetic serialization-only migration.

On current code, assigning the original population config to the runner
**only inside a historical counterfactual test**, before any ticks, restores
all 12 original raw tick dictionaries and the complete original snapshot.
Keeping normal reconciliation reproduces all 12 raw dictionaries and the
snapshot from the first changed commit. Identical initial state and matching
first-tick organism IDs further exclude the suggested ID/RNG explanation for
this specific divergence. This does not claim an audit of every RNG path.

## Decision and actual fixes

Keep capsule reconciliation: it is a documented, tested wiring correction,
and reverting it would restore the original ignored-setting defect. Do not
quietly turn capsules off globally or change evolution parameters to force a
historical hash. The pre-migration and current conditions are different model
conditions and must never be pooled without a declared comparison.

V4 correctly matched b28's final snapshot but did not establish the historical
cause and left Phase-B tick pins at the old condition. This patch:

1. Makes the original Phase-A baseline test explicitly historical; its old
   tick and snapshot pins are restored together.
2. Adds separate current-condition tests against archived full raw trajectories
   from both sides of the bisected change; assertions include the ATP mechanism.
3. Fixes misleading reconciliation telemetry: requested_capsules_enabled was
   False despite the resolved engine request being enabled. It now reports the
   resolved top-level request before population overrides. Effective state is
   reported separately. No capsule dynamics or RNG code is changed here.

The legacy runner override is strictly test-only. It is not a supported
production experiment mode and its exported manifest should not be used as a
scientific run artifact. To run a capsule-free experiment, explicitly disable
capsules in the public specification, producing a distinct specification ID.

## Reproduce

From a separate worktree (never a dirty production checkout):

```sh
git bisect start 5e7fefe 3b1191b
PYTHONPATH=src git bisect run python3 /absolute/path/digest_probe.py
git bisect log
git bisect reset
```

The included probe returns 0 for the historical snapshot, 1 for a changed
snapshot and 125 only for incompatible execution. Historical archives contain
raw tick dictionaries, snapshot dictionaries and hashes. They are regression
fixtures, not manually fabricated experimental measurements.

Run targeted checks:

```sh
PYTHONPATH=src python3 -m pytest -o addopts='' -q \
  tests/test_life_loop_digest_history.py \
  tests/test_genesis_phase_b_sexual_recombination.py \
  tests/test_audit_phase3_r09_wiring.py
```
