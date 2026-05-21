# Replay and Artifacts

`RunManifest`, `RunArtifactSchema`, `ReplayBundle`, `PopulationSnapshot`, and `AgentSnapshot` provide deterministic object-level schemas. Core does not write files implicitly. Use `JsonArtifactExporter` when a caller explicitly wants JSON text.


## Replay verification scope

`ReplayBundle` is a deterministic replay metadata bundle, not a full simulation re-execution engine yet. `verify_replay_bundle(bundle, result)` checks manifest digest, generation digests, tick count, and bundle-level metadata against a `GenesisRunResult`-like object. Full re-execution replay remains future work.
