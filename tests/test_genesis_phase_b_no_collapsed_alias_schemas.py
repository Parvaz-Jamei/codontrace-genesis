from dataclasses import is_dataclass, fields

import codontrace.genesis.phase_b_scientific_maturity as pb


def _schema_default(cls: type) -> str:
    for f in fields(cls):
        if f.name == "schema_version":
            return str(f.default)
    raise AssertionError(f"{cls.__name__} has no schema_version field")


def test_phase_b_public_schema_types_are_not_collapsed_aliases() -> None:
    groups = [
        ["DiscoveryEvent", "DiscoveryCandidate", "DiscoveryWitness", "D0BaselineReport", "ShadowBaselineReport", "DistanceToD0Result", "DiscoveryPersistenceReport", "DiscoveryClaimEligibilityResult"],
        ["AblationWitness", "AblationPlan", "AblationResult", "InterventionResult", "InterventionComparisonReport"],
        ["HeldoutEvaluationResult", "LineageSnapshot", "WorldSnapshot", "PopulationSnapshot", "PartnerGroupSpec", "HeldoutEvaluationSpec", "ReplayableEvaluationSpec", "GeneralizationMatrix", "HeldoutLeakageAudit"],
        ["OEEClaimEligibilityResult", "NoveltyTrajectory", "PersistenceReport", "LearnabilityReport", "SteppingStoneTransferReport", "OEECandidateMetrics"],
        ["CurriculumEnvironmentRecord", "TaskGeneratorSpec", "EnvironmentMutationSpec", "CurriculumStepRecord", "EnvironmentLineageRecord", "ChallengeNoveltyReport", "EnvironmentAgentTransferRecord"],
        ["ScaleBenchmarkReport", "ScaleBenchmarkSpec", "ResourceBudgetPolicy", "LongHorizonRunManifest", "CheckpointResumeAudit", "SeedSweepReport"],
        ["StatisticalClaimValidationResult", "PreregisteredMetricSpec", "PairedSeedComparison", "EffectSizeReport", "ConfidenceIntervalReport", "MultipleComparisonAudit", "NegativeResultReport"],
        ["PluginValidationResult", "PluginSpec", "PluginManifest", "ActionPluginSpec", "WorldPluginSpec", "FitnessPluginSpec", "MutationPluginSpec", "PolicyPluginSpec"],
        ["ReleaseEvidencePackSample", "Phase3ScientificSummary", "ReplayBundleIndex", "BenchmarkLeaderboardArtifact", "AblationMatrixArtifact", "ClaimDowngradeReport", "ReleaseEvidencePack", "FinalClaimManifest", "EvidenceLineageDAG"],
    ]
    for names in groups:
        classes = [getattr(pb, name) for name in names]
        assert all(is_dataclass(cls) for cls in classes)
        assert len({id(cls) for cls in classes}) == len(classes)
        assert len({_schema_default(cls) for cls in classes}) == len(classes)
