# GENESIS API for UI

UI clients should start from `GenesisExperimentSpec` and `GenesisEngine`:

```python
from codontrace.genesis.engine import GenesisEngine, GenesisExperimentSpec

engine = GenesisEngine.from_spec(GenesisExperimentSpec(tick_count=10))
result = engine.run_ticks()
snapshot = engine.snapshot()
evidence = engine.export_evidence_pack()
replay = engine.export_replay_bundle()
```

The UI should not manually mutate organism/world internals. It should consume snapshots, manifest digests, evidence packs, review requests, and replay bundles.


## Phase 3 polish hooks

`GenesisExperimentSpec` can accept custom `Ribosome`, `CodonTable`, `GenomeSpec`, `ActionRegistry`, memory/causal/capsule/QD configs, an `ApprovedRuleSet`, and an optional `ElementGrid`. UI callers should pass these through the spec rather than mutating engine internals. Non-JSON runtime objects are represented in manifests by stable digests.

ADF support in the unified API is action-token based: variable-length ADF codons decode and dispatch through the action registry. Automatic macro expansion is intentionally not implicit in this release.

`ElementGrid` support is a bridge: a supplied grid can seed `World2D`, and the engine can mirror a digest for audit/UI. Full unified substrate physics remains a later operational layer.

## Studio adapter ownership notes

This core repository exposes object APIs only. A future Studio/API adapter may use FastAPI or WebSocket in a separate repository, but it must own long-running `GenesisEngine` executions through an explicit worker, queue, or process boundary. Do not rely on a FastAPI request-handler threadpool to own engine state, because synchronous FastAPI `def` path operations are run in an external threadpool by the framework. REST and WebSocket routes should publish state from the run owner rather than mutating core engine objects concurrently.

Core-boundary checks should use the AST-based `tools/check_core_boundary.py` guard so documentation may mention Studio technologies while actual imports under `src/codontrace` remain blocked.
