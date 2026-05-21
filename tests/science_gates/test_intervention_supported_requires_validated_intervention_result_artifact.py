from __future__ import annotations

from codontrace.genesis.causal_validation import build_intervention_result
from codontrace.genesis.engine import GenesisEngine, GenesisEngineConfig, GenesisExperimentSpec
from codontrace.genesis.evidence_validation import EvidenceValidationContext


def test_intervention_supported_requires_validated_intervention_result_artifact_file() -> None:
    intervention = build_intervention_result("scenario", [1.0, 2.0], [2.0, 3.0])
    context = EvidenceValidationContext(
        intervention_results=(intervention,),
        intervention_protocol_digests=("protocol-artifact",),
        paired_seed_protocol_digests=("paired-seed-protocol",),
    )
    result = GenesisEngine.from_spec(
        GenesisExperimentSpec(
            tick_count=0,
            engine_config=GenesisEngineConfig(claim_level="intervention_supported"),
            evidence_validation_context=context,
        )
    ).run_ticks()

    assert result.manifest.claim_level == "intervention_supported"
    assert result.manifest.claim_gate_allowed is True
