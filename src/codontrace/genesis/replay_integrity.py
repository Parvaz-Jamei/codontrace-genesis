"""Replay digest policy registry for public digest-bearing dataclasses.

This module is intentionally conservative. A dataclass that exposes a
``digest`` or ``*_digest`` field is not automatically scientific evidence.
It must either be listed as replay-critical with strict construction-time
validation, or explicitly listed as a non-replay-critical reference/summary
object that cannot by itself grant scientific claims.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from inspect import isclass
from typing import Any


@dataclass(frozen=True)
class ReplayDigestClassPolicy:
    """Policy for one public dataclass with digest-like fields."""

    class_path: str
    digest_fields: tuple[str, ...]
    replay_role: str
    evidence_role: str
    validation_mode: str
    rationale: str

    @property
    def replay_critical(self) -> bool:
        return self.replay_role == "replay_critical"


STRICT_REPLAY_CRITICAL_DIGEST_CLASSES: tuple[str, ...] = (
    "codontrace.genesis.adf_runtime.MacroPruningDecision",
    "codontrace.genesis.adf_runtime.MacroUtilityRecord",
    "codontrace.genesis.adf_runtime.ADFUsefulnessControlReport",
    "codontrace.genesis.causal_validation.InterventionResult",
    "codontrace.genesis.causal_validation.PredictiveProbeResult",
    "codontrace.genesis.claim_gate.ClaimDecision",
    "codontrace.genesis.claim_gate.ClaimGatePolicy",
    "codontrace.genesis.discovery_witness.DiscoveryWitness",
    "codontrace.genesis.event_graph.EventGraphEdge",
    "codontrace.genesis.final_release_manifest.FinalReleaseManifest",
    "codontrace.genesis.innovation_protection.InnovationRecord",
    "codontrace.genesis.qd_search.QDCandidate",
    "codontrace.genesis.qd_search.QDSchedulerState",
    "codontrace.genesis.quality_diversity.QDArchivePolicy",
    "codontrace.genesis.quality_diversity.QDArchiveRejectedCandidate",
    "codontrace.genesis.quality_diversity.QDElite",
    "codontrace.genesis.scientific_evidence.ScientificEvidencePack",
    "codontrace.genesis.statistical_protocol.OEEMetricsReport",
    "codontrace.genesis.structural_mutation.GenomeProgram",
    "codontrace.genesis.structural_mutation.StructuralMutationRecord",
    "codontrace.genesis.translation_profile.SemanticProxyReport",
    "codontrace.genesis.translation_profile.TranslationProfile",
    "codontrace.genesis.translation_profile.TranslationUpdateRecord",
)

NON_REPLAY_CRITICAL_DIGEST_CLASSES: tuple[str, ...] = (
    "codontrace.genesis.ablation.AblationRunRecord",
    "codontrace.genesis.adf_runtime.ADFExpansionResult",
    "codontrace.genesis.adf_runtime.ADFMacroDefinition",
    "codontrace.genesis.api_audit.ActionWiringRecord",
    "codontrace.genesis.api_audit.CompatibilitySnapshot",
    "codontrace.genesis.artifacts.AgentSnapshot",
    "codontrace.genesis.artifacts.DiscoveryRecord",
    "codontrace.genesis.artifacts.PopulationSnapshot",
    "codontrace.genesis.artifacts.RawEventSchema",
    "codontrace.genesis.artifacts.ReplayVerificationResult",
    "codontrace.genesis.artifacts.ReviewStatus",
    "codontrace.genesis.artifacts.RunManifest",
    "codontrace.genesis.birth.ADFInheritanceRecord",
    "codontrace.genesis.birth.AIBirthInterventionRecord",
    "codontrace.genesis.birth.BirthEvent",
    "codontrace.genesis.birth.BirthRequest",
    "codontrace.genesis.birth.ChildGenomeResult",
    "codontrace.genesis.birth.LearningInheritanceRecord",
    "codontrace.genesis.birth.MutationAuditResult",
    "codontrace.genesis.birth.MutationPlan",
    "codontrace.genesis.birth.SkillCompressionRecord",
    "codontrace.genesis.birth.WorldLawPatch",
    "codontrace.genesis.benchmark_suite.BenchmarkScenarioSpec",
    "codontrace.genesis.controls.ControlGenome",
    "codontrace.genesis.capsule.CapsuleTransferMetric",
    "codontrace.genesis.death.DeathClassificationRecord",
    "codontrace.genesis.diagnostics.CapsuleUtilityRecord",
    "codontrace.genesis.diagnostics.DeathReasonRecord",
    "codontrace.genesis.diagnostics.EnergyAccountingRecord",
    "codontrace.genesis.diagnostics.EngineDigestAuditRecord",
    "codontrace.genesis.diagnostics.ExportWrittenFile",
    "codontrace.genesis.capsule.CausalCapsule",
    "codontrace.genesis.campaign.EliteLineage",
    "codontrace.genesis.campaign.EliteReplayResult",
    "codontrace.genesis.campaign.EliteSelectionResult",
    "codontrace.genesis.campaign.EvolutionCampaign",
    "codontrace.genesis.campaign.HeldoutEvaluationResult",
    "codontrace.genesis.capsule.CapsuleShuffleRecord",
    "codontrace.genesis.evidence.EvidenceManifest",
    "codontrace.genesis.phase1_runtime_maturity.ADFUsefulnessAuditRecord",
    "codontrace.genesis.phase1_runtime_maturity.CapsuleControlAuditRecord",
    "codontrace.genesis.phase1_runtime_maturity.CausalInterventionAuditRecord",
    "codontrace.genesis.phase1_runtime_maturity.DeathEnergyDiagnosticRecord",
    "codontrace.genesis.phase1_runtime_maturity.MutationOperatorAuditRecord",
    "codontrace.genesis.phase1_runtime_maturity.Phase1FeatureMaturityStatus",
    "codontrace.genesis.phase1_runtime_maturity.Phase1RuntimeMaturityReport",
    "codontrace.genesis.phase1_runtime_maturity.ReproductionGateAuditRecord",
    "codontrace.genesis.phase1_runtime_maturity.RuntimeQDAuditRecord",
    "codontrace.genesis.phase1_runtime_maturity.RuntimeRoleEvidenceRecord",
    "codontrace.genesis.phase1_runtime_maturity.ToolchainPreconditionAuditRecord",
    "codontrace.genesis.fitness.FitnessLandscapeScore",
    "codontrace.genesis.fitness.SelectionFitnessScore",
    "codontrace.genesis.frames.EventFrame",
    "codontrace.genesis.frames.WorldFrame",
    "codontrace.genesis.generalization.GeneralizationResult",
    "codontrace.genesis.generalization.HeldoutWorldSpec",
    "codontrace.genesis.role.RoleAssignment",
    "codontrace.genesis.role.RoleContribution",
    "codontrace.genesis.selection.NoveltyScore",
    "codontrace.genesis.selection.QDSelectionFeedback",
    "codontrace.genesis.capsule.NexusSignal",
    "codontrace.genesis.causal_runtime.CausalPrediction",
    "codontrace.genesis.causal_validation.CausalValidationReport",
    "codontrace.genesis.claim_gate.ClaimRequest",
    "codontrace.genesis.claim_gate.StrongClaimLadderResult",
    "codontrace.genesis.contribution_ledger.ContributionLedger",
    "codontrace.genesis.contribution_ledger.MicroAblationAttributionRecord",
    "codontrace.genesis.discovery.DiscoveryWitnessStub",
    "codontrace.genesis.discovery_gate.AblationMatrixResult",
    "codontrace.genesis.discovery_gate.D0CalibrationRun",
    "codontrace.genesis.discovery_gate.DiscoveryGateResult",
    "codontrace.genesis.discovery_gate.ShadowRunResult",
    "codontrace.genesis.discovery_protocol.D0ExecutableBaseline",
    "codontrace.genesis.discovery_protocol.ShadowRun",
    "codontrace.genesis.discovery_runner.DiscoveryCandidateFromQD",
    "codontrace.genesis.discovery_runner.DiscoveryDetectionResult",
    "codontrace.genesis.discovery_runner.DiscoveryReviewPack",
    "codontrace.genesis.discovery_witness.D0BaselineRun",
    "codontrace.genesis.discovery_witness.D0CalibrationResult",
    "codontrace.genesis.discovery_witness.DiscoveryCandidate",
    "codontrace.genesis.discovery_witness.DiscoveryWitnessConfig",
    "codontrace.genesis.discovery_witness.DistanceToD0Result",
    "codontrace.genesis.engine.GenesisRun",
    "codontrace.genesis.engine.GenesisRunSummary",
    "codontrace.genesis.engine.GenesisSnapshot",
    "codontrace.genesis.evidence_bundle.EvidenceRecord",
    "codontrace.genesis.evidence_lineage.MatureAlphaReadinessResult",
    "codontrace.genesis.example_smoke.ExampleSmokeResult",
    "codontrace.genesis.fitness.FitnessBreakdown",
    "codontrace.genesis.intervention.CounterfactualProbe",
    "codontrace.genesis.limitations.FailureModeRecord",
    "codontrace.genesis.learning.MemoryConsolidationResult",
    "codontrace.genesis.mature_alpha.DocumentationAuditResult",
    "codontrace.genesis.mature_alpha.SecurityEvidenceRecord",
    "codontrace.genesis.memory.EpisodicEvent",
    "codontrace.genesis.multiseed.SeedRunRecord",
    "codontrace.genesis.odd.GenesisODDReport",
    "codontrace.genesis.paper_companion.ExternalReplicationRecord",
    "codontrace.genesis.paper_companion.PaperEvidenceBundle",
    "codontrace.genesis.population.GenerationResult",
    "codontrace.genesis.population.LineageRecord",
    "codontrace.genesis.population.MutationResult",
    "codontrace.genesis.population.OrganismStepRecord",
    "codontrace.genesis.qd_descriptors.DescriptorSchema",
    "codontrace.genesis.qd_search.QDEvaluateResult",
    "codontrace.genesis.qd_search.QDParentSelection",
    "codontrace.genesis.qd_search.QDSearchStepResult",
    "codontrace.genesis.quality_diversity.DiscoveryCandidateFromQD",
    "codontrace.genesis.quality_diversity.QDArchiveBatchUpdateResult",
    "codontrace.genesis.quality_diversity.QDArchiveItemUpdateRecord",
    "codontrace.genesis.quality_diversity.QDArchiveSummary",
    "codontrace.genesis.quality_diversity.QDArchiveUpdateResult",
    "codontrace.genesis.release_candidate.ReleaseCandidateChecklist",
    "codontrace.genesis.release_candidate.ReleaseGateRecord",
    "codontrace.genesis.release_readiness.DocsConsistencyRecord",
    "codontrace.genesis.research_validation.ValidationRunRecord",
    "codontrace.genesis.research_validation.ValidationScenario",
    "codontrace.genesis.review.ExternalReviewRecord",
    "codontrace.genesis.review.HumanReviewDecision",
    "codontrace.genesis.review.LLMReviewResult",
    "codontrace.genesis.review.ReviewArtifact",
    "codontrace.genesis.review.ReviewFinding",
    "codontrace.genesis.ribosome.CodonExecutionRecord",
    "codontrace.genesis.rules.ApprovedRuleApplicationResult",
    "codontrace.genesis.rules.HumanApprovalRecord",
    "codontrace.genesis.rules.RuleValidationResult",
    "codontrace.genesis.scientific_evidence.AblationEvidenceSummary",
    "codontrace.genesis.scientific_evidence.D0EvidenceSummary",
    "codontrace.genesis.scientific_evidence.QDEvidenceSummary",
    "codontrace.genesis.scientific_evidence.WitnessEvidenceSummary",
    "codontrace.genesis.selection.EvolutionSelectionResult",
    "codontrace.genesis.social.SocialInteractionEvent",
    "codontrace.genesis.statistical_report.StatisticalExperimentReport",
    "codontrace.genesis.toolchain.ToolChainRecord",
    "codontrace.replay.ReplayResult",
    "codontrace.replay.TimelineReplayResult",
    "codontrace.scenario.Scenario",
    "codontrace.simulation.SimulationResult",
    "codontrace.trace.TraceEvent",
)

_DIGEST_FIELDS_BY_CLASS: dict[str, tuple[str, ...]] = {
    "codontrace.genesis.ablation.AblationRunRecord": (
        "config_digest",
        "trace_digest",
        "behavior_digest",
        "witness_digest",
        "qd_archive_digest",
    ),
    "codontrace.genesis.adf_runtime.ADFExpansionResult": ("expansion_digest",),
    "codontrace.genesis.adf_runtime.ADFMacroDefinition": (
        "source_pattern_digest",
        "definition_digest",
    ),
    "codontrace.genesis.adf_runtime.MacroPruningDecision": ("digest",),
    "codontrace.genesis.adf_runtime.MacroUtilityRecord": ("contribution_ledger_digest", "digest"),
    "codontrace.genesis.adf_runtime.ADFUsefulnessControlReport": ("source_map_digest", "digest"),
    "codontrace.genesis.api_audit.ActionWiringRecord": ("runtime_validation_digest",),
    "codontrace.genesis.api_audit.CompatibilitySnapshot": (
        "config_defaults_digest",
        "metadata_digest",
    ),
    "codontrace.genesis.artifacts.AgentSnapshot": (
        "genome_digest",
        "causal_graph_digest",
        "memory_digest",
    ),
    "codontrace.genesis.artifacts.DiscoveryRecord": ("manifest_digest",),
    "codontrace.genesis.artifacts.PopulationSnapshot": ("population_digest", "nexus_digest"),
    "codontrace.genesis.artifacts.RawEventSchema": ("event_digest",),
    "codontrace.genesis.artifacts.ReplayVerificationResult": ("manifest_digest", "bundle_digest"),
    "codontrace.genesis.artifacts.ReviewStatus": ("decision_digest",),
    "codontrace.genesis.artifacts.RunManifest": (
        "replay_digest",
        "source_digest",
        "rng_state_digest",
        "seed_schedule_digest",
        "archive_digest",
        "qd_scheduler_digest",
        "benchmark_scenario_digest",
        "execution_source_digest",
        "claim_gate_decision_digest",
    ),
    "codontrace.genesis.birth.ADFInheritanceRecord": (
        "parent_adf_digest",
        "child_adf_digest",
    ),
    "codontrace.genesis.birth.AIBirthInterventionRecord": (
        "input_evidence_digest",
        "decision_digest",
    ),
    "codontrace.genesis.birth.BirthEvent": (
        "parent_genome_digest",
        "child_genome_digest",
        "mutation_digest",
        "birth_policy_digest",
        "reproduction_gate_digest",
    ),
    "codontrace.genesis.birth.BirthRequest": (
        "parent_genome_digest",
        "policy_digest",
        "intent_digest",
    ),
    "codontrace.genesis.birth.ChildGenomeResult": (
        "parent_genome_digest",
        "child_genome_digest",
        "mutation_digest",
    ),
    "codontrace.genesis.birth.LearningInheritanceRecord": (
        "source_lifetime_evidence_digest",
        "compressed_skill_digest",
        "child_received_skill_digest",
    ),
    "codontrace.genesis.birth.MutationAuditResult": (
        "child_genome_digest",
        "mutation_digest",
    ),
    "codontrace.genesis.birth.MutationPlan": (
        "parent_genome_digest",
        "controller_digest",
    ),
    "codontrace.genesis.birth.SkillCompressionRecord": (
        "successful_behavior_trace_digest",
        "compressed_skill_digest",
    ),
    "codontrace.genesis.birth.WorldLawPatch": (
        "old_digest",
        "new_digest",
        "controller_digest",
        "claim_gate_decision_digest",
    ),
    "codontrace.genesis.benchmark_suite.BenchmarkScenarioSpec": (
        "baseline_config_digest",
        "treatment_config_digest",
    ),
    "codontrace.genesis.controls.ControlGenome": ("action_filter_policy_digest",),
    "codontrace.genesis.capsule.CapsuleTransferMetric": (
        "pre_behavior_digest",
        "post_behavior_digest",
        "pre_graph_digest",
        "post_graph_digest",
    ),
    "codontrace.genesis.death.DeathClassificationRecord": ("death_policy_digest",),
    "codontrace.genesis.diagnostics.CapsuleUtilityRecord": ("utility_protocol_digest",),
    "codontrace.genesis.diagnostics.DeathReasonRecord": ("death_policy_digest",),
    "codontrace.genesis.diagnostics.EnergyAccountingRecord": ("death_policy_digest",),
    "codontrace.genesis.diagnostics.EngineDigestAuditRecord": ("digest",),
    "codontrace.genesis.diagnostics.ExportWrittenFile": ("header_digest", "file_digest"),
    "codontrace.genesis.capsule.CausalCapsule": ("source_graph_digest", "source_fitness_digest"),
    "codontrace.genesis.campaign.EliteLineage": (
        "lineage_digest",
        "replay_digest",
        "behavior_digest",
    ),
    "codontrace.genesis.campaign.EliteReplayResult": ("replay_digest",),
    "codontrace.genesis.campaign.EliteSelectionResult": ("selection_digest",),
    "codontrace.genesis.campaign.EvolutionCampaign": ("train_digest",),
    "codontrace.genesis.campaign.HeldoutEvaluationResult": (
        "evaluation_digest",
        "train_digest",
        "heldout_digest",
    ),
    "codontrace.genesis.capsule.CapsuleShuffleRecord": (
        "real_capsule_digest",
        "shuffled_capsule_digest",
    ),
    "codontrace.genesis.evidence.EvidenceManifest": (
        "config_digest",
        "source_digest",
        "protocol_digest",
    ),
    "codontrace.genesis.phase1_runtime_maturity.ADFUsefulnessAuditRecord": (
        "source_trace_digest",
        "source_map_digest",
        "record_digest",
    ),
    "codontrace.genesis.phase1_runtime_maturity.CapsuleControlAuditRecord": ("record_digest",),
    "codontrace.genesis.phase1_runtime_maturity.CausalInterventionAuditRecord": (
        "baseline_digest",
        "treatment_digest",
        "event_graph_digest",
        "causal_graph_digest",
        "record_digest",
    ),
    "codontrace.genesis.phase1_runtime_maturity.DeathEnergyDiagnosticRecord": ("record_digest",),
    "codontrace.genesis.phase1_runtime_maturity.MutationOperatorAuditRecord": (
        "before_genome_digest",
        "after_genome_digest",
        "codon_table_digest",
        "operator_parameters_digest",
        "record_digest",
    ),
    "codontrace.genesis.phase1_runtime_maturity.Phase1FeatureMaturityStatus": ("record_digest",),
    "codontrace.genesis.phase1_runtime_maturity.Phase1RuntimeMaturityReport": (
        "run_digest",
        "source_digest",
        "record_digest",
    ),
    "codontrace.genesis.phase1_runtime_maturity.ReproductionGateAuditRecord": (
        "parent_genome_digest",
        "child_genome_digest",
        "record_digest",
    ),
    "codontrace.genesis.phase1_runtime_maturity.RuntimeQDAuditRecord": (
        "objective_vector_digest",
        "record_digest",
    ),
    "codontrace.genesis.phase1_runtime_maturity.RuntimeRoleEvidenceRecord": (
        "contribution_digest",
        "record_digest",
    ),
    "codontrace.genesis.phase1_runtime_maturity.ToolchainPreconditionAuditRecord": ("record_digest",),
    "codontrace.genesis.fitness.FitnessLandscapeScore": ("landscape_digest",),
    "codontrace.genesis.fitness.SelectionFitnessScore": ("breakdown_digest", "alive_gate_digest"),
    "codontrace.genesis.frames.EventFrame": ("digest",),
    "codontrace.genesis.frames.WorldFrame": ("world_digest",),
    "codontrace.genesis.generalization.GeneralizationResult": ("train_digest", "heldout_digest"),
    "codontrace.genesis.generalization.HeldoutWorldSpec": ("world_digest",),
    "codontrace.genesis.role.RoleAssignment": ("action_distribution_digest",),
    "codontrace.genesis.role.RoleContribution": ("evidence_digest",),
    "codontrace.genesis.selection.NoveltyScore": ("descriptor_digest",),
    "codontrace.genesis.selection.QDSelectionFeedback": (
        "descriptor_digest",
        "fitness_scores_digest",
        "novelty_scores_digest",
    ),
    "codontrace.genesis.capsule.NexusSignal": ("signal_digest",),
    "codontrace.genesis.causal_runtime.CausalPrediction": ("graph_digest",),
    "codontrace.genesis.causal_validation.CausalValidationReport": ("manifest_digest",),
    "codontrace.genesis.causal_validation.InterventionResult": (
        "baseline_digest",
        "treatment_digest",
        "digest",
    ),
    "codontrace.genesis.causal_validation.PredictiveProbeResult": ("digest",),
    "codontrace.genesis.claim_gate.ClaimDecision": ("digest",),
    "codontrace.genesis.claim_gate.ClaimGatePolicy": ("digest",),
    "codontrace.genesis.claim_gate.ClaimRequest": ("manifest_digest",),
    "codontrace.genesis.claim_gate.StrongClaimLadderResult": ("digest",),
    "codontrace.genesis.contribution_ledger.ContributionLedger": ("digest",),
    "codontrace.genesis.contribution_ledger.MicroAblationAttributionRecord": ("contribution_ledger_digest", "digest"),
    "codontrace.genesis.discovery.DiscoveryWitnessStub": (
        "behavior_digest",
        "graph_digest",
        "vocabulary_digest",
        "capsule_store_digest",
    ),
    "codontrace.genesis.discovery_gate.AblationMatrixResult": ("matrix_digest",),
    "codontrace.genesis.discovery_gate.D0CalibrationRun": ("baseline_digest",),
    "codontrace.genesis.discovery_gate.DiscoveryGateResult": ("manifest_digest",),
    "codontrace.genesis.discovery_gate.ShadowRunResult": ("shadow_digest",),
    "codontrace.genesis.discovery_protocol.D0ExecutableBaseline": ("manifest_digest",),
    "codontrace.genesis.discovery_protocol.ShadowRun": ("manifest_digest",),
    "codontrace.genesis.discovery_runner.DiscoveryCandidateFromQD": ("archive_digest",),
    "codontrace.genesis.discovery_runner.DiscoveryDetectionResult": ("candidate_digest",),
    "codontrace.genesis.discovery_runner.DiscoveryReviewPack": ("manifest_digest",),
    "codontrace.genesis.discovery_witness.D0BaselineRun": (
        "config_digest",
        "behavior_digest",
        "trace_digest",
        "population_digest",
        "graph_digest",
        "vocabulary_digest",
        "capsule_store_digest",
    ),
    "codontrace.genesis.discovery_witness.D0CalibrationResult": ("baseline_digest",),
    "codontrace.genesis.discovery_witness.DiscoveryCandidate": ("behavior_digest",),
    "codontrace.genesis.discovery_witness.DiscoveryWitness": (
        "baseline_digest",
        "trace_digest",
        "replay_digest",
        "graph_digest",
        "vocabulary_digest",
        "capsule_store_digest",
        "statistical_protocol_digest",
        "qd_archive_digest",
    ),
    "codontrace.genesis.discovery_witness.DiscoveryWitnessConfig": (
        "require_trace_digest",
        "require_replay_digest",
        "require_baseline_digest",
    ),
    "codontrace.genesis.discovery_witness.DistanceToD0Result": ("baseline_digest",),
    "codontrace.genesis.engine.GenesisRun": ("spec_digest",),
    "codontrace.genesis.engine.GenesisRunSummary": ("manifest_digest",),
    "codontrace.genesis.engine.GenesisSnapshot": (
        "world_digest",
        "qd_archive_digest",
        "element_grid_digest",
    ),
    "codontrace.genesis.event_graph.EventGraphEdge": ("validation_digest", "digest"),
    "codontrace.genesis.evidence_bundle.EvidenceRecord": (
        "config_digest",
        "trace_digest",
        "replay_digest",
        "behavior_digest",
        "graph_digest",
        "qd_archive_digest",
        "witness_digest",
    ),
    "codontrace.genesis.evidence_lineage.MatureAlphaReadinessResult": (
        "release_decision_digest",
        "scientific_evidence_validation_digest",
        "evidence_quality_digest",
        "claim_audit_digest",
        "api_audit_digest",
    ),
    "codontrace.genesis.example_smoke.ExampleSmokeResult": ("stdout_digest",),
    "codontrace.genesis.final_release_manifest.FinalReleaseManifest": (
        "source_zip_digest",
        "wheel_digest",
        "sdist_digest",
        "api_stability_map_digest",
        "compatibility_policy_digest",
        "documentation_audit_digest",
        "claim_audit_digest",
        "scientific_evidence_validation_digest",
        "mature_alpha_readiness_digest",
        "release_decision_digest",
        "citation_digest",
        "security_evidence_digest",
        "limitations_digest",
    ),
    "codontrace.genesis.fitness.FitnessBreakdown": ("config_digest",),
    "codontrace.genesis.innovation_protection.InnovationRecord": ("contribution_digest", "digest"),
    "codontrace.genesis.intervention.CounterfactualProbe": (
        "control_digest",
        "intervention_digest",
    ),
    "codontrace.genesis.limitations.FailureModeRecord": ("trace_digest",),
    "codontrace.genesis.learning.MemoryConsolidationResult": (
        "consolidation_event_digest",
    ),
    "codontrace.genesis.mature_alpha.DocumentationAuditResult": (
        "claim_audit_digest",
        "api_coverage_digest",
    ),
    "codontrace.genesis.mature_alpha.SecurityEvidenceRecord": ("evidence_url_or_digest",),
    "codontrace.genesis.memory.EpisodicEvent": ("trace_event_digest",),
    "codontrace.genesis.multiseed.SeedRunRecord": (
        "manifest_digest",
        "replay_digest",
        "evidence_digest",
        "qd_archive_digest",
    ),
    "codontrace.genesis.odd.GenesisODDReport": ("spec_digest",),
    "codontrace.genesis.paper_companion.ExternalReplicationRecord": (
        "scenario_digest",
        "evidence_digest",
    ),
    "codontrace.genesis.paper_companion.PaperEvidenceBundle": (
        "scenario_suite_digest",
        "evidence_pack_digest",
        "validation_matrix_digest",
        "reproducibility_summary_digest",
        "limitations_digest",
        "claim_audit_digest",
    ),
    "codontrace.genesis.population.GenerationResult": ("world_before_digest", "world_after_digest"),
    "codontrace.genesis.population.LineageRecord": ("genome_digest",),
    "codontrace.genesis.population.MutationResult": ("rng_digest",),
    "codontrace.genesis.population.OrganismStepRecord": (
        "trace_digest",
        "world_before_digest",
        "world_after_digest",
        "genome_digest",
    ),
    "codontrace.genesis.qd_descriptors.DescriptorSchema": ("digest",),
    "codontrace.genesis.qd_search.QDCandidate": (
        "genome_digest",
        "genome_program_digest",
        "macro_registry_digest",
        "translation_profile_digest",
        "mutation_record_digest",
    ),
    "codontrace.genesis.qd_search.QDEvaluateResult": ("fitness_breakdown_digest",),
    "codontrace.genesis.qd_search.QDParentSelection": ("parent_candidate_digest",),
    "codontrace.genesis.qd_search.QDSchedulerState": (
        "archive_digest",
        "emitter_state_digest",
        "descriptor_schema_digest",
        "parent_selection_feedback_digest",
        "rng_state_digest",
        "digest",
    ),
    "codontrace.genesis.qd_search.QDSearchStepResult": ("archive_digest",),
    "codontrace.genesis.quality_diversity.DiscoveryCandidateFromQD": ("archive_digest",),
    "codontrace.genesis.quality_diversity.QDArchiveBatchUpdateResult": (
        "archive_before_digest",
        "archive_after_digest",
    ),
    "codontrace.genesis.quality_diversity.QDArchiveItemUpdateRecord": (
        "candidate_digest",
        "previous_elite_digest",
        "new_elite_digest",
    ),
    "codontrace.genesis.quality_diversity.QDArchivePolicy": (
        "require_behavior_digest",
        "require_trace_digest",
    ),
    "codontrace.genesis.quality_diversity.QDArchiveRejectedCandidate": (
        "candidate_digest",
        "existing_elite_digest",
    ),
    "codontrace.genesis.quality_diversity.QDArchiveSummary": (
        "archive_digest",
        "best_elite_digest",
    ),
    "codontrace.genesis.quality_diversity.QDArchiveUpdateResult": (
        "candidate_digest",
        "previous_elite_digest",
    ),
    "codontrace.genesis.quality_diversity.QDElite": (
        "genome_digest",
        "trace_digest",
        "behavior_digest",
    ),
    "codontrace.genesis.release_candidate.ReleaseCandidateChecklist": (
        "api_snapshot_digest",
        "claim_audit_digest",
        "validation_bundle_digest",
        "compatibility_snapshot_digest",
        "citation_digest",
        "limitations_digest",
    ),
    "codontrace.genesis.release_candidate.ReleaseGateRecord": ("evidence_digest",),
    "codontrace.genesis.release_readiness.DocsConsistencyRecord": ("claim_audit_digest",),
    "codontrace.genesis.research_validation.ValidationRunRecord": (
        "trace_digest",
        "behavior_digest",
        "qd_archive_digest",
        "witness_digest",
        "ablation_digest",
        "statistical_protocol_digest",
    ),
    "codontrace.genesis.research_validation.ValidationScenario": ("config_digest",),
    "codontrace.genesis.review.ExternalReviewRecord": ("request_digest", "result_digest"),
    "codontrace.genesis.review.HumanReviewDecision": ("review_result_digest",),
    "codontrace.genesis.review.LLMReviewResult": ("request_digest",),
    "codontrace.genesis.review.ReviewArtifact": ("digest",),
    "codontrace.genesis.review.ReviewFinding": ("artifact_digest",),
    "codontrace.genesis.ribosome.CodonExecutionRecord": ("context_digest",),
    "codontrace.genesis.rules.ApprovedRuleApplicationResult": ("approved_rule_set_digest",),
    "codontrace.genesis.rules.HumanApprovalRecord": ("proposal_digest", "validation_digest"),
    "codontrace.genesis.rules.RuleValidationResult": ("proposal_digest",),
    "codontrace.genesis.scientific_evidence.AblationEvidenceSummary": ("comparison_digest",),
    "codontrace.genesis.scientific_evidence.D0EvidenceSummary": ("baseline_digest",),
    "codontrace.genesis.scientific_evidence.QDEvidenceSummary": (
        "archive_digest",
        "descriptor_schema_digest",
    ),
    "codontrace.genesis.scientific_evidence.ScientificEvidencePack": (
        "validation_matrix_digest",
        "claim_audit_digest",
        "replay_digest",
    ),
    "codontrace.genesis.social.SocialInteractionEvent": (
        "world_state_before_digest",
        "world_state_after_digest",
    ),
    "codontrace.genesis.scientific_evidence.WitnessEvidenceSummary": (
        "witness_digest",
        "baseline_digest",
        "trace_digest",
        "replay_digest",
        "ablation_validation_digest",
    ),
    "codontrace.genesis.selection.EvolutionSelectionResult": (
        "config_digest",
        "fitness_scores_digest",
        "novelty_scores_digest",
        "descriptor_digest",
    ),
    "codontrace.genesis.statistical_protocol.OEEMetricsReport": ("threshold_digest", "digest"),
    "codontrace.genesis.statistical_report.StatisticalExperimentReport": ("protocol_digest",),
    "codontrace.genesis.toolchain.ToolChainRecord": (
        "state_digest",
        "world_state_before_digest",
        "world_state_after_digest",
        "effect_digest",
    ),
    "codontrace.genesis.structural_mutation.GenomeProgram": (
        "macro_registry_digest",
        "structural_mutation_digest",
        "digest",
        "identity_digest",
        "provenance_digest",
        "artifact_digest",
    ),
    "codontrace.genesis.structural_mutation.StructuralMutationRecord": (
        "parent_genome_digest",
        "child_genome_digest",
        "payload_digest",
        "digest",
        "child_genome_identity_digest",
        "child_genome_provenance_digest",
        "before_tokens_digest",
        "after_tokens_digest",
    ),
    "codontrace.genesis.translation_profile.SemanticProxyReport": (
        "behavior_delta_digest",
        "digest",
    ),
    "codontrace.genesis.translation_profile.TranslationProfile": ("genome_spec_digest", "digest"),
    "codontrace.genesis.translation_profile.TranslationUpdateRecord": ("digest",),
    "codontrace.replay.ReplayResult": ("trace_digest", "world_digest", "agent_digest"),
    "codontrace.replay.TimelineReplayResult": (
        "trace_digest",
        "bundle_digest",
        "world_digest",
        "frames_digest",
    ),
    "codontrace.scenario.Scenario": ("initial_world_digest", "initial_agent_digest"),
    "codontrace.simulation.SimulationResult": ("world_digest", "trace_digest"),
    "codontrace.trace.TraceEvent": ("genome_digest",),
}


# Phase 2 strict AI-team feature-gap surfaces: these dataclasses carry digest-like
# fields and must be explicitly accounted for by replay policy sweeps. They are
# currently reference/protocol objects rather than replay-critical proof artifacts
# unless wrapped by validated manifests, ClaimGate decisions, or executed pilots.
_PHASE2_FEATURE_GAP_DIGEST_FIELDS: dict[str, tuple[str, ...]] = {
    "codontrace.genesis.causal_validation.InterventionSpec": (
        "baseline_config_digest",
        "treatment_config_digest",
        "seed_family_digest",
    ),
    "codontrace.genesis.causal_validation.CounterfactualReplaySpec": (
        "baseline_replay_digest",
        "expected_treatment_digest",
    ),
    "codontrace.genesis.causal_validation.CausalInterventionRunPair": (
        "baseline_digest",
        "treatment_digest",
    ),
    "codontrace.genesis.checkpointing.RunCheckpoint": (
        "manifest_digest",
        "snapshot_digest",
        "rng_state_digest",
    ),
    "codontrace.genesis.checkpointing.CheckpointResumeSpec": (
        "checkpoint_digest",
        "expected_continuation_digest",
    ),
    "codontrace.genesis.checkpointing.SeedSweepSpec": ("scenario_digest",),
    "codontrace.genesis.checkpointing.SeedSweepResult": ("spec_digest",),
    "codontrace.genesis.checkpointing.LongRunIntegrityReport": (
        "checkpoint_digest",
        "resume_digest",
        "per_seed_artifact_manifest_digest",
    ),
    "codontrace.genesis.collective_intelligence.CollectiveTaskSpec": (
        "heldout_partner_protocol_digest",
    ),
    "codontrace.genesis.collective_intelligence.RoleComplementarityRecord": (
        "evidence_digest",
    ),
    "codontrace.genesis.collective_intelligence.CollectiveAblationRecord": (
        "baseline_digest",
        "ablated_digest",
    ),
    "codontrace.genesis.collective_intelligence.CollectiveIntelligenceEvidenceReport": (
        "familiar_partner_digest",
        "unfamiliar_partner_digest",
        "replay_digest",
        "digest",
    ),
    "codontrace.genesis.curriculum.EnvironmentLineageRecord": (
        "parent_environment_digest",
        "child_environment_digest",
        "mutation_spec_digest",
    ),
    "codontrace.genesis.curriculum.ChallengeNoveltyReport": (
        "challenge_digest",
        "baseline_digest",
    ),
    "codontrace.genesis.curriculum.EnvironmentAgentTransferRecord": (
        "agent_digest",
        "source_environment_digest",
        "target_environment_digest",
    ),
    "codontrace.genesis.open_endedness.OEECandidateMetrics": ("replay_digest", "d0_baseline_digest", "shadow_digest", "digest"),
    "codontrace.genesis.quality_diversity.ParetoEliteRecord": ("artifact_digest",),
    "codontrace.genesis.quality_diversity.QDTradeoffReport": ("archive_digest",),
    "codontrace.genesis.swarm_metrics.SwarmMetricReport": ("digest",),
}

for _path, _fields in _PHASE2_FEATURE_GAP_DIGEST_FIELDS.items():
    _DIGEST_FIELDS_BY_CLASS[_path] = _fields



# Phase 3 maximum scientific validation surfaces. These are protocol/manifest
# objects; their digest fields are explicit references and are not sufficient to
# unlock claims unless the referenced artifact itself is validated.
_PHASE3_MAX_VALIDATION_DIGEST_FIELDS: dict[str, tuple[str, ...]] = {
    "codontrace.genesis.adf_runtime.ADFCompressionReport": ("source_map_digest", "runtime_effect_digest"),
    "codontrace.genesis.campaign.Phase3CampaignManifest": ("campaign_spec_digest", "run_records_digest", "summary_digest", "claim_manifest_digest", "replay_bundle_digest"),
    "codontrace.genesis.campaign.Phase3CampaignResult": ("claim_manifest_digest", "replay_bundle_digest"),
    "codontrace.genesis.campaign.Phase3ExperimentLedger": ("campaign_digest", "evidence_lineage_digest", "claim_manifest_digest"),
    "codontrace.genesis.campaign.Phase3RunRecord": ("manifest_digest", "replay_bundle_digest"),
    "codontrace.genesis.campaign.Phase3ScenarioSpec": ("config_digest", "world_digest"),
    "codontrace.genesis.checkpointing.CheckpointRecord": ("behavior_digest",),
    "codontrace.genesis.checkpointing.ResumeValidationRecord": ("checkpoint_digest", "continuous_digest", "resumed_digest"),
    "codontrace.genesis.collective_intelligence.DivisionOfLaborReport": ("stable_role_digest", "heldout_digest"),
    "codontrace.genesis.final_release_manifest.FinalClaimManifest": ("replay_bundle_digest", "claim_gate_decision_digest"),
    "codontrace.genesis.final_release_manifest.ReleaseEvidencePack": ("replay_bundle_index_digest", "ablation_matrix_digest", "validation_result_digest"),
    "codontrace.genesis.final_release_manifest.ReplayBundleIndex": ("seed_plan_digest", "config_digest"),
    "codontrace.genesis.final_release_manifest.BenchmarkLeaderboardArtifact": ("seed_policy_digest",),
    "codontrace.genesis.final_release_manifest.AblationMatrixArtifact": ("baseline_digest", "treatment_digest"),
    "codontrace.genesis.final_release_manifest.ClaimDowngradeReport": ("claim_gate_digest",),
    "codontrace.genesis.final_release_manifest.NegativeResultReport": ("claim_gate_digest", "replay_digest"),
    "codontrace.genesis.final_release_manifest.Phase3ScientificSummary": ("replay_bundle_index_digest", "benchmark_leaderboard_digest", "ablation_matrix_digest"),
    "codontrace.genesis.open_endedness.LearnabilityReport": ("heldout_digest", "replay_digest"),
    "codontrace.genesis.open_endedness.PersistenceReport": ("persistence_digest",),
    "codontrace.genesis.open_endedness.SteppingStoneTransferReport": ("source_environment_digest", "target_environment_digest"),
    "codontrace.genesis.open_endedness.CurriculumCoEvolutionReport": ("curriculum_digest", "agent_population_digest"),
    "codontrace.genesis.open_endedness.D0ShadowBaselineReport": ("d0_baseline_digest", "shadow_digest"),
    "codontrace.genesis.open_endedness.TaskGeneratorSpec": ("generator_digest",),
    "codontrace.genesis.open_endedness.EnvironmentMutationRecord": ("source_environment_digest", "mutated_environment_digest"),
    "codontrace.genesis.plugins.PluginValidationReport": ("plugin_digest",),
    "codontrace.genesis.quality_diversity.CoverageReport": ("archive_digest",),
    "codontrace.genesis.quality_diversity.QDScoreReport": ("archive_digest",),
    "codontrace.genesis.replay.ReplayBundleManifest": ("config_digest", "seed_digest", "source_digest", "environment_digest"),
    "codontrace.genesis.replay.ReplayEquivalenceReport": ("continuous_digest", "resumed_digest"),
    "codontrace.genesis.scale_performance.ScaleBenchmarkReport": ("spec_digest", "semantics_digest"),
    "codontrace.genesis.statistical_protocol.PairedComparisonResult": ("baseline_values_digest", "treatment_values_digest", "paired_seed_digest"),
    "codontrace.genesis.swarm_metrics.SwarmResilienceReport": ("perturbation_digest", "control_digest"),
}
for _path, _fields in _PHASE3_MAX_VALIDATION_DIGEST_FIELDS.items():
    _DIGEST_FIELDS_BY_CLASS[_path] = _fields

NON_REPLAY_CRITICAL_DIGEST_CLASSES = tuple(
    dict.fromkeys((*NON_REPLAY_CRITICAL_DIGEST_CLASSES, *_PHASE2_FEATURE_GAP_DIGEST_FIELDS, *_PHASE3_MAX_VALIDATION_DIGEST_FIELDS))
)


_PLUGIN_SAFETY_DIGEST_FIELDS: dict[str, tuple[str, ...]] = {
    "codontrace.genesis.plugins.PluginManifest": ("config_digest",),
    "codontrace.genesis.plugins.PluginValidationResult": ("plugin_digest",),
}
for _path, _fields in _PLUGIN_SAFETY_DIGEST_FIELDS.items():
    _DIGEST_FIELDS_BY_CLASS[_path] = _fields

NON_REPLAY_CRITICAL_DIGEST_CLASSES = tuple(
    dict.fromkeys((*NON_REPLAY_CRITICAL_DIGEST_CLASSES, *_PLUGIN_SAFETY_DIGEST_FIELDS))
)

# Final Phase-B runtime/scientific evidence surfaces. These are linked into
# GenesisRunResult exports and EvidenceManifest; the digest fields are explicit
# record/artifact identities and never grant claims without ClaimGate review.
_PHASE_B_SCIENTIFIC_MATURITY_DIGEST_FIELDS: dict[str, tuple[str, ...]] = {
    "codontrace.genesis.phase_b_scientific_maturity.PhaseBFeatureMaturityStatus": ("record_digest",),
    "codontrace.genesis.phase_b_scientific_maturity.DiscoveryEvent": ("world_digest", "candidate_behavior_digest", "baseline_d0_digest", "shadow_run_digest", "ablation_witness_digest", "source_package_digest", "record_digest"),
    "codontrace.genesis.phase_b_scientific_maturity.AblationWitness": ("baseline_run_digest", "treatment_run_digest", "record_digest"),
    "codontrace.genesis.phase_b_scientific_maturity.HeldoutEvaluationResult": ("source_run_digest", "lineage_digest", "world_digest", "partner_group_digest", "heldout_result_digest", "record_digest"),
    "codontrace.genesis.phase_b_scientific_maturity.CollectiveSwarmEvidenceLadder": ("record_digest",),
    "codontrace.genesis.phase_b_scientific_maturity.OEEClaimEligibilityResult": ("novelty_baseline_digest", "heldout_learnability_digest", "stepping_stone_source_digest", "stepping_stone_target_digest", "negative_control_digest", "record_digest"),
    "codontrace.genesis.phase_b_scientific_maturity.CurriculumEnvironmentRecord": ("parent_environment_digest", "task_spec_digest", "agent_transfer_digest", "record_digest"),
    "codontrace.genesis.phase_b_scientific_maturity.ScaleBenchmarkReport": ("checkpoint_digest", "resume_digest", "record_digest"),
    "codontrace.genesis.phase_b_scientific_maturity.StatisticalClaimValidationResult": ("preregistered_metric_digest", "multiple_comparison_audit_digest", "negative_result_digest", "record_digest"),
    "codontrace.genesis.phase_b_scientific_maturity.PluginValidationResult": ("config_digest", "record_digest"),
    "codontrace.genesis.phase_b_scientific_maturity.ReleaseEvidencePackSample": ("phase1_runtime_maturity_digest", "discovery_digest", "ablation_digest", "generalization_digest", "oee_digest", "statistical_digest", "replay_bundle_digest", "claim_manifest_digest", "evidence_lineage_dag_digest", "record_digest"),
    "codontrace.genesis.phase_b_scientific_maturity.PhaseBScientificMaturityReport": ("source_result_digest", "phase1_runtime_maturity_digest", "record_digest"),
}
for _path, _fields in _PHASE_B_SCIENTIFIC_MATURITY_DIGEST_FIELDS.items():
    _DIGEST_FIELDS_BY_CLASS[_path] = _fields

NON_REPLAY_CRITICAL_DIGEST_CLASSES = tuple(
    dict.fromkeys((*NON_REPLAY_CRITICAL_DIGEST_CLASSES, *_PHASE_B_SCIENTIFIC_MATURITY_DIGEST_FIELDS))
)


def build_replay_digest_class_policy(class_path: str) -> ReplayDigestClassPolicy:
    """Return the explicit replay/evidence policy for a digest-bearing class."""

    fields = _DIGEST_FIELDS_BY_CLASS[class_path]
    if class_path in STRICT_REPLAY_CRITICAL_DIGEST_CLASSES:
        return ReplayDigestClassPolicy(
            class_path=class_path,
            digest_fields=fields,
            replay_role="replay_critical",
            evidence_role="validated_artifact_or_gate_input",
            validation_mode="constructor_or_factory_must_validate_digest",
            rationale=(
                "This object can participate in replay identity, scientific claim gates, "
                "or artifact evidence. Caller-supplied digest values must be recomputed "
                "or rejected by construction/factory logic."
            ),
        )
    if class_path in NON_REPLAY_CRITICAL_DIGEST_CLASSES:
        return ReplayDigestClassPolicy(
            class_path=class_path,
            digest_fields=fields,
            replay_role="non_replay_critical",
            evidence_role="reference_or_summary_only_not_scientific_evidence",
            validation_mode="excluded_from_claim_granting_without_validated_artifact",
            rationale=(
                "Digest-like fields here are references, snapshots, summaries, or externally "
                "computed identifiers. They are explicitly not sufficient to grant scientific "
                "claims unless wrapped by a validated replay-critical artifact."
            ),
        )
    raise KeyError(f"No replay digest policy registered for {class_path}")


def replay_digest_class_policies() -> tuple[ReplayDigestClassPolicy, ...]:
    """Return all explicit digest-class policies in deterministic order."""

    paths = sorted((*STRICT_REPLAY_CRITICAL_DIGEST_CLASSES, *NON_REPLAY_CRITICAL_DIGEST_CLASSES))
    return tuple(build_replay_digest_class_policy(path) for path in paths)


def public_dataclass_digest_fields(class_obj: type[Any]) -> tuple[str, ...]:
    """Return digest-like dataclass field names for a class object."""

    fields = getattr(class_obj, "__dataclass_fields__", {})
    return tuple(name for name in fields if name == "digest" or name.endswith("_digest"))


def resolve_class_path(class_path: str) -> type[Any]:
    """Import and return a class from its fully qualified path."""

    if "." not in class_path:
        raise ValueError(f"Invalid class path (no module separator): {class_path!r}")

    module_name, _, class_name = class_path.rpartition(".")
    if not module_name or not class_name:
        raise ValueError(f"Invalid class path: {class_path!r}")

    module = import_module(module_name)
    cls = getattr(module, class_name)
    if not isclass(cls):
        raise TypeError(f"{class_path} does not resolve to a class")
    return cls


def audit_replay_digest_policy_registry() -> tuple[str, ...]:
    """Validate that the explicit registry matches importable dataclass fields.

    Returns an empty tuple when the registry is complete. Each returned string is
    a deterministic human-readable audit finding.
    """

    findings: list[str] = []
    all_paths = (*STRICT_REPLAY_CRITICAL_DIGEST_CLASSES, *NON_REPLAY_CRITICAL_DIGEST_CLASSES)
    if len(set(all_paths)) != len(all_paths):
        findings.append("duplicate_class_policy")
    for path in sorted(all_paths):
        try:
            cls = resolve_class_path(path)
        except Exception as exc:  # pragma: no cover - defensive audit branch
            findings.append(f"unresolvable:{path}:{exc.__class__.__name__}")
            continue
        actual = public_dataclass_digest_fields(cls)
        expected = _DIGEST_FIELDS_BY_CLASS.get(path)
        if actual != expected:
            findings.append(f"digest_field_mismatch:{path}:expected={expected}:actual={actual}")
        policy = build_replay_digest_class_policy(path)
        if policy.replay_critical and not hasattr(cls, "__post_init__"):
            findings.append(f"replay_critical_without_post_init:{path}")
    return tuple(findings)

# Integration integration/reference/evidence hardening surfaces.  These audit records
# are not claim-positive by themselves; they make package integrity, public API,
# runtime wiring, and evidence consistency replay-visible.
_PLAN_C_HARDENING_DIGEST_FIELDS: dict[str, tuple[str, ...]] = {
    "codontrace.genesis.public_api_manifest.IntegrationPublicAPISymbol": ("schema_digest",),
    "codontrace.genesis.runtime_wiring_audit.RuntimeWiringFeature": ("record_digest",),
    "codontrace.genesis.evidence_consistency.EvidenceConsistencyIssue": ("record_digest",),
}
for _path, _fields in _PLAN_C_HARDENING_DIGEST_FIELDS.items():
    _DIGEST_FIELDS_BY_CLASS[_path] = _fields

NON_REPLAY_CRITICAL_DIGEST_CLASSES = tuple(
    dict.fromkeys((*NON_REPLAY_CRITICAL_DIGEST_CLASSES, *_PLAN_C_HARDENING_DIGEST_FIELDS))
)

_CAUSAL_MECHANISM_HARDENING_DIGEST_FIELDS: tuple[str, ...] = (
    "codontrace.genesis.capsule_validation.CapsuleAblationPolicy",
    "codontrace.genesis.capsule_validation.CapsuleOutcomeWindow",
    "codontrace.genesis.capsule_validation.CapsuleDelayedOutcomeRecord",
    "codontrace.genesis.memory.SignalMemoryCausalLinkRecord",
    "codontrace.genesis.memory.SourceReputationMemory",
    "codontrace.genesis.birth.SkillCompressionAblationPolicy",
    "codontrace.genesis.birth.ChildOutcomeAuditRecord",
    "codontrace.genesis.role.RoleMechanicsPolicy",
    "codontrace.genesis.role.TerritoryMechanicsConfig",
    "codontrace.genesis.role.TerritoryDefenseRecord",
    "codontrace.genesis.collective_intelligence.CollectiveTaskNode",
    "codontrace.genesis.collective_intelligence.RoleDependencyEdge",
    "codontrace.genesis.collective_intelligence.CollectiveTaskGraph",
    "codontrace.genesis.collective_intelligence.JointTaskProgressRecord",
    "codontrace.genesis.collective_intelligence.RoleAblationProtocol",
    "codontrace.genesis.generalization.HeldoutPartnerEvaluationProtocol",
    "codontrace.genesis.generalization.HeldoutPartnerEvaluationRecord",
    "codontrace.genesis.contribution_ledger.MultiAgentContributionRecord",
    "codontrace.genesis.contribution_ledger.MultiAgentContributionLedger",
    "codontrace.genesis.intervention.CounterfactualReplayProtocol",
    "codontrace.genesis.intervention.CounterfactualReplayResult",
    "codontrace.genesis.open_endedness.OEEExtendedMetrics",
)
NON_REPLAY_CRITICAL_DIGEST_CLASSES = tuple(
    dict.fromkeys((*NON_REPLAY_CRITICAL_DIGEST_CLASSES, *_CAUSAL_MECHANISM_HARDENING_DIGEST_FIELDS))
)
_CAUSAL_MECHANISM_HARDENING_DIGEST_FIELD_MAP: dict[str, tuple[str, ...]] = {
    "codontrace.genesis.capsule_validation.CapsuleAblationPolicy": (),
    "codontrace.genesis.capsule_validation.CapsuleOutcomeWindow": (),
    "codontrace.genesis.capsule_validation.CapsuleDelayedOutcomeRecord": ("window_digest", "policy_digest", "compared_control_digest", "record_digest"),
    "codontrace.genesis.memory.SignalMemoryCausalLinkRecord": ("memory_record_digest", "action_record_digest", "control_digest", "record_digest"),
    "codontrace.genesis.memory.SourceReputationMemory": (),
    "codontrace.genesis.birth.SkillCompressionAblationPolicy": (),
    "codontrace.genesis.birth.ChildOutcomeAuditRecord": ("compression_digest", "control_digest", "record_digest"),
    "codontrace.genesis.role.RoleMechanicsPolicy": (),
    "codontrace.genesis.role.TerritoryMechanicsConfig": (),
    "codontrace.genesis.role.TerritoryDefenseRecord": ("evidence_digest", "record_digest"),
    "codontrace.genesis.collective_intelligence.CollectiveTaskNode": (),
    "codontrace.genesis.collective_intelligence.RoleDependencyEdge": (),
    "codontrace.genesis.collective_intelligence.CollectiveTaskGraph": ("single_agent_baseline_digest",),
    "codontrace.genesis.collective_intelligence.JointTaskProgressRecord": ("graph_digest", "evidence_digest"),
    "codontrace.genesis.collective_intelligence.RoleAblationProtocol": (),
    "codontrace.genesis.generalization.HeldoutPartnerEvaluationProtocol": (),
    "codontrace.genesis.generalization.HeldoutPartnerEvaluationRecord": ("protocol_digest", "familiar_partner_digest", "unfamiliar_partner_digest", "record_digest"),
    "codontrace.genesis.contribution_ledger.MultiAgentContributionRecord": ("evidence_digest",),
    "codontrace.genesis.contribution_ledger.MultiAgentContributionLedger": (),
    "codontrace.genesis.intervention.CounterfactualReplayProtocol": ("base_replay_digest",),
    "codontrace.genesis.intervention.CounterfactualReplayResult": ("protocol_digest", "base_replay_digest", "counterfactual_replay_digest", "intervention_manifest_digest", "record_digest"),
    "codontrace.genesis.open_endedness.OEEExtendedMetrics": ("baseline_digest", "negative_control_digest", "record_digest"),
}
for _path, _fields in _CAUSAL_MECHANISM_HARDENING_DIGEST_FIELD_MAP.items():
    _DIGEST_FIELDS_BY_CLASS[_path] = _fields
# Only dataclasses with public digest-like fields belong in replay policy sweeps.
# Digest-capable pure policy/config objects with no *_digest field stay importable
# and deterministic via .digest(), but are not part of the dataclass digest-field
# registry used by the strict sweep.
_CAUSAL_MECHANISM_POLICY_ONLY_CLASSES = {
    "codontrace.genesis.capsule_validation.CapsuleAblationPolicy",
    "codontrace.genesis.capsule_validation.CapsuleOutcomeWindow",
    "codontrace.genesis.birth.SkillCompressionAblationPolicy",
    "codontrace.genesis.role.RoleMechanicsPolicy",
    "codontrace.genesis.role.TerritoryMechanicsConfig",
    "codontrace.genesis.collective_intelligence.CollectiveTaskNode",
    "codontrace.genesis.collective_intelligence.RoleDependencyEdge",
    "codontrace.genesis.collective_intelligence.RoleAblationProtocol",
    "codontrace.genesis.generalization.HeldoutPartnerEvaluationProtocol",
    "codontrace.genesis.memory.SourceReputationMemory",
    "codontrace.genesis.contribution_ledger.MultiAgentContributionLedger",
}
NON_REPLAY_CRITICAL_DIGEST_CLASSES = tuple(
    path for path in NON_REPLAY_CRITICAL_DIGEST_CLASSES if path not in _CAUSAL_MECHANISM_POLICY_ONLY_CLASSES
)
for _path in _CAUSAL_MECHANISM_POLICY_ONLY_CLASSES:
    _DIGEST_FIELDS_BY_CLASS.pop(_path, None)
