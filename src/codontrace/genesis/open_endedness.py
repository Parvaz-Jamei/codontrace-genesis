"""Open-endedness/OEE candidate measurement primitives."""

from __future__ import annotations

from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.genesis.canonical import (
    canonical_digest,
    is_real_evidence_digest as _real_digest,
    require_finite_float,
)


OEE_RESEARCH_GRADE_MIN_SEEDS = 30


@dataclass(frozen=True, slots=True)
class OEEArtifactSequence:
    artifact_digests: tuple[str, ...]
    schema_version: str = "oee_artifact_sequence_v1"

    def __post_init__(self) -> None:
        if not self.artifact_digests or any(not _real_digest(digest) for digest in self.artifact_digests):
            raise ValueError("OEEArtifactSequence requires real artifact digests")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "artifact_digests": list(self.artifact_digests),
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class NoveltyTrajectory:
    values: tuple[float, ...]
    schema_version: str = "novelty_trajectory_v1"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "values",
            tuple(require_finite_float("novelty", value) for value in self.values),
        )

    @property
    def persistent(self) -> bool:
        return len(self.values) >= 2 and self.values[-1] > 0 and min(self.values) >= 0

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "values": list(self.values),
            "persistent": self.persistent,
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class OEECandidateMetrics:
    novelty_persistence: float
    behavioral_innovation_rate: float
    lineage_depth_growth: float
    archive_expansion: float
    learnability_delta: float
    complexity_growth_cost_adjusted: float
    d0_baseline_distance: float
    shadow_baseline_delta: float
    ablation_sensitivity: float
    multi_seed_count: int
    replay_verified: bool
    replay_digest: str = ""
    d0_baseline_digest: str = ""
    shadow_digest: str = ""
    schema_version: str = "oee_candidate_metrics_v2"
    digest: str = ""

    def __post_init__(self) -> None:
        for attr in (
            "novelty_persistence",
            "behavioral_innovation_rate",
            "lineage_depth_growth",
            "archive_expansion",
            "learnability_delta",
            "complexity_growth_cost_adjusted",
            "d0_baseline_distance",
            "shadow_baseline_delta",
            "ablation_sensitivity",
        ):
            object.__setattr__(self, attr, round(require_finite_float(attr, getattr(self, attr)), 10))
        if self.multi_seed_count < 0:
            raise ValueError("multi_seed_count must be non-negative")
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ValueError("OEECandidateMetrics digest mismatch")
        object.__setattr__(self, "digest", computed)

    @property
    def evidence_level(self) -> str:
        if self.multi_seed_count < 2:
            return "too_few_seeds"
        if self.multi_seed_count < OEE_RESEARCH_GRADE_MIN_SEEDS:
            return "descriptive_only"
        return "research_grade_candidate"

    @property
    def claim_eligible(self) -> bool:
        return (
            self.novelty_persistence > 0.0
            and self.learnability_delta > 0.0
            and self.ablation_sensitivity > 0.0
            and self.d0_baseline_distance > 0.0
            and self.shadow_baseline_delta > 0.0
            and self.multi_seed_count >= OEE_RESEARCH_GRADE_MIN_SEEDS
            and self.replay_verified
            and _real_digest(self.replay_digest)
            and _real_digest(self.d0_baseline_digest)
            and _real_digest(self.shadow_digest)
        )

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "novelty_persistence": self.novelty_persistence,
            "behavioral_innovation_rate": self.behavioral_innovation_rate,
            "lineage_depth_growth": self.lineage_depth_growth,
            "archive_expansion": self.archive_expansion,
            "learnability_delta": self.learnability_delta,
            "complexity_growth_cost_adjusted": self.complexity_growth_cost_adjusted,
            "d0_baseline_distance": self.d0_baseline_distance,
            "shadow_baseline_delta": self.shadow_baseline_delta,
            "ablation_sensitivity": self.ablation_sensitivity,
            "multi_seed_count": self.multi_seed_count,
            "replay_verified": self.replay_verified,
            "replay_digest": self.replay_digest,
            "d0_baseline_digest": self.d0_baseline_digest,
            "shadow_digest": self.shadow_digest,
            "evidence_level": self.evidence_level,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "claim_eligible": self.claim_eligible, "digest": self.digest}


