# Engine replay contract

CodonTrace Genesis keeps Phase A–E default digest pins stable. This note
records the invariants after the first `engine.py` split. It is not a claim
that replay is complete simulation re-execution.

**Claim ceiling:** software capability / `runtime_observation`.

## Module boundaries

| Module | Owns | Must not change without a pin review |
|---|---|---|
| `codontrace.engine_digest` | Spec/result hashing (`_digest`, registry/object hashes) | Canonical JSON separators, key order, float encoding, default action-registry manifest version |
| `codontrace.engine_results` | `GenesisTickResult`, `GenesisSnapshot`, `GenesisRun`, `GenesisRunSummary`, `ConsistencyValidationResult`, `ExogenousInputRecord` | `to_dict()` field names and types used in digests |
| `codontrace.engine_spec` | `GenesisEngineConfig`, `GenesisExperimentSpec`, `GenerationBoundaryObserver`, `GenerationInputProvider` | Spec `to_dict()` field names used in digests |
| `codontrace.engine_runtime` | `GenesisEngine` orchestrator (+ `_effective_evolution_config`, `_default_qd_archive`) | Default life-loop run semantics; observer and input-provider call sites are domain-free |
| `codontrace.engine_run_result` | `GenesisRunResult` evidence / maturity surface | Result `to_dict()` / digest payload |
| `codontrace.engine_claims` | Claim ladder, protocol statuses, review attach, phase2 hashes | ClaimGate honesty; no soft-pass labels in helpers |
| `codontrace.engine` | Thin facade re-exports only | Public import surface / `__all__` |

Historical imports (`from codontrace.engine import …` and
`from codontrace.genesis.engine import …`) stay valid. The split is a
boundary, not a new public API family.

## Invariants

1. **Same spec, same digest.** `GenesisExperimentSpec.to_dict()` is hashed
   with `engine_digest._digest`. Default
   `life_loop_world(seed=7, tick_count=12, population=6)` stays
   `7d199ae51345872215dbbb0c45cf8f141aacfb4c31d6537eda6de246c0cb7aac`.
2. **Same run, same result digest.** Two `GenesisEngine.from_spec(spec).run_ticks()`
   calls with that pinned spec must match each other. The snapshot digest
   stays `76a5e62cb0123b20a089adde25acd1cfb6dc460bdfab52f33ee460533d76f43a`.
3. **Opt-in overlays must not alias the pin.** Hard experiment 01 and Phase
   E–K helpers build *new* specs. They must not mutate the default life-loop
   metadata or population configs used by the pin.
4. **Replay verification is independent re-execution.** Matching a digest
   against the same in-memory object is not replay. Hard experiment 01
   re-runs the treatment arm on the first seed and compares spec/result
   digests.
5. **ClaimGate stays outside the hasher.** Digests record artifacts.
   `ScientificClaimGate` assigns labels. Hash helpers must not write
   `intelligence`, `collective_intelligence`, `agi`,
   `tokyo_type1_passed`, or `avida_replacement`.
6. **Exogenous inputs are recorded world events.** An optional
   `GenerationInputProvider` (`GenesisEngine.from_spec(...,
   generation_input_provider=...)`) is called before each `step_generation`
   with the generation index and a disposable clone of the world. Its
   `WorldEvent`s are validated on a second clone, then applied to the live
   world through `World2D.apply_world_event`; if the provider raises or an
   event cannot be applied, the generation fails with the world, tick results
   and records unchanged. Only types that change the world are accepted
   (resource, wall, custom-cell and object events with a position). Each
   generation that received events gets an `ExogenousInputRecord` with the
   world digests before and after, available as
   `GenesisEngine.exogenous_inputs` and `GenesisRunResult.exogenous_inputs`.
   The provider is not part of the spec, so the spec digest does not change.
7. **No provider, no new fields.** Without a provider, or with one that
   returns no events, `exogenous_inputs` is empty and is omitted from
   `GenesisRunResult.to_dict()`, so every pin above is unchanged. When
   present it is part of the result digest.
8. **Recorded inputs replay without the source.**
   `codontrace.replay.RecordedInputProvider.from_records(records)` feeds the
   recorded events back (records or their `to_dict()` form). It checks the
   offered world against `world_digest_before` and raises `ReplayError` on a
   mismatch. A live run and its recorded replay give equal spec, result,
   snapshot and world digests. Randomness in a live provider is the
   provider's concern and should come from `RNGManager`, like any other.

## What this is not

This contract does not claim a full GENESIS Engine, complete world replay,
or that every user experiment is deterministic unless seeds, configs, and
artifacts are preserved. See [`REPLAY_AND_ARTIFACTS.md`](REPLAY_AND_ARTIFACTS.md)
and [`../REPRODUCIBILITY.md`](../REPRODUCIBILITY.md).
