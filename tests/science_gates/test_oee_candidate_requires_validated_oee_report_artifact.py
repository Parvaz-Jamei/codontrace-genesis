from __future__ import annotations

from codontrace.genesis.engine import GenesisEngine, GenesisEngineConfig, GenesisExperimentSpec
from codontrace.genesis.evidence_validation import EvidenceValidationContext
from codontrace.genesis.statistical_protocol import build_oee_metrics_report


def test_oee_candidate_requires_validated_oee_report_artifact_file() -> None:
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
    )
    result = GenesisEngine.from_spec(
        GenesisExperimentSpec(
            tick_count=0,
            engine_config=GenesisEngineConfig(claim_level="oee_candidate"),
            evidence_validation_context=EvidenceValidationContext(oee_reports=(report,)),
        )
    ).run_ticks()

    assert result.manifest.claim_level == "oee_candidate"
    assert result.manifest.claim_gate_allowed is True