@dataclass(frozen=True, slots=True)
class LearnabilityReport:
    cross_environment_utility: float
    heldout_digest: str
    replay_digest: str
    schema_version: str = "learnability_report_v2"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "cross_environment_utility",
            require_finite_float("cross_environment_utility", self.cross_environment_utility),
        )

    @property
    def rejection_reasons(self) -> tuple[str, ...]:
        reasons: list[str] = []
        if self.cross_environment_utility <= 0.0:
            reasons.append("non_positive_cross_environment_utility")
        if not _real_digest(self.heldout_digest):
            reasons.append("missing_heldout_digest")
        if not _real_digest(self.replay_digest):
            reasons.append("missing_replay_digest")
        return tuple(reasons)

    @property
    def claim_eligible(self) -> bool:
        return not self.rejection_reasons

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "cross_environment_utility": self.cross_environment_utility,
            "heldout_digest": self.heldout_digest,
            "replay_digest": self.replay_digest,
            "claim_eligible": self.claim_eligible,
            "rejection_reasons": list(self.rejection_reasons),
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())



@dataclass(frozen=True, slots=True)
class PersistenceReport:
    trajectory: NoveltyTrajectory
    persistence_digest: str
    status: str = "measured"
    schema_version: str = "persistence_report_v1"

    def __post_init__(self) -> None:
        if not _real_digest(self.persistence_digest):
            raise ValueError("PersistenceReport requires a real persistence digest")

    @property
    def persistent(self) -> bool:
        return self.trajectory.persistent and self.status == "measured"

    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "trajectory": self.trajectory.to_dict(), "persistence_digest": self.persistence_digest, "status": self.status, "persistent": self.persistent}

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class SteppingStoneTransferReport:
    learnability: LearnabilityReport | float
    source_environment_digest: str
    target_environment_digest: str
    transfer_status: str = "measured"
    schema_version: str = "stepping_stone_transfer_report_v1"

    def __post_init__(self) -> None:
        # Compatibility with the former LearnabilityReport alias accepted the
        # compact shape ``(utility, heldout_digest, replay_digest)``.  Preserve
        # that public call form, but keep fake/placeholder/not_run evidence as
        # negative evidence rather than constructor-crashing or being counted as
        # positive claim support.
        if not isinstance(self.learnability, LearnabilityReport):
            object.__setattr__(
                self,
                "learnability",
                LearnabilityReport(
                    float(self.learnability),
                    self.source_environment_digest,
                    self.target_environment_digest,
                ),
            )
        if not _real_digest(self.source_environment_digest) or not _real_digest(self.target_environment_digest):
            object.__setattr__(self, "transfer_status", "invalid_evidence")

    @property
    def rejection_reasons(self) -> tuple[str, ...]:
        reasons = list(self.learnability.rejection_reasons)
        if not _real_digest(self.source_environment_digest):
            reasons.append("missing_source_environment_digest")
        if not _real_digest(self.target_environment_digest):
            reasons.append("missing_target_environment_digest")
        if self.transfer_status != "measured":
            reasons.append(f"transfer_status:{self.transfer_status}")
        return tuple(dict.fromkeys(reasons))

    @property
    def claim_eligible(self) -> bool:
        return self.learnability.claim_eligible and self.transfer_status == "measured" and not self.rejection_reasons

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "learnability": self.learnability.to_dict(),
            "source_environment_digest": self.source_environment_digest,
            "target_environment_digest": self.target_environment_digest,
            "transfer_status": self.transfer_status,
            "claim_eligible": self.claim_eligible,
            "rejection_reasons": list(self.rejection_reasons),
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class CurriculumCoEvolutionReport:
    learnability: LearnabilityReport
    curriculum_digest: str
    agent_population_digest: str
    status: str = "measured"
    schema_version: str = "curriculum_coevolution_report_v1"

    def __post_init__(self) -> None:
        if not _real_digest(self.curriculum_digest) or not _real_digest(self.agent_population_digest):
            raise ValueError("CurriculumCoEvolutionReport requires real curriculum and population digests")

    @property
    def claim_eligible(self) -> bool:
        return self.learnability.claim_eligible and self.status == "measured"

    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "learnability": self.learnability.to_dict(), "curriculum_digest": self.curriculum_digest, "agent_population_digest": self.agent_population_digest, "status": self.status, "claim_eligible": self.claim_eligible}

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class D0ShadowBaselineReport:
    learnability: LearnabilityReport
    d0_baseline_digest: str
    shadow_digest: str
    status: str = "measured"
    schema_version: str = "d0_shadow_baseline_report_v1"

    def __post_init__(self) -> None:
        if not _real_digest(self.d0_baseline_digest) or not _real_digest(self.shadow_digest):
            raise ValueError("D0ShadowBaselineReport requires real D0 and shadow digests")

    @property
    def claim_eligible(self) -> bool:
        return self.learnability.claim_eligible and self.status == "measured"

    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "learnability": self.learnability.to_dict(), "d0_baseline_digest": self.d0_baseline_digest, "shadow_digest": self.shadow_digest, "status": self.status, "claim_eligible": self.claim_eligible}

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class TaskGeneratorSpec:
    artifact_sequence: OEEArtifactSequence
    generator_id: str
    generator_digest: str
    status: str = "provisional"
    schema_version: str = "task_generator_spec_v1"

    def __post_init__(self) -> None:
        if not self.generator_id:
            raise ValueError("TaskGeneratorSpec requires generator_id")
        if not _real_digest(self.generator_digest):
            raise ValueError("TaskGeneratorSpec requires a real generator digest")

    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "artifact_sequence": self.artifact_sequence.to_dict(), "generator_id": self.generator_id, "generator_digest": self.generator_digest, "status": self.status}

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class EnvironmentMutationRecord:
    artifact_sequence: OEEArtifactSequence
    source_environment_digest: str
    mutated_environment_digest: str
    mutation_reason: str
    status: str = "measured"
    schema_version: str = "environment_mutation_record_v1"

    def __post_init__(self) -> None:
        if not _real_digest(self.source_environment_digest) or not _real_digest(self.mutated_environment_digest):
            raise ValueError("EnvironmentMutationRecord requires real environment digests")
        if not self.mutation_reason:
            raise ValueError("EnvironmentMutationRecord requires mutation_reason")

    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "artifact_sequence": self.artifact_sequence.to_dict(), "source_environment_digest": self.source_environment_digest, "mutated_environment_digest": self.mutated_environment_digest, "mutation_reason": self.mutation_reason, "status": self.status}

    def digest(self) -> str:
        return canonical_digest(self.to_dict())

