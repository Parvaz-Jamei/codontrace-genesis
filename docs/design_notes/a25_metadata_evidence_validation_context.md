# A25 Metadata/Evidence Validation Context

CodonTrace treats `GenesisExperimentSpec.metadata` as annotation and artifact-pointer data only. Metadata keys such as `validated_intervention_result_digest`, `validated_oee_report_digest`, `baseline_digest`, `effect_size`, or `claim_gate_decision_digest` are not accepted as validated scientific evidence by themselves.



Default and metadata-only runs must report:

```text
scientific_protocol_executed = False
scientific_validation_protocol_executed = false
intervention_protocol_executed = false
oee_protocol_executed = false
```

Validated artifact contexts may grant stronger alpha-level claims only when the required typed artifacts and derived evidence flags are present. These are still alpha scientific-library claim gates, not proof of causal discovery, artificial life, open-ended evolution, or production readiness.
