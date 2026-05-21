# Benchmark Scenario Suite

CodonTrace benchmark scenarios are library objects used to create reproducible experiment specs, not an app workflow. The suite gives researchers fixed baseline/treatment definitions for comparing runs under the same seed policy, replay policy, and claim ceiling.

## What it implements

`BenchmarkScenarioSuite.standard()` returns the v2 scientific suite. It includes sanity worlds, static and deceptive resource worlds, novelty-required worlds, variable-genome and ADF usefulness scenarios, known causal worlds, capsule-transfer worlds, environmental-shift translation worlds, and multi-agent stigmergy worlds. Each `BenchmarkScenarioSpec` records:

- `scenario_id`
- purpose and expected signal
- baseline and treatment config digests
- required metrics
- minimum seed policy
- claim ceiling

## What it does not claim

A passing benchmark run is not proof of artificial life, open-ended evolution, semantic closure, or full GENESIS. Benchmark results are evidence objects for ClaimGate. Strong claims still require multi-seed execution, statistical policy, replay verification, ablation/control runs, and review.

## Runtime hooks

Benchmark specs are consumed by Python APIs such as `GenesisEngine.from_spec`, `MultiSeedExperimentRunner`, statistical reports, and ClaimGate. They do not start background jobs, write databases, or create UI state.

## Artifacts and manifest fields

Scientific manifests should include `benchmark_scenario_digest` and protocol status fields. If a benchmark is not run, status must remain `not_run`; a placeholder digest is schema completeness, not evidence.

## Tests

The suite is covered by benchmark scenario existence, valid spec generation, known capsule transfer scenario, and claim-ceiling tests.
