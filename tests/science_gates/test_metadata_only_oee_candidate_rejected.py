from __future__ import annotations

from codontrace.genesis.engine import GenesisEngine, GenesisEngineConfig, GenesisExperimentSpec
from codontrace.genesis.evidence_validation import EvidenceValidationContext
from codontrace.genesis.statistical_protocol import build_oee_metrics_report


def test_metadata_only_oee_candidate_rejected() -> None:
    spec = GenesisExperimentSpec(
        tick_count=0,
        engine_config=GenesisEngineConfig(claim_level="oee_candidate"),
        metadata={
            "oee_status": "candidate",
            "validated_oee_report_digest": "fake",
            "oee_protocol_executed": True,
            "shadow_run_present": True,
            "min_seed_threshold_met": True,
            "persistence_window_observed": True,
            "confidence_intervals_present": True,
            "stagnation_diversity_status_recorded": True,
            "claim_gate_decision_digest": "fake_decision",
        },
    )

    result = GenesisEngine.from_spec(spec).run_ticks()

    assert result.manifest.claim_level == "oee_measurement_only"
    assert result.manifest.claim_gate_allowed is False
    assert result.manifest.claim_gate_decision == "insufficient_evidence"
    assert "missing_oee_report_artifact" in result.manifest.failed_reasons
    assert result.manifest.scientific_protocol_executed is False


def test_oee_candidate_requires_validated_oee_report_artifact() -> None:
    report = build_oee_metrics_report(
        seed_count=30,
        generation_count=1000,
        metrics={
            "archive_coverage_slope": 0.2,
            "persistent_novelty_rate": 0.3,
            "lineage_persistence": 10.0,
            "behavior_entropy": 1.5,
        },
        confidence_intervals={
            "archive_coverage_slope": (0.1, 0.3),
            "persistent_novelty_rate": (0.2, 0.4),
            "lineage_persistence": (10.0, 12.0),
            "behavior_entropy": (1.2, 1.8),
        },
        shadow_adjusted=True,
        persistence_window_observed=10,
        stagnation_window=5,
        diversity_collapse_flag=False,
    )
    assert report.claim_level == "oee_candidate"
    spec = GenesisExperimentSpec(
        tick_count=0,
        engine_config=GenesisEngineConfig(claim_level="oee_candidate"),
        evidence_validation_context=EvidenceValidationContext(oee_reports=(report,)),
        metadata={"validated_oee_report_digest": "user_supplied_must_be_ignored"},
    )

    result = GenesisEngine.from_spec(spec).run_ticks()

    assert result.manifest.claim_level == "oee_candidate"
    assert result.manifest.claim_gate_allowed is True
    assert result.manifest.claim_gate_decision == "allowed"
    assert result.manifest.scientific_protocol_executed is True
