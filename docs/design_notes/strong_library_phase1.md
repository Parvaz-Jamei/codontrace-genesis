# Design Note: Strong Library Phase 1

## Existing modules extended
- `rng.py`
- `genesis/fitness.py`
- `genesis/quality_diversity.py`
- `genesis/qd_search.py`
- `genesis/qd_descriptors.py`
- `genesis/benchmark_suite.py`
- `genesis/ribosome.py`
- `genesis/organism.py`
- `genesis/artifacts.py`
- `genesis/claim_gate.py`

## New modules added, if any
None. Phase 1 intentionally upgrades existing modules instead of creating a parallel architecture.

## Scientific source / pattern used
- MAP-Elites / Quality-Diversity: ask/evaluate/tell candidate flow, descriptor schemas, archive feedback.
- Reproducible simulation/artifact review: source digest, RNG backend metadata, replay-critical digest factories.
- Continuous fitness: raw/normalized/weighted components with explicit reward/penalty polarity.

## What this PR implements
- RNGProtocol with default RNGManager backend and optional lazy NumPy backend.
- Continuous fitness component values and scorer config.
- QDCandidate plus QDAsk/QDEvaluate/QDTell contracts.
- DescriptorSchema factory/import validation.
- BenchmarkScenarioSuite v2 specs.
- BrainTokenSource and CodonExecutionRecord source map, gated off by default.
- Phase-1 manifest fields and source digest.
- Phase-1 ClaimGate labels.
- Release hygiene test.

## What this PR intentionally does not implement
- Variable genome structural mutation.
- ContributionLedger / descendant credit.
- EventGraph migration.
- Granger/PCMCI/DoWhy causal adapters.
- OEE long-horizon thresholds.
- UI, server, background jobs, or LLM hot-loop control.

## Allowed claim
CodonTrace has a stronger scientific-library foundation with normalized continuous fitness, active-QD-ready candidate architecture, deterministic RNG/replay metadata, benchmark scenario specs, and source-mapped execution traces.

## Rejected claim
This PR does not prove artificial life, semantic closure, unbounded open-ended evolution, causal intelligence, or a full GENESIS engine.

## Replay / manifest / artifact fields added
- `source_digest`
- `rng_backend_kind`
- `rng_namespace`
- `rng_draw_count`
- `rng_state_digest`
- `seed_schedule_digest`
- `protocol_version`
- `fitness_config_hash`
- `descriptor_schema_hash`
- `archive_digest`
- `qd_scheduler_digest`
- `benchmark_scenario_digest`
- `execution_source_digest`
- `claim_gate_decision_digest`

## Tests added
- `tests/science_gates/test_strong_library_phase1_fitness_qd_rng.py`
- `tests/science_gates/test_strong_library_phase1_descriptor_benchmark_manifest.py`
- `tests/science_gates/test_strong_library_phase1_source_map.py`
- `tests/release/test_release_artifact_has_no_cache_files.py`

## Backward compatibility impact
Existing defaults remain library-only and backward-compatible. Source-map tracing is disabled by default. QD candidate objects add future-compatible API without removing the older QD search candidate helper.
