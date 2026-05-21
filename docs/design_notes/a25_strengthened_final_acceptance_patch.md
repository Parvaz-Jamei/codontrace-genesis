# CodonTrace v0.3.0a1 Strengthened Final Acceptance Patch

This design note records the final library-hardening patch applied after the strengthened acceptance review. The goal is not to expand product scope; CodonTrace remains an importable Python scientific library.

## Public API and packaging

`codontrace.__all__` is treated as a real public API contract. Names listed there must be importable from `codontrace`, and a regression test now enforces that contract. The build backend remains setuptools, and unused Hatch build-target sections were removed to avoid misleading mixed-backend configuration.


## Claim and evidence discipline

The default engine claim is `foundation_engine`, with the previous `research_alpha_foundation_engine` retained as a compatibility alias. Metadata-only evidence is not allowed to grant scientific claims. Intervention, OEE, active-QD, predictive, lineage, and related claims require validated artifacts or validated digests plus supporting protocol fields.

Protocol execution semantics are split into feature-specific fields such as predictive, intervention, OEE, translation, and innovation protocol flags. A default run without those protocols reports no scientific validation protocol execution.

## Replay and source integrity


## QD, custom actions, statistics, and immutability

The QD claim ladder separates passive reporting from active QD. A canonical `QDCandidateSearchRunner` preserves candidate genome, macro, and translation digests, while active-QD evidence requires scheduler and parent-selection feedback digests.

Custom action registry identity now includes handler bytecode, constants, closure content, version/provenance, and ABI digest where available; non-built-in handlers are treated as non-replayable external handlers for replay-grade claim gating.

Statistical reports are policy-driven and never grant scientific status from p-values alone. Rule proposals and rule-set diffs deep-freeze nested mappings/lists so replay-critical metadata cannot mutate after construction.
