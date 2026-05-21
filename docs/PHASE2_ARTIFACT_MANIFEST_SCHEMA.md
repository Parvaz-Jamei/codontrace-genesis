# Phase 2 Artifact Manifest Schema

Phase 2 extends `RunManifest.runtime_hashes` with scientific evidence surfaces. Every surface must have a digest or an explicit deterministic not-run/not-configured digest; empty values are not accepted by `validate_phase2_manifest_fields`.

Required runtime hash surfaces include:

```text
genome_program_digest
structural_mutation_digest
structural_mutation_record_digest
adf_macro_registry_digest
adf_usefulness_report_digest
translation_profile_digest
contribution_ledger_digest
micro_ablation_attribution_digest
innovation_registry_digest
event_graph_digest
causal_intervention_result_digest
discovery_witness_digest
benchmark_scenario_digest
statistical_report_digest
oee_report_digest
social_generalization_digest
phase2_claim_decision_digest
```

Backward-compatible aliases such as `macro_registry_digest`, `macro_utility_digest`, `translation_profile_hash`, and `claim_gate_decision_digest` are preserved.

Manifest hashes are evidence surfaces, not proof by themselves. ClaimGate decides what claim level is allowed.

## Strict status/hash rule

For Phase 2 manifest fields:

- `measured`, `runtime_effective`, and `provisional` require non-empty, non-placeholder runtime hashes.
- `not_run`, `disabled_by_config`, `not_configured`, `fixed_default`, `not_applicable`, `not_observed`, and `empty_but_available` may keep deterministic replay sentinel hashes, but they are not claim-eligible evidence.
