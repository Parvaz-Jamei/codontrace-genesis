import codontrace.genesis as g
from codontrace.genesis.replay_integrity import build_replay_digest_class_policy


def test_phase_b_direct_public_api_symbols_are_bound_to_runtime_module():
    expected = {
        "DiscoveryEvent", "D0BaselineReport", "ShadowBaselineReport",
        "DiscoveryPersistenceReport", "DiscoveryClaimEligibilityResult",
        "AblationWitness", "AblationPlan", "AblationResult", "InterventionComparisonReport",
        "LineageSnapshot", "WorldSnapshot", "PartnerGroupSpec", "HeldoutEvaluationSpec",
        "ReplayableEvaluationSpec", "GeneralizationMatrix", "HeldoutLeakageAudit",
        "LongHorizonRunManifest", "CheckpointResumeAudit", "SeedSweepReport",
        "PreregisteredMetricSpec", "PairedSeedComparison", "EffectSizeReport", "ConfidenceIntervalReport",
    }
    missing = sorted(name for name in expected if not hasattr(g, name))
    assert missing == []
    for name in expected:
        assert name in g.__all__


def test_phase_b_core_records_have_replay_policies():
    for path in (
        "codontrace.genesis.phase_b_scientific_maturity.DiscoveryEvent",
        "codontrace.genesis.phase_b_scientific_maturity.AblationWitness",
        "codontrace.genesis.phase_b_scientific_maturity.HeldoutEvaluationResult",
        "codontrace.genesis.phase_b_scientific_maturity.OEEClaimEligibilityResult",
        "codontrace.genesis.phase_b_scientific_maturity.PhaseBScientificMaturityReport",
    ):
        policy = build_replay_digest_class_policy(path)
        assert policy.digest_fields
        assert policy.evidence_role == "reference_or_summary_only_not_scientific_evidence"
