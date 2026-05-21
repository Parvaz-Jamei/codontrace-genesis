"""Environment/curriculum co-evolution primitives for GENESIS."""

from __future__ import annotations

from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.genesis.canonical import canonical_digest, require_finite_float


@dataclass(frozen=True, slots=True)
class EnvironmentMutationSpec:
    mutation_id: str
    seed: int
    change_kind: str
    difficulty_target: float
    schema_version: str = "environment_mutation_spec_v1"

    def __post_init__(self) -> None:
        if not self.mutation_id or not self.change_kind:
            raise ValueError("EnvironmentMutationSpec requires mutation_id/change_kind")
        object.__setattr__(self, "difficulty_target", require_finite_float("difficulty_target", self.difficulty_target, non_negative=True))

    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "mutation_id": self.mutation_id, "seed": self.seed, "change_kind": self.change_kind, "difficulty_target": self.difficulty_target}

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class CurriculumStepRecord:
    step_index: int
    environment_digest_before: str
    environment_digest_after: str
    measured_difficulty_delta: float
    accepted: bool
    rejection_reason: str | None = None
    schema_version: str = "curriculum_step_record_v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "measured_difficulty_delta", require_finite_float("measured_difficulty_delta", self.measured_difficulty_delta))
        if self.step_index < 0:
            raise ValueError("step_index must be non-negative")

    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "step_index": self.step_index, "environment_digest_before": self.environment_digest_before, "environment_digest_after": self.environment_digest_after, "measured_difficulty_delta": self.measured_difficulty_delta, "accepted": self.accepted, "rejection_reason": self.rejection_reason}

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class EnvironmentLineageRecord:
    lineage_id: str
    parent_environment_digest: str | None
    child_environment_digest: str
    mutation_spec_digest: str
    schema_version: str = "environment_lineage_record_v1"

    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "lineage_id": self.lineage_id, "parent_environment_digest": self.parent_environment_digest, "child_environment_digest": self.child_environment_digest, "mutation_spec_digest": self.mutation_spec_digest}

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ChallengeNoveltyReport:
    challenge_digest: str
    baseline_digest: str
    novelty_distance: float
    difficulty_measured: bool
    schema_version: str = "challenge_novelty_report_v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "novelty_distance", require_finite_float("novelty_distance", self.novelty_distance, non_negative=True))

    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "challenge_digest": self.challenge_digest, "baseline_digest": self.baseline_digest, "novelty_distance": self.novelty_distance, "difficulty_measured": self.difficulty_measured}

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class EnvironmentAgentTransferRecord:
    agent_digest: str
    source_environment_digest: str
    target_environment_digest: str
    transfer_score_delta: float
    no_rescue_applied: bool = True
    schema_version: str = "environment_agent_transfer_record_v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "transfer_score_delta", require_finite_float("transfer_score_delta", self.transfer_score_delta))

    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "agent_digest": self.agent_digest, "source_environment_digest": self.source_environment_digest, "target_environment_digest": self.target_environment_digest, "transfer_score_delta": self.transfer_score_delta, "no_rescue_applied": self.no_rescue_applied}

    def digest(self) -> str:
        return canonical_digest(self.to_dict())