# ---------------------------------------------------------------------------
# Extended OEE metric bundle (P2)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class OEEExtendedMetrics:
    novelty_accumulation: float
    complexity_growth: float
    adaptive_success_accumulation: float
    lineage_persistence: float
    behavior_space_expansion: float
    stepping_stone_transfer: float = 0.0
    learnability: float = 0.0
    seed_count: int = 0
    baseline_digest: str | None = None
    negative_control_digest: str | None = None
    schema_version: str = "oee_extended_metrics_v1"
    record_digest: str = ""

    def __post_init__(self) -> None:
        for attr in ("novelty_accumulation", "complexity_growth", "adaptive_success_accumulation", "lineage_persistence", "behavior_space_expansion", "stepping_stone_transfer", "learnability"):
            object.__setattr__(self, attr, round(require_finite_float(attr, getattr(self, attr)), 10))
        if self.seed_count < 0:
            raise ValueError("seed_count must be non-negative")
        if not self.record_digest:
            object.__setattr__(self, "record_digest", canonical_digest(self._payload(), prefix="oee_extended"))

    @property
    def evidence_level(self) -> str:
        if self.seed_count < 2:
            return "too_few_seeds"
        if self.seed_count < 10:
            return "descriptive_only"
        return "candidate_evidence"

    @property
    def claim_eligible(self) -> bool:
        return (
            self.seed_count >= 10
            and self.novelty_accumulation > 0.0
            and self.complexity_growth > 0.0
            and self.adaptive_success_accumulation > 0.0
            and self.lineage_persistence > 0.0
            and self.behavior_space_expansion > 0.0
            and self.learnability > 0.0
            and bool(self.baseline_digest)
            and bool(self.negative_control_digest)
        )

    def _payload(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "novelty_accumulation": self.novelty_accumulation, "complexity_growth": self.complexity_growth, "adaptive_success_accumulation": self.adaptive_success_accumulation, "lineage_persistence": self.lineage_persistence, "behavior_space_expansion": self.behavior_space_expansion, "stepping_stone_transfer": self.stepping_stone_transfer, "learnability": self.learnability, "seed_count": self.seed_count, "baseline_digest": self.baseline_digest, "negative_control_digest": self.negative_control_digest, "evidence_level": self.evidence_level, "claim_eligible": self.claim_eligible}

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "record_digest": self.record_digest}

    def digest(self) -> str:
        return self.record_digest


OpenEndednessMetrics = OEEExtendedMetrics
