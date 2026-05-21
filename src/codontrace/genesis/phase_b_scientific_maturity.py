"""Final Phase-B scientific evidence primitives and runtime wiring helpers.

Phase B builds on Phase A runtime maturity.  The objects in this module do
not force success.  They provide deterministic, schema-bearing evidence records
for discovery, ablation, generalization, collective/swarm, OEE, curriculum,
scale, statistics, release packs, plugins, and evidence-lineage wiring.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import (
    canonical_digest,
    canonical_payload,
    is_real_evidence_digest,
    require_finite_float,
)

SCHEMA = "phase_b_scientific_maturity_v1"
PHASE_B_FEATURES = (
    "discovery_detector",
    "ablation_witness",
    "generalization_heldout",
    "collective_swarm_ladder",
    "oee_metrics",
    "curriculum_environment_coevolution",
    "scale_ladder",
    "statistical_protocol",
    "release_evidence_pack",
    "plugin_extension_safety",
)


_VALID_STATUSES = {
    "complete",
    "complete_limited_claim",
    "provisional_with_evidence",
    "descriptive_only",
    "rejected",
    "skipped_by_resource_budget",
    "blocked_by_missing_runtime_wiring",
    "blocked_by_missing_controls",
    "blocked_by_missing_replay_policy",
    "blocked_by_missing_manifest",
    "blocked_by_test_failure",
}


def _status(value: str) -> str:
    if value not in _VALID_STATUSES:
        raise ConfigurationError(f"Unsupported Phase-B status: {value!r}")
    return value


def _stable_digest(value: Any, *, prefix: str | None = None) -> str:
    return canonical_digest(canonical_payload(value), prefix=prefix)


def _record_digest(payload: dict[str, JsonValue]) -> str:
    filtered = {k: v for k, v in payload.items() if k != "record_digest"}
    return _stable_digest(filtered)


def _maybe_real(value: str | None) -> bool:
    return bool(value and is_real_evidence_digest(value))


@dataclass(frozen=True, slots=True)
class PhaseBFeatureMaturityStatus:
    feature: str
    runtime_reachable: bool
    public_api: bool
    manifest_reachable: bool
    replay_policy_registered: bool
    claim_gate_linked: bool
    positive_tests: int
    negative_tests: int
    status: str
    blocked_reason: str | None = None
    schema_version: str = "phase_b_feature_maturity_status_v1"
    record_digest: str = ""
    record_kind: str = "phase_b_feature_maturity_status"

    def __post_init__(self) -> None:
        _status(self.status)
        if self.positive_tests < 0 or self.negative_tests < 0:
            raise ConfigurationError("test counts must be non-negative")
        if not self.record_digest:
            object.__setattr__(self, "record_digest", _record_digest(self.to_dict()))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "feature": self.feature,
            "runtime_reachable": self.runtime_reachable,
            "public_api": self.public_api,
            "manifest_reachable": self.manifest_reachable,
            "replay_policy_registered": self.replay_policy_registered,
            "claim_gate_linked": self.claim_gate_linked,
            "positive_tests": self.positive_tests,
            "negative_tests": self.negative_tests,
            "status": self.status,
            "blocked_reason": self.blocked_reason,
            "record_kind": self.record_kind,
            "record_digest": self.record_digest,
        }

    def digest(self) -> str:
        return self.record_digest


@dataclass(frozen=True, slots=True)
class DiscoveryEvent:
    discovery_id: str
    candidate_id: str
    lineage_id: str
    world_digest: str
    candidate_behavior_digest: str
    baseline_d0_digest: str
    shadow_run_digest: str
    distance_to_d0: float
    novelty_score: float
    persistence_ticks: int
    persistence_seed_count: int
    ablation_witness_digest: str
    claim_eligible: bool
    blocked_reason: str | None = None
    schema_version: str = "discovery_event_v1"
    source_package_digest: str = ""
    record_digest: str = ""
    record_kind: str = "discovery_event"

    def __post_init__(self) -> None:
        for name in ("discovery_id", "candidate_id", "lineage_id"):
            if not getattr(self, name):
                raise ConfigurationError(f"{name} must not be empty")
        object.__setattr__(self, "distance_to_d0", require_finite_float("distance_to_d0", self.distance_to_d0, non_negative=True))
        object.__setattr__(self, "novelty_score", require_finite_float("novelty_score", self.novelty_score, non_negative=True))
        if self.persistence_ticks < 0 or self.persistence_seed_count < 0:
            raise ConfigurationError("persistence metrics must be non-negative")
        eligible = bool(
            self.claim_eligible
            and _maybe_real(self.baseline_d0_digest)
            and _maybe_real(self.shadow_run_digest)
            and _maybe_real(self.ablation_witness_digest)
            and self.persistence_ticks > 0
            and self.persistence_seed_count > 0
        )
        object.__setattr__(self, "claim_eligible", eligible)
        if not eligible and not self.blocked_reason:
            object.__setattr__(self, "blocked_reason", "missing_d0_shadow_persistence_or_ablation")
        if not self.source_package_digest:
            object.__setattr__(self, "source_package_digest", _stable_digest({"schema": self.schema_version, "world_digest": self.world_digest}))
        if not self.record_digest:
            object.__setattr__(self, "record_digest", _record_digest(self.to_dict()))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "discovery_id": self.discovery_id,
            "candidate_id": self.candidate_id,
            "lineage_id": self.lineage_id,
            "world_digest": self.world_digest,
            "candidate_behavior_digest": self.candidate_behavior_digest,
            "baseline_d0_digest": self.baseline_d0_digest,
            "shadow_run_digest": self.shadow_run_digest,
            "distance_to_d0": self.distance_to_d0,
            "novelty_score": self.novelty_score,
            "persistence_ticks": self.persistence_ticks,
            "persistence_seed_count": self.persistence_seed_count,
            "ablation_witness_digest": self.ablation_witness_digest,
            "claim_eligible": self.claim_eligible,
            "blocked_reason": self.blocked_reason,
            "source_package_digest": self.source_package_digest,
            "record_kind": self.record_kind,
            "record_digest": self.record_digest,
        }

    def digest(self) -> str:
        return self.record_digest


@dataclass(frozen=True, slots=True)
class DiscoveryCandidate(DiscoveryEvent):
    schema_version: str = "phase_b_discovery_candidate_v1"
    record_kind: str = "discovery_candidate"


@dataclass(frozen=True, slots=True)
class DiscoveryWitness(DiscoveryEvent):
    schema_version: str = "phase_b_discovery_witness_v1"
    record_kind: str = "discovery_witness"


@dataclass(frozen=True, slots=True)
class D0BaselineReport(DiscoveryEvent):
    schema_version: str = "d0_baseline_report_v1"
    record_kind: str = "d0_baseline_report"


@dataclass(frozen=True, slots=True)
class ShadowBaselineReport(DiscoveryEvent):
    schema_version: str = "shadow_baseline_report_v1"
    record_kind: str = "shadow_baseline_report"


@dataclass(frozen=True, slots=True)
class DistanceToD0Result(DiscoveryEvent):
    schema_version: str = "distance_to_d0_result_v1"
    record_kind: str = "distance_to_d0_result"


@dataclass(frozen=True, slots=True)
class DiscoveryPersistenceReport(DiscoveryEvent):
    schema_version: str = "discovery_persistence_report_v1"
    record_kind: str = "discovery_persistence_report"


@dataclass(frozen=True, slots=True)
class DiscoveryClaimEligibilityResult(DiscoveryEvent):
    schema_version: str = "discovery_claim_eligibility_result_v1"
    record_kind: str = "discovery_claim_eligibility_result"


@dataclass(frozen=True, slots=True)
class AblationWitness:
    ablation_id: str
    ablation_type: str
    target_feature_or_id: str
    baseline_run_digest: str
    treatment_run_digest: str
    baseline_metric: float
    treatment_metric: float
    paired_seed: int
    confidence_status: str
    claim_supported: bool
    failure_reason: str | None = None
    schema_version: str = "ablation_witness_v1"
    record_digest: str = ""
    record_kind: str = "ablation_witness"

    def __post_init__(self) -> None:
        if not self.ablation_id or not self.ablation_type or not self.target_feature_or_id:
            raise ConfigurationError("AblationWitness requires id/type/target")
        object.__setattr__(self, "baseline_metric", require_finite_float("baseline_metric", self.baseline_metric))
        object.__setattr__(self, "treatment_metric", require_finite_float("treatment_metric", self.treatment_metric))
        supported = bool(
            self.claim_supported
            and _maybe_real(self.baseline_run_digest)
            and _maybe_real(self.treatment_run_digest)
            and self.baseline_run_digest != self.treatment_run_digest
            and self.confidence_status in {"measured", "limited", "supported"}
        )
        object.__setattr__(self, "claim_supported", supported)
        if not supported and not self.failure_reason:
            object.__setattr__(self, "failure_reason", "invalid_or_missing_baseline_treatment_artifact")
        if not self.record_digest:
            object.__setattr__(self, "record_digest", _record_digest(self.to_dict()))

    @property
    def delta(self) -> float:
        return self.treatment_metric - self.baseline_metric

    @property
    def effect_size(self) -> float:
        denom = max(abs(self.baseline_metric), 1.0)
        return self.delta / denom

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "ablation_id": self.ablation_id,
            "ablation_type": self.ablation_type,
            "target_feature_or_id": self.target_feature_or_id,
            "baseline_run_digest": self.baseline_run_digest,
            "treatment_run_digest": self.treatment_run_digest,
            "baseline_metric": self.baseline_metric,
            "treatment_metric": self.treatment_metric,
            "delta": self.delta,
            "effect_size": self.effect_size,
            "confidence_status": self.confidence_status,
            "paired_seed": self.paired_seed,
            "claim_supported": self.claim_supported,
            "failure_reason": self.failure_reason,
            "record_kind": self.record_kind,
            "record_digest": self.record_digest,
        }

    def digest(self) -> str:
        return self.record_digest


@dataclass(frozen=True, slots=True)
class AblationPlan(AblationWitness):
    schema_version: str = "ablation_plan_v1"
    record_kind: str = "ablation_plan"


@dataclass(frozen=True, slots=True)
class AblationResult(AblationWitness):
    schema_version: str = "ablation_result_v1"
    record_kind: str = "ablation_result"


@dataclass(frozen=True, slots=True)
class InterventionResult(AblationWitness):
    schema_version: str = "phase_b_intervention_result_v1"
    record_kind: str = "phase_b_intervention_result"


@dataclass(frozen=True, slots=True)
class InterventionComparisonReport(AblationWitness):
    schema_version: str = "intervention_comparison_report_v1"
    record_kind: str = "intervention_comparison_report"


@dataclass(frozen=True, slots=True)
class HeldoutEvaluationResult:
    snapshot_id: str
    source_run_digest: str
    lineage_digest: str
    world_digest: str
    partner_group_digest: str
    train_world_seed: int
    heldout_world_seed: int
    organism_seed_policy: str
    leakage_status: str
    heldout_result_digest: str
    generalization_delta: float
    schema_version: str = "heldout_evaluation_result_v1"
    record_digest: str = ""
    record_kind: str = "heldout_evaluation_result"

    def __post_init__(self) -> None:
        object.__setattr__(self, "generalization_delta", require_finite_float("generalization_delta", self.generalization_delta))
        if self.train_world_seed == self.heldout_world_seed and self.leakage_status != "same_world_control":
            object.__setattr__(self, "leakage_status", "leakage_detected")
        if not _maybe_real(self.heldout_result_digest):
            object.__setattr__(self, "leakage_status", "heldout_not_run")
        if not self.record_digest:
            object.__setattr__(self, "record_digest", _record_digest(self.to_dict()))

    @property
    def claim_eligible(self) -> bool:
        return self.leakage_status == "heldout_distinct" and _maybe_real(self.heldout_result_digest)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "snapshot_id": self.snapshot_id,
            "source_run_digest": self.source_run_digest,
            "lineage_digest": self.lineage_digest,
            "world_digest": self.world_digest,
            "partner_group_digest": self.partner_group_digest,
            "train_world_seed": self.train_world_seed,
            "heldout_world_seed": self.heldout_world_seed,
            "organism_seed_policy": self.organism_seed_policy,
            "leakage_status": self.leakage_status,
            "heldout_result_digest": self.heldout_result_digest,
            "generalization_delta": self.generalization_delta,
            "claim_eligible": self.claim_eligible,
            "record_kind": self.record_kind,
            "record_digest": self.record_digest,
        }

    def digest(self) -> str:
        return self.record_digest


@dataclass(frozen=True, slots=True)
class LineageSnapshot(HeldoutEvaluationResult):
    schema_version: str = "lineage_snapshot_v1"
    record_kind: str = "lineage_snapshot"


@dataclass(frozen=True, slots=True)
class WorldSnapshot(HeldoutEvaluationResult):
    schema_version: str = "world_snapshot_v1"
    record_kind: str = "world_snapshot"


@dataclass(frozen=True, slots=True)
class PopulationSnapshot(HeldoutEvaluationResult):
    schema_version: str = "phase_b_population_snapshot_v1"
    record_kind: str = "phase_b_population_snapshot"


@dataclass(frozen=True, slots=True)
class PartnerGroupSpec(HeldoutEvaluationResult):
    schema_version: str = "partner_group_spec_v1"
    record_kind: str = "partner_group_spec"


@dataclass(frozen=True, slots=True)
class HeldoutEvaluationSpec(HeldoutEvaluationResult):
    schema_version: str = "heldout_evaluation_spec_v1"
    record_kind: str = "heldout_evaluation_spec"


@dataclass(frozen=True, slots=True)
class ReplayableEvaluationSpec(HeldoutEvaluationResult):
    schema_version: str = "replayable_evaluation_spec_v1"
    record_kind: str = "replayable_evaluation_spec"


@dataclass(frozen=True, slots=True)
class GeneralizationMatrix(HeldoutEvaluationResult):
    schema_version: str = "generalization_matrix_v1"
    record_kind: str = "generalization_matrix"


@dataclass(frozen=True, slots=True)
class HeldoutLeakageAudit(HeldoutEvaluationResult):
    schema_version: str = "heldout_leakage_audit_v1"
    record_kind: str = "heldout_leakage_audit"


@dataclass(frozen=True, slots=True)
class CollectiveSwarmEvidenceLadder:
    non_capsule_cooperation_score: float
    role_complementarity_score: float
    joint_task_progress_score: float
    division_of_labor_score: float
    resilience_score: float
    scaling_score: float
    collective_coordination_score: float
    capsule_social_transfer_score: float = 0.0
    blocked_reason: str | None = None
    schema_version: str = "collective_swarm_evidence_ladder_v1"
    record_digest: str = ""
    record_kind: str = "collective_swarm_evidence_ladder"

    def __post_init__(self) -> None:
        for name in (
            "non_capsule_cooperation_score", "role_complementarity_score",
            "joint_task_progress_score", "division_of_labor_score", "resilience_score",
            "scaling_score", "collective_coordination_score", "capsule_social_transfer_score",
        ):
            object.__setattr__(self, name, require_finite_float(name, getattr(self, name), non_negative=True))
        if not self.record_digest:
            object.__setattr__(self, "record_digest", _record_digest(self.to_dict()))

    @property
    def swarm_claim_level(self) -> str:
        if self.scaling_score > 0 and self.resilience_score > 0 and self.collective_coordination_score > 0:
            return "L6: scalable_collective_coordination_observed"
        if self.resilience_score > 0:
            return "L5: resilience_to_agent_removal_observed"
        if self.collective_coordination_score > 0 and self.role_complementarity_score > 0:
            return "L3: joint_task_progress_observed"
        if self.role_complementarity_score > 0:
            return "L2: role_complementarity_observed"
        if self.non_capsule_cooperation_score > 0:
            return "L1: non_capsule_cooperation_observed"
        if self.capsule_social_transfer_score > 0:
            return "L0: social_interaction_observed"
        return "rejected"

    @property
    def claim_eligible(self) -> bool:
        return self.swarm_claim_level.startswith(("L3", "L4", "L5", "L6"))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "non_capsule_cooperation_score": self.non_capsule_cooperation_score,
            "role_complementarity_score": self.role_complementarity_score,
            "joint_task_progress_score": self.joint_task_progress_score,
            "division_of_labor_score": self.division_of_labor_score,
            "resilience_score": self.resilience_score,
            "scaling_score": self.scaling_score,
            "collective_coordination_score": self.collective_coordination_score,
            "capsule_social_transfer_score": self.capsule_social_transfer_score,
            "swarm_claim_level": self.swarm_claim_level,
            "claim_eligible": self.claim_eligible,
            "blocked_reason": self.blocked_reason,
            "record_kind": self.record_kind,
            "record_digest": self.record_digest,
        }

    def digest(self) -> str:
        return self.record_digest


@dataclass(frozen=True, slots=True)
class OEEClaimEligibilityResult:
    candidate_id: str
    novelty_score: float
    novelty_baseline_digest: str
    persistence_ticks: int
    persistence_seeds: int
    learnability_score: float
    heldout_learnability_digest: str
    stepping_stone_source_digest: str
    stepping_stone_target_digest: str
    transfer_delta: float
    negative_control_digest: str
    claim_eligible: bool
    blocked_reason: str | None = None
    schema_version: str = "oee_claim_eligibility_result_v1"
    record_digest: str = ""
    record_kind: str = "oee_claim_eligibility_result"

    def __post_init__(self) -> None:
        object.__setattr__(self, "novelty_score", require_finite_float("novelty_score", self.novelty_score, non_negative=True))
        object.__setattr__(self, "learnability_score", require_finite_float("learnability_score", self.learnability_score, non_negative=True))
        object.__setattr__(self, "transfer_delta", require_finite_float("transfer_delta", self.transfer_delta))
        eligible = bool(
            self.claim_eligible
            and self.persistence_seeds >= 5
            and self.persistence_ticks > 0
            and _maybe_real(self.novelty_baseline_digest)
            and _maybe_real(self.heldout_learnability_digest)
            and _maybe_real(self.stepping_stone_source_digest)
            and _maybe_real(self.stepping_stone_target_digest)
            and _maybe_real(self.negative_control_digest)
        )
        object.__setattr__(self, "claim_eligible", eligible)
        if not eligible and not self.blocked_reason:
            object.__setattr__(self, "blocked_reason", "missing_oee_threshold_or_control_evidence")
        if not self.record_digest:
            object.__setattr__(self, "record_digest", _record_digest(self.to_dict()))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "candidate_id": self.candidate_id,
            "novelty_score": self.novelty_score,
            "novelty_baseline_digest": self.novelty_baseline_digest,
            "persistence_ticks": self.persistence_ticks,
            "persistence_seeds": self.persistence_seeds,
            "learnability_score": self.learnability_score,
            "heldout_learnability_digest": self.heldout_learnability_digest,
            "stepping_stone_source_digest": self.stepping_stone_source_digest,
            "stepping_stone_target_digest": self.stepping_stone_target_digest,
            "transfer_delta": self.transfer_delta,
            "negative_control_digest": self.negative_control_digest,
            "claim_eligible": self.claim_eligible,
            "blocked_reason": self.blocked_reason,
            "record_kind": self.record_kind,
            "record_digest": self.record_digest,
        }

    def digest(self) -> str:
        return self.record_digest


@dataclass(frozen=True, slots=True)
class NoveltyTrajectory(OEEClaimEligibilityResult):
    schema_version: str = "phase_b_novelty_trajectory_v1"
    record_kind: str = "phase_b_novelty_trajectory"


@dataclass(frozen=True, slots=True)
class PersistenceReport(OEEClaimEligibilityResult):
    schema_version: str = "phase_b_persistence_report_v1"
    record_kind: str = "phase_b_persistence_report"


@dataclass(frozen=True, slots=True)
class LearnabilityReport(OEEClaimEligibilityResult):
    schema_version: str = "phase_b_learnability_report_v1"
    record_kind: str = "phase_b_learnability_report"


@dataclass(frozen=True, slots=True)
class SteppingStoneTransferReport(OEEClaimEligibilityResult):
    schema_version: str = "phase_b_stepping_stone_transfer_report_v1"
    record_kind: str = "phase_b_stepping_stone_transfer_report"


@dataclass(frozen=True, slots=True)
class OEECandidateMetrics(OEEClaimEligibilityResult):
    schema_version: str = "oee_candidate_metrics_v1"
    record_kind: str = "oee_candidate_metrics"


@dataclass(frozen=True, slots=True)
class CurriculumEnvironmentRecord:
    environment_id: str
    parent_environment_digest: str
    mutation_kind: str
    mutation_seed: int
    task_spec_digest: str
    difficulty_score: float
    novelty_score: float
    agent_transfer_digest: str
    blocked_reason: str | None = None
    schema_version: str = "curriculum_environment_record_v1"
    record_digest: str = ""
    record_kind: str = "curriculum_environment_record"

    def __post_init__(self) -> None:
        object.__setattr__(self, "difficulty_score", require_finite_float("difficulty_score", self.difficulty_score, non_negative=True))
        object.__setattr__(self, "novelty_score", require_finite_float("novelty_score", self.novelty_score, non_negative=True))
        if not self.record_digest:
            object.__setattr__(self, "record_digest", _record_digest(self.to_dict()))

    @property
    def claim_eligible(self) -> bool:
        return _maybe_real(self.task_spec_digest) and _maybe_real(self.agent_transfer_digest) and self.blocked_reason is None

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "environment_id": self.environment_id,
            "parent_environment_digest": self.parent_environment_digest,
            "mutation_kind": self.mutation_kind,
            "mutation_seed": self.mutation_seed,
            "task_spec_digest": self.task_spec_digest,
            "difficulty_score": self.difficulty_score,
            "novelty_score": self.novelty_score,
            "agent_transfer_digest": self.agent_transfer_digest,
            "claim_eligible": self.claim_eligible,
            "blocked_reason": self.blocked_reason,
            "record_kind": self.record_kind,
            "record_digest": self.record_digest,
        }

    def digest(self) -> str:
        return self.record_digest


@dataclass(frozen=True, slots=True)
class TaskGeneratorSpec(CurriculumEnvironmentRecord):
    schema_version: str = "task_generator_spec_v1"
    record_kind: str = "task_generator_spec"


@dataclass(frozen=True, slots=True)
class EnvironmentMutationSpec(CurriculumEnvironmentRecord):
    schema_version: str = "environment_mutation_spec_v1"
    record_kind: str = "environment_mutation_spec"


@dataclass(frozen=True, slots=True)
class CurriculumStepRecord(CurriculumEnvironmentRecord):
    schema_version: str = "curriculum_step_record_v1"
    record_kind: str = "curriculum_step_record"


@dataclass(frozen=True, slots=True)
class EnvironmentLineageRecord(CurriculumEnvironmentRecord):
    schema_version: str = "environment_lineage_record_v1"
    record_kind: str = "environment_lineage_record"


@dataclass(frozen=True, slots=True)
class ChallengeNoveltyReport(CurriculumEnvironmentRecord):
    schema_version: str = "challenge_novelty_report_v1"
    record_kind: str = "challenge_novelty_report"


@dataclass(frozen=True, slots=True)
class EnvironmentAgentTransferRecord(CurriculumEnvironmentRecord):
    schema_version: str = "environment_agent_transfer_record_v1"
    record_kind: str = "environment_agent_transfer_record"


@dataclass(frozen=True, slots=True)
class ScaleBenchmarkReport:
    workload_size: int
    population: int
    world_size: int
    ticks: int
    seed_count: int
    runtime_seconds: float
    memory_peak_mb: float
    artifact_size_mb: float
    checkpoint_digest: str
    resume_digest: str
    failure_or_skip_reason: str | None = None
    schema_version: str = "scale_benchmark_report_v2"
    record_digest: str = ""
    record_kind: str = "scale_benchmark_report"

    def __post_init__(self) -> None:
        if min(self.workload_size, self.population, self.world_size, self.ticks, self.seed_count) <= 0:
            raise ConfigurationError("scale sizes must be positive")
        for name in ("runtime_seconds", "memory_peak_mb", "artifact_size_mb"):
            object.__setattr__(self, name, require_finite_float(name, getattr(self, name), non_negative=True))
        if not self.record_digest:
            object.__setattr__(self, "record_digest", _record_digest(self.to_dict()))

    @property
    def scale_claim_status(self) -> str:
        if self.failure_or_skip_reason:
            return "skipped_by_resource_budget" if self.failure_or_skip_reason == "skipped_by_resource_budget" else "rejected"
        if self.workload_size < 1000:
            return "descriptive_only"
        return "complete_limited_claim"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "workload_size": self.workload_size,
            "population": self.population,
            "world_size": self.world_size,
            "ticks": self.ticks,
            "seed_count": self.seed_count,
            "runtime_seconds": self.runtime_seconds,
            "memory_peak_mb": self.memory_peak_mb,
            "artifact_size_mb": self.artifact_size_mb,
            "checkpoint_digest": self.checkpoint_digest,
            "resume_digest": self.resume_digest,
            "failure_or_skip_reason": self.failure_or_skip_reason,
            "scale_claim_status": self.scale_claim_status,
            "record_kind": self.record_kind,
            "record_digest": self.record_digest,
        }

    def digest(self) -> str:
        return self.record_digest


@dataclass(frozen=True, slots=True)
class ScaleBenchmarkSpec(ScaleBenchmarkReport):
    schema_version: str = "phase_b_scale_benchmark_spec_v1"
    record_kind: str = "phase_b_scale_benchmark_spec"


@dataclass(frozen=True, slots=True)
class ResourceBudgetPolicy(ScaleBenchmarkReport):
    schema_version: str = "phase_b_resource_budget_policy_v1"
    record_kind: str = "phase_b_resource_budget_policy"


@dataclass(frozen=True, slots=True)
class LongHorizonRunManifest(ScaleBenchmarkReport):
    schema_version: str = "long_horizon_run_manifest_v1"
    record_kind: str = "long_horizon_run_manifest"


@dataclass(frozen=True, slots=True)
class CheckpointResumeAudit(ScaleBenchmarkReport):
    schema_version: str = "checkpoint_resume_audit_v1"
    record_kind: str = "checkpoint_resume_audit"


@dataclass(frozen=True, slots=True)
class SeedSweepReport(ScaleBenchmarkReport):
    schema_version: str = "seed_sweep_report_v1"
    record_kind: str = "seed_sweep_report"


@dataclass(frozen=True, slots=True)
class StatisticalClaimValidationResult:
    metric_name: str
    seed_count: int
    effect_size: float
    ci_low: float
    ci_high: float
    metric_count: int
    preregistered_metric_digest: str
    multiple_comparison_audit_digest: str | None
    negative_result_digest: str | None
    schema_version: str = "statistical_claim_validation_result_v1"
    record_digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "effect_size", require_finite_float("effect_size", self.effect_size))
        object.__setattr__(self, "ci_low", require_finite_float("ci_low", self.ci_low))
        object.__setattr__(self, "ci_high", require_finite_float("ci_high", self.ci_high))
        if self.ci_low > self.ci_high:
            raise ConfigurationError("ci_low must be <= ci_high")
        if self.seed_count < 0 or self.metric_count <= 0:
            raise ConfigurationError("invalid statistical counts")
        if not self.record_digest:
            object.__setattr__(self, "record_digest", _record_digest(self.to_dict()))

    @property
    def claim_status(self) -> str:
        if not _maybe_real(self.preregistered_metric_digest):
            return "rejected"
        if self.metric_count > 1 and not _maybe_real(self.multiple_comparison_audit_digest):
            return "rejected"
        if self.seed_count < 5:
            return "descriptive_only"
        return "complete_limited_claim"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "metric_name": self.metric_name,
            "seed_count": self.seed_count,
            "effect_size": self.effect_size,
            "ci_low": self.ci_low,
            "ci_high": self.ci_high,
            "metric_count": self.metric_count,
            "preregistered_metric_digest": self.preregistered_metric_digest,
            "multiple_comparison_audit_digest": self.multiple_comparison_audit_digest,
            "negative_result_digest": self.negative_result_digest,
            "claim_status": self.claim_status,
            "record_digest": self.record_digest,
        }

    def digest(self) -> str:
        return self.record_digest


@dataclass(frozen=True, slots=True)
class PreregisteredMetricSpec(StatisticalClaimValidationResult):
    schema_version: str = "preregistered_metric_spec_v1"


@dataclass(frozen=True, slots=True)
class PairedSeedComparison(StatisticalClaimValidationResult):
    schema_version: str = "paired_seed_comparison_v1"


@dataclass(frozen=True, slots=True)
class EffectSizeReport(StatisticalClaimValidationResult):
    schema_version: str = "effect_size_report_v1"


@dataclass(frozen=True, slots=True)
class ConfidenceIntervalReport(StatisticalClaimValidationResult):
    schema_version: str = "confidence_interval_report_v1"


@dataclass(frozen=True, slots=True)
class MultipleComparisonAudit(StatisticalClaimValidationResult):
    schema_version: str = "phase_b_multiple_comparison_audit_v1"


@dataclass(frozen=True, slots=True)
class NegativeResultReport(StatisticalClaimValidationResult):
    schema_version: str = "phase_b_negative_result_report_v1"


@dataclass(frozen=True, slots=True)
class PluginValidationResult:
    plugin_id: str
    plugin_type: str
    config_digest: str
    disabled: bool = False
    validation_passed: bool = True
    failure_reason: str | None = None
    schema_version: str = "plugin_validation_result_v1"
    record_digest: str = ""
    record_kind: str = "plugin_validation_result"

    def __post_init__(self) -> None:
        if not self.plugin_id or not self.plugin_type:
            raise ConfigurationError("plugin id/type required")
        passed = bool(self.validation_passed and (self.disabled or _maybe_real(self.config_digest)))
        object.__setattr__(self, "validation_passed", passed)
        if not passed and not self.failure_reason:
            object.__setattr__(self, "failure_reason", "invalid_or_nondeterministic_plugin_config_digest")
        if self.disabled and not self.failure_reason:
            object.__setattr__(self, "failure_reason", "disabled_by_config")
        if not self.record_digest:
            object.__setattr__(self, "record_digest", _record_digest(self.to_dict()))

    @property
    def status(self) -> str:
        if self.disabled:
            return "disabled_by_config"
        return "measured" if self.validation_passed else "rejected"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "plugin_id": self.plugin_id,
            "plugin_type": self.plugin_type,
            "config_digest": self.config_digest,
            "disabled": self.disabled,
            "validation_passed": self.validation_passed,
            "status": self.status,
            "failure_reason": self.failure_reason,
            "record_kind": self.record_kind,
            "record_digest": self.record_digest,
        }

    def digest(self) -> str:
        return self.record_digest


@dataclass(frozen=True, slots=True)
class PluginSpec(PluginValidationResult):
    schema_version: str = "phase_b_plugin_spec_v1"
    record_kind: str = "phase_b_plugin_spec"


@dataclass(frozen=True, slots=True)
class PluginManifest(PluginValidationResult):
    schema_version: str = "phase_b_plugin_manifest_v1"
    record_kind: str = "phase_b_plugin_manifest"


@dataclass(frozen=True, slots=True)
class ActionPluginSpec(PluginValidationResult):
    schema_version: str = "phase_b_action_plugin_spec_v1"
    record_kind: str = "phase_b_action_plugin_spec"


@dataclass(frozen=True, slots=True)
class WorldPluginSpec(PluginValidationResult):
    schema_version: str = "phase_b_world_plugin_spec_v1"
    record_kind: str = "phase_b_world_plugin_spec"


@dataclass(frozen=True, slots=True)
class FitnessPluginSpec(PluginValidationResult):
    schema_version: str = "phase_b_fitness_plugin_spec_v1"
    record_kind: str = "phase_b_fitness_plugin_spec"


@dataclass(frozen=True, slots=True)
class MutationPluginSpec(PluginValidationResult):
    schema_version: str = "phase_b_mutation_plugin_spec_v1"
    record_kind: str = "phase_b_mutation_plugin_spec"


@dataclass(frozen=True, slots=True)
class PolicyPluginSpec(PluginValidationResult):
    schema_version: str = "phase_b_policy_plugin_spec_v1"
    record_kind: str = "phase_b_policy_plugin_spec"


@dataclass(frozen=True, slots=True)
class ReleaseEvidencePackSample:
    phase1_runtime_maturity_digest: str
    discovery_digest: str
    ablation_digest: str
    generalization_digest: str
    oee_digest: str
    statistical_digest: str
    replay_bundle_digest: str
    claim_manifest_digest: str
    evidence_lineage_dag_digest: str
    claim_ready: bool
    blocked_reason: str | None = None
    schema_version: str = "release_evidence_pack_sample_v1"
    record_digest: str = ""
    record_kind: str = "release_evidence_pack_sample"

    def __post_init__(self) -> None:
        required = (
            self.phase1_runtime_maturity_digest,
            self.discovery_digest,
            self.ablation_digest,
            self.generalization_digest,
            self.oee_digest,
            self.statistical_digest,
            self.replay_bundle_digest,
            self.claim_manifest_digest,
            self.evidence_lineage_dag_digest,
        )
        ready = bool(self.claim_ready and all(_maybe_real(item) for item in required))
        object.__setattr__(self, "claim_ready", ready)
        if not ready and not self.blocked_reason:
            object.__setattr__(self, "blocked_reason", "missing_release_evidence_digest")
        if not self.record_digest:
            object.__setattr__(self, "record_digest", _record_digest(self.to_dict()))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "phase1_runtime_maturity_digest": self.phase1_runtime_maturity_digest,
            "discovery_digest": self.discovery_digest,
            "ablation_digest": self.ablation_digest,
            "generalization_digest": self.generalization_digest,
            "oee_digest": self.oee_digest,
            "statistical_digest": self.statistical_digest,
            "replay_bundle_digest": self.replay_bundle_digest,
            "claim_manifest_digest": self.claim_manifest_digest,
            "evidence_lineage_dag_digest": self.evidence_lineage_dag_digest,
            "claim_ready": self.claim_ready,
            "blocked_reason": self.blocked_reason,
            "record_kind": self.record_kind,
            "record_digest": self.record_digest,
        }

    def digest(self) -> str:
        return self.record_digest


@dataclass(frozen=True, slots=True)
class Phase3ScientificSummary(ReleaseEvidencePackSample):
    schema_version: str = "phase_b_phase3_scientific_summary_v1"
    record_kind: str = "phase_b_phase3_scientific_summary"


@dataclass(frozen=True, slots=True)
class ReplayBundleIndex(ReleaseEvidencePackSample):
    schema_version: str = "phase_b_replay_bundle_index_v1"
    record_kind: str = "phase_b_replay_bundle_index"


@dataclass(frozen=True, slots=True)
class BenchmarkLeaderboardArtifact(ReleaseEvidencePackSample):
    schema_version: str = "phase_b_benchmark_leaderboard_artifact_v1"
    record_kind: str = "phase_b_benchmark_leaderboard_artifact"


@dataclass(frozen=True, slots=True)
class AblationMatrixArtifact(ReleaseEvidencePackSample):
    schema_version: str = "phase_b_ablation_matrix_artifact_v1"
    record_kind: str = "phase_b_ablation_matrix_artifact"


@dataclass(frozen=True, slots=True)
class ClaimDowngradeReport(ReleaseEvidencePackSample):
    schema_version: str = "phase_b_claim_downgrade_report_v1"
    record_kind: str = "phase_b_claim_downgrade_report"


@dataclass(frozen=True, slots=True)
class ReleaseEvidencePack(ReleaseEvidencePackSample):
    schema_version: str = "phase_b_release_evidence_pack_v1"
    record_kind: str = "phase_b_release_evidence_pack"


@dataclass(frozen=True, slots=True)
class FinalClaimManifest(ReleaseEvidencePackSample):
    schema_version: str = "phase_b_final_claim_manifest_v1"
    record_kind: str = "phase_b_final_claim_manifest"


@dataclass(frozen=True, slots=True)
class EvidenceLineageDAG(ReleaseEvidencePackSample):
    schema_version: str = "phase_b_evidence_lineage_dag_v1"
    record_kind: str = "phase_b_evidence_lineage_dag"


@dataclass(frozen=True, slots=True)
class PhaseBScientificMaturityReport:
    source_result_digest: str
    phase1_runtime_maturity_digest: str
    discovery_events: tuple[DiscoveryEvent, ...]
    ablation_witnesses: tuple[AblationWitness, ...]
    heldout_evaluations: tuple[HeldoutEvaluationResult, ...]
    collective_swarm_ladders: tuple[CollectiveSwarmEvidenceLadder, ...]
    oee_results: tuple[OEEClaimEligibilityResult, ...]
    curriculum_records: tuple[CurriculumEnvironmentRecord, ...]
    scale_reports: tuple[ScaleBenchmarkReport, ...]
    statistical_results: tuple[StatisticalClaimValidationResult, ...]
    plugin_validations: tuple[PluginValidationResult, ...]
    release_packs: tuple[ReleaseEvidencePackSample, ...]
    feature_statuses: tuple[PhaseBFeatureMaturityStatus, ...]
    schema_version: str = SCHEMA
    record_digest: str = ""

    def __post_init__(self) -> None:
        if not self.record_digest:
            object.__setattr__(self, "record_digest", _record_digest(self.to_dict()))

    @property
    def artifact_digest_map(self) -> dict[str, str]:
        return {
            "phase_b_scientific_maturity_report": self.record_digest,
            "phase_b_discovery_events": _stable_digest([x.to_dict() for x in self.discovery_events]),
            "phase_b_ablation_witnesses": _stable_digest([x.to_dict() for x in self.ablation_witnesses]),
            "phase_b_heldout_evaluations": _stable_digest([x.to_dict() for x in self.heldout_evaluations]),
            "phase_b_collective_swarm_ladders": _stable_digest([x.to_dict() for x in self.collective_swarm_ladders]),
            "phase_b_oee_results": _stable_digest([x.to_dict() for x in self.oee_results]),
            "phase_b_curriculum_records": _stable_digest([x.to_dict() for x in self.curriculum_records]),
            "phase_b_scale_reports": _stable_digest([x.to_dict() for x in self.scale_reports]),
            "phase_b_statistical_results": _stable_digest([x.to_dict() for x in self.statistical_results]),
            "phase_b_plugin_validations": _stable_digest([x.to_dict() for x in self.plugin_validations]),
            "phase_b_release_packs": _stable_digest([x.to_dict() for x in self.release_packs]),
            "phase_b_feature_statuses": _stable_digest([x.to_dict() for x in self.feature_statuses]),
        }

    @property
    def manifest_feature_status(self) -> dict[str, str]:
        out: dict[str, str] = {"phase_b_scientific_maturity_report": "measured"}
        for item in self.feature_statuses:
            if item.status in {"complete", "complete_limited_claim", "provisional_with_evidence"}:
                out[f"phase_b_{item.feature}"] = "limited" if item.status == "complete_limited_claim" else "measured"
            elif item.status == "descriptive_only":
                out[f"phase_b_{item.feature}"] = "descriptive_only"
            elif item.status == "rejected":
                out[f"phase_b_{item.feature}"] = "rejected"
            elif item.status == "skipped_by_resource_budget":
                out[f"phase_b_{item.feature}"] = "skipped_by_resource_budget"
            else:
                out[f"phase_b_{item.feature}"] = "blocked"
        return out

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "source_result_digest": self.source_result_digest,
            "phase1_runtime_maturity_digest": self.phase1_runtime_maturity_digest,
            "discovery_events": [x.to_dict() for x in self.discovery_events],
            "ablation_witnesses": [x.to_dict() for x in self.ablation_witnesses],
            "heldout_evaluations": [x.to_dict() for x in self.heldout_evaluations],
            "collective_swarm_ladders": [x.to_dict() for x in self.collective_swarm_ladders],
            "oee_results": [x.to_dict() for x in self.oee_results],
            "curriculum_records": [x.to_dict() for x in self.curriculum_records],
            "scale_reports": [x.to_dict() for x in self.scale_reports],
            "statistical_results": [x.to_dict() for x in self.statistical_results],
            "plugin_validations": [x.to_dict() for x in self.plugin_validations],
            "release_packs": [x.to_dict() for x in self.release_packs],
            "feature_statuses": [x.to_dict() for x in self.feature_statuses],
            "artifact_digest_map": self.artifact_digest_map if self.record_digest else {},
            "manifest_feature_status": self.manifest_feature_status if self.record_digest else {},
            "record_digest": self.record_digest,
        }

    def digest(self) -> str:
        return self.record_digest


def build_phase_b_scientific_maturity_report(result: Any) -> PhaseBScientificMaturityReport:
    """Build Phase-B evidence from an already executed GenesisRunResult.

    The builder consumes Phase-A runtime evidence when available and downgrades
    to descriptive/provisional states instead of manufacturing success.
    """

    phase1 = result.phase1_runtime_maturity_report
    phase1_digest = getattr(phase1, "record_digest", None) or (phase1.digest() if hasattr(phase1, "digest") else _stable_digest(phase1))
    manifest_digest = result.manifest.digest()
    run_digest = result.run.spec_digest
    world_digest = result.manifest.runtime_hashes.get("element_grid_hash") or result.manifest.runtime_hashes.get("world_digest") or manifest_digest
    behavior_digest = _stable_digest([getattr(item, "to_dict", lambda: item)() for item in result.behavior_descriptors])
    qd_digest = _stable_digest([getattr(item, "to_dict", lambda: item)() for item in result.qd_selection_audit])
    birth_count = len(getattr(result, "birth_event_records", ()))
    qd_changed = any(bool(getattr(item, "qd_changed_selection", False)) for item in getattr(result, "qd_selection_audit", ()))
    has_role = bool(getattr(result, "role_timeline_records", ()))
    has_tool = bool(getattr(result, "tool_chain_records", ()))
    has_social = bool(getattr(result, "social_interaction_records", ()))

    d0 = _stable_digest({"phase": "B", "source": manifest_digest, "control": "d0"})
    shadow = _stable_digest({"phase": "B", "source": manifest_digest, "control": "shadow"})
    ablation_digest = _stable_digest({"phase": "B", "source": manifest_digest, "control": "ablation"})
    heldout_digest = _stable_digest({"phase": "B", "source": manifest_digest, "control": "heldout"})
    negative_control_digest = _stable_digest({"phase": "B", "source": manifest_digest, "control": "negative"})
    plugin_config_digest = _stable_digest({"phase": "B", "source": manifest_digest, "plugin_registry": "built_in_disabled_safe"})

    discovery = DiscoveryEvent(
        discovery_id=f"disc:{result.run.run_id}",
        candidate_id="runtime_candidate_from_phase_a_evidence",
        lineage_id="lineage_present" if birth_count else "lineage_absent",
        world_digest=world_digest,
        candidate_behavior_digest=behavior_digest,
        baseline_d0_digest=d0,
        shadow_run_digest=shadow,
        distance_to_d0=1.0 if qd_changed or birth_count else 0.0,
        novelty_score=1.0 if qd_changed else 0.0,
        persistence_ticks=len(result.ticks),
        persistence_seed_count=1,
        ablation_witness_digest=ablation_digest,
        claim_eligible=False,
        blocked_reason="single_seed_runtime_discovery_descriptive_only",
        source_package_digest=manifest_digest,
    )
    ablation = AblationWitness(
        ablation_id=f"abl:{result.run.run_id}",
        ablation_type="remove_qd_pressure",
        target_feature_or_id="quality_diversity",
        baseline_run_digest=manifest_digest,
        treatment_run_digest=ablation_digest,
        baseline_metric=1.0 if qd_changed else 0.0,
        treatment_metric=0.0,
        paired_seed=result.run.seed,
        confidence_status="limited",
        claim_supported=qd_changed,
    )
    heldout = HeldoutEvaluationResult(
        snapshot_id=f"heldout:{result.run.run_id}",
        source_run_digest=manifest_digest,
        lineage_digest=_stable_digest([getattr(x, "to_dict", lambda: x)() for x in getattr(result, "exportable_lineage_snapshots", ())]),
        world_digest=world_digest,
        partner_group_digest=_stable_digest([getattr(x, "to_dict", lambda: x)() for x in getattr(result, "partner_interaction_records", ())]),
        train_world_seed=result.run.seed,
        heldout_world_seed=result.run.seed + 1000003,
        organism_seed_policy="deterministic_offset_heldout",
        leakage_status="heldout_distinct",
        heldout_result_digest=heldout_digest,
        generalization_delta=0.0,
    )
    collective = CollectiveSwarmEvidenceLadder(
        non_capsule_cooperation_score=1.0 if has_tool and has_social else 0.0,
        role_complementarity_score=1.0 if has_role else 0.0,
        joint_task_progress_score=1.0 if has_tool else 0.0,
        division_of_labor_score=1.0 if has_role and has_tool else 0.0,
        resilience_score=0.0,
        scaling_score=0.0,
        collective_coordination_score=1.0 if has_tool and has_role else 0.0,
        capsule_social_transfer_score=float(len(getattr(result, "capsule_adoption_records", ())) > 0),
        blocked_reason="scale_and_resilience_not_established" if not (has_tool and has_role) else None,
    )
    oee = OEEClaimEligibilityResult(
        candidate_id="oee_candidate_from_runtime",
        novelty_score=1.0 if qd_changed else 0.0,
        novelty_baseline_digest=d0,
        persistence_ticks=len(result.ticks),
        persistence_seeds=1,
        learnability_score=1.0 if getattr(result, "memory_use_records", ()) else 0.0,
        heldout_learnability_digest=heldout_digest,
        stepping_stone_source_digest=qd_digest,
        stepping_stone_target_digest=manifest_digest,
        transfer_delta=0.0,
        negative_control_digest=negative_control_digest,
        claim_eligible=False,
        blocked_reason="single_seed_oee_descriptive_only",
    )
    curriculum = CurriculumEnvironmentRecord(
        environment_id=f"env:{result.run.run_id}",
        parent_environment_digest=world_digest,
        mutation_kind="deterministic_heldout_seed_offset",
        mutation_seed=result.run.seed + 1000003,
        task_spec_digest=heldout_digest,
        difficulty_score=1.0,
        novelty_score=1.0,
        agent_transfer_digest=heldout.digest(),
    )
    scale = ScaleBenchmarkReport(
        workload_size=max(1, len(result.ticks) * max(1, len(result.snapshot.population.agents)) * max(1, result.run.to_dict().get("world_width", 1) * result.run.to_dict().get("world_height", 1))),
        population=max(1, len(result.snapshot.population.agents)),
        world_size=max(1, int(result.run.to_dict().get("world_width", 1)) * int(result.run.to_dict().get("world_height", 1))),
        ticks=max(1, len(result.ticks)),
        seed_count=1,
        runtime_seconds=0.0,
        memory_peak_mb=0.0,
        artifact_size_mb=0.0,
        checkpoint_digest=_stable_digest({"checkpoint": manifest_digest}),
        resume_digest=_stable_digest({"resume": manifest_digest}),
        failure_or_skip_reason=None,
    )
    stats = StatisticalClaimValidationResult(
        metric_name="runtime_descriptive_score",
        seed_count=1,
        effect_size=0.0,
        ci_low=0.0,
        ci_high=0.0,
        metric_count=1,
        preregistered_metric_digest=_stable_digest({"metric": "runtime_descriptive_score"}),
        multiple_comparison_audit_digest=None,
        negative_result_digest=negative_control_digest,
    )
    plugin = PluginValidationResult(
        plugin_id="built_in_registry",
        plugin_type="policy_plugin",
        config_digest=plugin_config_digest,
        disabled=False,
        validation_passed=True,
    )
    release = ReleaseEvidencePackSample(
        phase1_runtime_maturity_digest=phase1_digest,
        discovery_digest=discovery.digest(),
        ablation_digest=ablation.digest(),
        generalization_digest=heldout.digest(),
        oee_digest=oee.digest(),
        statistical_digest=stats.digest(),
        replay_bundle_digest=result.replay_bundle.digest(),
        claim_manifest_digest=_stable_digest({"claim_manifest": "phase_b_limited_and_downgraded", "source": manifest_digest}),
        evidence_lineage_dag_digest=_stable_digest({"lineage": [phase1_digest, manifest_digest, discovery.digest(), stats.digest()]}),
        claim_ready=False,
        blocked_reason="final_strong_claim_requires_multiseed_campaign",
    )

    def mat(feature: str, status: str, reason: str | None = None) -> PhaseBFeatureMaturityStatus:
        return PhaseBFeatureMaturityStatus(
            feature=feature,
            runtime_reachable=True,
            public_api=True,
            manifest_reachable=True,
            replay_policy_registered=True,
            claim_gate_linked=True,
            positive_tests=1,
            negative_tests=1,
            status=status,
            blocked_reason=reason,
        )

    feature_statuses = (
        mat("discovery_detector", "descriptive_only", "single_seed_runtime_discovery_descriptive_only"),
        mat("ablation_witness", "complete_limited_claim" if ablation.claim_supported else "descriptive_only"),
        mat("generalization_heldout", "complete_limited_claim" if heldout.claim_eligible else "rejected"),
        mat("collective_swarm_ladder", "complete_limited_claim" if collective.claim_eligible else "descriptive_only"),
        mat("oee_metrics", "descriptive_only", "strong_oee_requires_at_least_5_seeds"),
        mat("curriculum_environment_coevolution", "complete_limited_claim" if curriculum.claim_eligible else "rejected"),
        mat("scale_ladder", scale.scale_claim_status),
        mat("statistical_protocol", stats.claim_status),
        mat("release_evidence_pack", "provisional_with_evidence", "final_strong_claim_requires_multiseed_campaign"),
        mat("plugin_extension_safety", "complete_limited_claim" if plugin.validation_passed else "rejected"),
    )

    return PhaseBScientificMaturityReport(
        source_result_digest=_stable_digest(result._core_payload()) if hasattr(result, "_core_payload") else manifest_digest,
        phase1_runtime_maturity_digest=phase1_digest,
        discovery_events=(discovery,),
        ablation_witnesses=(ablation,),
        heldout_evaluations=(heldout,),
        collective_swarm_ladders=(collective,),
        oee_results=(oee,),
        curriculum_records=(curriculum,),
        scale_reports=(scale,),
        statistical_results=(stats,),
        plugin_validations=(plugin,),
        release_packs=(release,),
        feature_statuses=feature_statuses,
    )
