from __future__ import annotations

from codontrace.genesis.engine import GenesisEngine, GenesisEngineConfig, GenesisExperimentSpec


def test_scientific_protocol_executed_false_for_metadata_only_pseudo_evidence() -> None:
    spec = GenesisExperimentSpec(
        tick_count=0,
        engine_config=GenesisEngineConfig(claim_level="oee_candidate"),
        metadata={
            "intervention_result_status": "supported",
            "oee_status": "candidate",
            "validated_intervention_result_digest": "fake_intervention",
            "validated_oee_report_digest": "fake_oee",
            "oee_protocol_executed": True,
            "claim_gate_decision_digest": "fake_decision",
        },
    )

    result = GenesisEngine.from_spec(spec).run_ticks()

    assert result.manifest.scientific_protocol_executed is False
    statuses = result.manifest.protocol_statuses
    assert statuses["intervention_protocol_executed"] == "false"
    assert statuses["oee_protocol_executed"] == "false"
    assert statuses["scientific_validation_protocol_executed"] == "false"
