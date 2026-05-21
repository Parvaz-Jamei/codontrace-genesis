from __future__ import annotations

from codontrace.genesis.engine import GenesisEngine, GenesisEngineConfig, GenesisExperimentSpec


def test_claim_gate_ignores_user_supplied_claim_gate_decision_digest() -> None:
    spec = GenesisExperimentSpec(
        tick_count=0,
        engine_config=GenesisEngineConfig(claim_level="intervention_supported"),
        metadata={
            "claim_gate_decision_digest": "fake_decision",
            "validated_intervention_result_digest": "fake_result",
            "baseline_digest": "fake_base",
            "treatment_digest": "fake_treatment",
            "intervention_protocol_digest": "fake_protocol",
            "effect_size": 1.0,
            "paired_seed_protocol_digest": "fake_seed_protocol",
        },
    )

    result = GenesisEngine.from_spec(spec).run_ticks()

    assert result.manifest.claim_gate_allowed is False
    assert result.manifest.claim_gate_decision_digest != "fake_decision"
    assert "fake_decision" not in result.manifest.evidence_digests_used
    assert result.manifest.claim_level == "event_association_only"
