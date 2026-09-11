# Engine replay contract

CodonTrace Genesis keeps Phase A–E default digest pins stable. This note
records the invariants after the first `engine.py` split. It is not a claim
that replay is complete simulation re-execution.

**Claim ceiling:** software capability / `runtime_observation`.

## Module boundaries

| Module | Owns | Must not change without a pin review |
|---|---|---|
| `codontrace.engine_digest` | Spec/result hashing (`_digest`, registry/object hashes) | Canonical JSON separators, key order, float encoding, default action-registry manifest version |
| `codontrace.engine_results` | `GenesisTickResult`, `GenesisSnapshot`, `GenesisRun`, `GenesisRunSummary`, `ConsistencyValidationResult` | `to_dict()` field names and types used in digests |
| `codontrace.engine` | `GenesisEngine`, `GenesisExperimentSpec`, `GenesisRunResult` | Default life-loop run semantics |

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

## What this is not

This contract does not claim a full GENESIS Engine, complete world replay,
or that every user experiment is deterministic unless seeds, configs, and
artifacts are preserved. See [`REPLAY_AND_ARTIFACTS.md`](REPLAY_AND_ARTIFACTS.md)
and [`../REPRODUCIBILITY.md`](../REPRODUCIBILITY.md).
