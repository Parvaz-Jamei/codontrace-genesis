from codontrace.genesis.discovery_gate import (
    AblationMatrixResult,
    D0CalibrationRun,
    DiscoveryGate,
    PersistenceResult,
    ShadowRunResult,
)


def test_discovery_gate_downgrades_without_required_evidence():
    result = DiscoveryGate().evaluate(candidate_id="c1")

    assert result.decision.level == "candidate_only"
    assert "missing_or_failed_d0_baseline" in result.decision.reasons


def test_discovery_gate_supports_candidate_with_full_evidence():
    result = DiscoveryGate().evaluate(
        candidate_id="c1",
        d0=D0CalibrationRun("d0", 1.2, True),
        shadow=ShadowRunResult("shadow", True),
        persistence=PersistenceResult(5, 3),
        ablation=AblationMatrixResult("abl", True, ("qd",)),
        replay_verified=True,
        qd_novelty_checked=True,
        review_status="accepted",
    )

    assert result.decision.level == "supported_candidate"
    assert not any("proof" in reason.code for reason in result.decision.reasons)
