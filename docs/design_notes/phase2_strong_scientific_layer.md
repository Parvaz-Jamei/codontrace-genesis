# Design Note: Strong Library Phase 2 Scientific Layer

## Existing modules extended
- `adf_runtime.py`, `causal_graph.py`, `causal_validation.py`, `statistical_protocol.py`, `artifacts.py`, `claim_gate.py`, `benchmark_suite.py`.

## New modules added, if any
- `structural_mutation.py`, `contribution_ledger.py`, `innovation_protection.py`, `event_graph.py`, `translation_profile.py`.

## Scientific source / pattern used
- Codon-level mutation keeps replay alignment in codon-based systems.
- Macro expansion is bounded and source-mapped, not semantic closure.
- Contribution ledger uses local deltas/eligibility/micro-ablation as attribution estimates, not causal proof.
- EventGraph separates temporal/predictive/interventional evidence levels.
- OEE thresholds enforce multi-seed, long-horizon, shadow-run, CI, and persistence requirements.

## What this implements
Variable genome records, executable ADF macro expansion, contribution/innovation evidence, EventGraph migration, predictive/intervention objects, OEE/statistical policy, and TranslationProfile GP-map proxy.

## What this intentionally does not implement
No UI, server, database, app workflow engine, LLM hot-loop, semantic closure, proof of life, or proof of unbounded open-ended evolution.

## Allowed claim
Deterministic, replayable, library-first GENESIS-aligned experimental engine with variable genomes, executable ADF/macros, attribution estimates, causal-evidence protocols, OEE measurement, and adaptive GP-map proxies.

## Rejected claim
Full GENESIS Engine, solved artificial life, semantic closure, true causal intelligence, and proved unbounded OEE.

## Replay / manifest / artifact fields added
Phase 2 runtime hashes for genome programs, structural mutation, macro registry/utility, contribution ledger, innovation registry, EventGraph, predictive/intervention reports, statistical/OEE reports, TranslationProfile, SemanticProxyReport, and ClaimGate decision.

## Tests added
`tests/science_gates/test_strong_library_phase2_*.py`.

## Backward compatibility impact
Existing fixed-genome and fixed-translation behavior remains default. `CausalGraph` remains as compatibility alias while `EventGraph` is canonical for new protocols.

## Runtime-integration completion patch

### Existing modules extended
- `genesis.engine`: now passes Phase 2 runtime hooks from `GenesisExperimentSpec` into organisms and auto-populates Phase 2 manifest hashes.
- `genesis.organism`: now resolves `TranslationProfile` policies and expands registered ADF macros during `step()` without changing the default fixed translator path.
- `genesis.population`: now accepts `StructuralMutationConfig` and uses codon-token structural mutation in reproduction when explicitly configured.
- `genesis.artifacts`: evidence packs can include contribution ledgers built from real `CodonExecutionRecord` payloads.

### What this implements
- Config-gated runtime structural mutation during reproduction.
- Runtime ADF macro expansion from ADF token to primitive action sequence with source-map preservation.
- Runtime translation profile decoding override when a profile is explicitly supplied.
- Automatic contribution-ledger artifact export from source-mapped execution records.
- Automatic Phase 2 manifest runtime hashes for genome program, structural mutation, macro registry, contribution ledger, event graph, translation profile, OEE/statistical placeholders, and semantic proxy report.

### What this intentionally does not implement
- No UI/server/workflow engine.
- No LLM hot-loop behavior.
- No semantic-closure or full-GENESIS claim.
- No true genetic causality claim; contribution remains an attribution estimate.

### Allowed claim
CodonTrace now has Phase 2 runtime-integrated library hooks for variable genomes, executable ADF/macros, contribution-ledger evidence, translation-profile GP-map proxy experiments, and manifest audit fields.

### Rejected claim
This does not prove artificial life, semantic closure, unbounded OEE, causal intelligence, or a full GENESIS engine.

### Tests added
- `tests/science_gates/test_strong_library_phase2_runtime_completion.py`
