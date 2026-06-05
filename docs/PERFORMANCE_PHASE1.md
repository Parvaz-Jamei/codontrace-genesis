# Phase 1 Performance Plan

Status: **beta planning document for `0.3.0b1`**.

The goal is to improve live/interactive execution speed without changing features, scientific semantics, replay digests, RNG behavior, evidence schemas, or claim boundaries.

## Safe optimization targets

| Target | Expected effect | Safety rule |
|---|---:|---|
| Separate tick stepping from final artifact building | High for live Studio streams | `run_ticks(n)` must remain backward compatible |
| Build evidence/replay/manifest once at finalization | High | Final digest and schema must match batch execution |
| Avoid repeated source digest walks during live frames | Medium | Cache must be scoped and testable; disable path should exist |
| Return latest `EngineFrame` without full result rebuild | Medium/high | Frame schema and digest must remain stable |
| Reduce repeated `to_dict()` conversions in hot paths | Medium | Serialization tests must pass |

## Baseline profiling command

```bash
python - <<'PY'
import cProfile
import pstats
from codontrace.genesis import GenesisEngine, GenesisExperimentSpec

spec = GenesisExperimentSpec(tick_count=50, seed=7)
with cProfile.Profile() as pr:
    GenesisEngine.from_spec(spec).run_ticks()

pstats.Stats(pr).sort_stats("cumtime").print_stats(30)
PY
```

## Acceptance rules

- No runtime dependency may be added to core for this optimization pass.
- Determinism tests compare batch execution with any new incremental path.
- Performance CI should report data first; avoid fragile absolute-time hard failures.
- Any Studio live adapter must be implemented outside this repository.


## Studio worker ownership

The core performance work must not assume FastAPI owns execution. In the separate `codontrace-studio` repository, synchronous FastAPI `def` path operations are run in an external threadpool, so long-running simulations should be owned by a dedicated worker/queue outside request-handler threads. REST and WebSocket routes should publish state from that worker, not mutate `GenesisEngine` concurrently from arbitrary request handlers.
