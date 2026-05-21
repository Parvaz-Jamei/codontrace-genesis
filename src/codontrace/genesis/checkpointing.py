"""Long-run checkpoint and seed-sweep protocol primitives."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.genesis.canonical import canonical_digest


@dataclass(frozen=True, slots=True)
class RunCheckpoint:
    run_id: str
    tick: int
    manifest_digest: str
    snapshot_digest: str
    rng_state_digest: str
    schema_version: str = "run_checkpoint_v1"

    def __post_init__(self) -> None:
        if self.tick < 0:
            raise ValueError("tick must be non-negative")

    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "run_id": self.run_id, "tick": self.tick, "manifest_digest": self.manifest_digest, "snapshot_digest": self.snapshot_digest, "rng_state_digest": self.rng_state_digest}

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class CheckpointResumeSpec:
    checkpoint_digest: str
    additional_ticks: int
    expected_continuation_digest: str | None = None
    schema_version: str = "checkpoint_resume_spec_v1"

    def __post_init__(self) -> None:
        if self.additional_ticks < 0:
            raise ValueError("additional_ticks must be non-negative")

    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "checkpoint_digest": self.checkpoint_digest, "additional_ticks": self.additional_ticks, "expected_continuation_digest": self.expected_continuation_digest}

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class SeedSweepSpec:
    seeds: tuple[int, ...]
    scenario_digest: str
    max_workers: int = 1
    schema_version: str = "seed_sweep_spec_v1"

    def __post_init__(self) -> None:
        if not self.seeds:
            raise ValueError("SeedSweepSpec requires at least one seed")
        object.__setattr__(self, "seeds", tuple(sorted(int(seed) for seed in self.seeds)))
        if self.max_workers <= 0:
            raise ValueError("max_workers must be positive")

    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "seeds": list(self.seeds), "scenario_digest": self.scenario_digest, "max_workers": self.max_workers}

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class SeedSweepResult:
    spec_digest: str
    per_seed_manifest_digests: tuple[tuple[int, str], ...]
    partial_failure_status: str = "none"
    schema_version: str = "seed_sweep_result_v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "per_seed_manifest_digests", tuple(sorted((int(seed), str(digest)) for seed, digest in self.per_seed_manifest_digests)))

    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "spec_digest": self.spec_digest, "per_seed_manifest_digests": [[s, d] for s, d in self.per_seed_manifest_digests], "partial_failure_status": self.partial_failure_status}

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class LongRunIntegrityReport:
    checkpoint_digest: str
    resume_digest: str
    deterministic_continuation: bool
    per_seed_artifact_manifest_digest: str | None = None
    schema_version: str = "long_run_integrity_report_v1"

    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "checkpoint_digest": self.checkpoint_digest, "resume_digest": self.resume_digest, "deterministic_continuation": self.deterministic_continuation, "per_seed_artifact_manifest_digest": self.per_seed_artifact_manifest_digest}

    def digest(self) -> str:
        return canonical_digest(self.to_dict())

@dataclass(frozen=True, slots=True)
class CheckpointRecord:
    checkpoint: RunCheckpoint
    behavior_digest: str
    schema_version: str = "checkpoint_record_v1"
    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "checkpoint": self.checkpoint.to_dict(), "behavior_digest": self.behavior_digest}
    def digest(self) -> str:
        return canonical_digest(self.to_dict())

@dataclass(frozen=True, slots=True)
class ResumeValidationRecord:
    checkpoint_digest: str
    continuous_digest: str
    resumed_digest: str
    equivalent: bool
    mismatch_field_path: str | None = None
    schema_version: str = "resume_validation_record_v1"
    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "checkpoint_digest": self.checkpoint_digest, "continuous_digest": self.continuous_digest, "resumed_digest": self.resumed_digest, "equivalent": self.equivalent, "mismatch_field_path": self.mismatch_field_path}
    def digest(self) -> str:
        return canonical_digest(self.to_dict())
