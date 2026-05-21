# Phase 2 Evidence Protocol

Phase 2 expands GENESIS with stronger evolutionary-intelligence and discovery-capability surfaces. The protocol requirement is strict: every measured field must be backed by a real digest, and every claim must be traceable to runtime evidence.

## Manifest requirements

All Phase 2 manifest fields use `phase2.<field>.status`. Measured or claim-eligible statuses require a non-placeholder runtime hash. Provisional fields require both a digest and a status reason. Placeholder values such as `none`, `null`, `placeholder`, `default`, `not_run`, `disabled`, and `sha256:placeholder` are never valid measured evidence.

## Runtime evidence expectations

- Variable genome support reports structural mutation provenance and genome digests.
- ADF usefulness requires reuse, source-map digest, controls, finite metrics, and positive compression for compression claims.
- Semantic proxy reports are wired from engine runtime into manifest status and ClaimGate evidence.
- Event and causal evidence separate association from intervention or ablation.
- OEE candidate evidence requires novelty, learnability, persistence, controls, and replay.

## Consistency validation

`GenesisRunResult.validate_consistency(strict=True)` checks manifest/hash consistency, ClaimGate digest consistency, run-specific action wiring, social descriptor counts, placeholder measured hashes, and non-finite payloads. Official pilots should pass strict consistency validation before release decisions.
