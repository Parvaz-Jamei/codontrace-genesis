# GENESIS Runtime Contract

`BrainStep` means one compiled token/action execution. `GenesisOrganism.step()` keeps this backward-compatible behavior.

`OrganismTick` means a bounded organism-level call that may run multiple token steps through `step_brain_tick()`.

`PopulationTick` means one `step_population()` / `PopulationRunner.step_generation()` cycle over organisms with memory, causal, capsule, and fitness audit records.

`GenesisTick` means one unified `GenesisEngine` orchestration cycle: population tick, optional QD update, snapshot/evidence bookkeeping.

`GenesisRunResult` in `codontrace.genesis.engine` means a multi-tick engine run with manifest, evidence pack, replay bundle, and digestable summary.


## Capsule / EMIT_NEXUS scope

Capsule/Stigmergy runtime integration is active through `PopulationRunner` and `GenesisEngine`. Direct `GenesisOrganism.step()` only applies organism-local effects and does not perform full population-level capsule transfer unless a layer hook is supplied in a future API.

## ADF macro scope

ADF variable-width decoding is operational. ADF tokens are executable through normal action dispatch. Automatic ADF macro expansion is not runtime-native yet; ADF tokens require an action handler or explicit execution policy.
