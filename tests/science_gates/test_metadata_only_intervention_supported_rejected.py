from __future__ import annotations

from codontrace.genesis.causal_validation import build_intervention_result
from codontrace.genesis.engine import GenesisEngine, GenesisEngineConfig, GenesisExperimentSpec
from codontrace.genesis.evidence_validation import EvidenceValidationContext


def test_metadata_only_intervention_supported_rejected() -> None:
    spec = GenesisExperimentSpec(
        tick_count=0,
        engine_config=GenesisEngineConfig(claim_level="intervention_supported"),
        metadata={
            "intervention_result_status": "supported",
            "paired_seeds": True,
            "validated_intervention_result_digest": "fake",
            "baseline_digest": "fake_base",
            "treatment_digest": "fake_treatment",
            "intervention_protocol_digest": "fake_protocol",
            "effect_size": 0.5,
            "paired_seed_protocol_digest": "fake_seed_protocol",
            "claim_gate_decision_digest": "fake_decision",
        },
    )

    result = GenesisEngine.from_spec(spec).run_ticks()

    assert result.manifest.claim_level == "event_association_only"
    assert result.manifest.claim_gate_allowed is False
    assert result.manifest.claim_gate_decision == "insufficient_evidence"
    assert "missing_intervention_result_artifact" in result.manifest.failed_reasons
    assert result.manifest.scientific_protocol_executed is False


def test_intervention_supported_requires_validated_intervention_result_artifact() -> None:
    intervention = build_intervention_result("scenario", [1.0, 2.0, 3.0], [2.0, 3.0, 4.0])
    context = EvidenceValidationContext(
        intervention_results=(intervention,),
        intervention_protocol_digests=("protocol-artifact",),
        paired_seed_protocol_digests=("paired-seed-protocol",),
    )
    spec = GenesisExperimentSpec(
        tick_count=0,
        engine_config=GenesisEngineConfig(claim_level="intervention_supported"),
        evidence_validation_context=context,
        metadata={
            "intervention_result_status": "not_trusted_if_metadata_only",
            "claim_gate_decision_digest": "user_supplied_must_be_ignored",
        },
    )

    result = GenesisEngine.from_spec(spec).run_ticks()

    assert result.manifest.claim_level == "intervention_supported"
    assert result.manifest.claim_gate_allowed is True
    assert result.manifest.claim_gate_decision == "allowed"
    assert result.manifest.scientific_protocol_executed is True
