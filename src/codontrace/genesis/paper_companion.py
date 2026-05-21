"""Optional paper/benchmark companion evidence objects.

These are object-only records. They do not run benchmarks, compute p-values,
write papers, generate reports, or claim benchmark superiority.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError


@dataclass(frozen=True, slots=True)
class PaperEvidenceBundle:
    paper_bundle_id: str
    library_version: str
    scenario_suite_digest: str
    evidence_pack_digest: str
    validation_matrix_digest: str
    reproducibility_summary_digest: str
    limitations_digest: str
    claim_audit_digest: str
    allowed_claim_ceiling: str = "CANDIDATE"

    def __post_init__(self) -> None:
        if self.allowed_claim_ceiling not in {"NONE", "CANDIDATE", "EVIDENCE_SUPPORTED"}:
            raise ConfigurationError("PaperEvidenceBundle.allowed_claim_ceiling is invalid.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "paper_bundle_id": self.paper_bundle_id,
            "library_version": self.library_version,
            "scenario_suite_digest": self.scenario_suite_digest,
            "evidence_pack_digest": self.evidence_pack_digest,
            "validation_matrix_digest": self.validation_matrix_digest,
            "reproducibility_summary_digest": self.reproducibility_summary_digest,
            "limitations_digest": self.limitations_digest,
            "claim_audit_digest": self.claim_audit_digest,
            "allowed_claim_ceiling": self.allowed_claim_ceiling,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> PaperEvidenceBundle:
        return cls(
            _str(data, "paper_bundle_id"),
            _str(data, "library_version"),
            _str(data, "scenario_suite_digest"),
            _str(data, "evidence_pack_digest"),
            _str(data, "validation_matrix_digest"),
            _str(data, "reproducibility_summary_digest"),
            _str(data, "limitations_digest"),
            _str(data, "claim_audit_digest"),
            _str(data, "allowed_claim_ceiling", "CANDIDATE"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class BenchmarkScenario:
    benchmark_id: str
    description: str
    baseline_method: str
    controlled_variables: tuple[str, ...]
    metrics: tuple[str, ...]
    non_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.non_claims:
            raise ConfigurationError(
                "BenchmarkScenario.non_claims must state no superiority claim."
            )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "benchmark_id": self.benchmark_id,
            "description": self.description,
            "baseline_method": self.baseline_method,
            "controlled_variables": list(self.controlled_variables),
            "metrics": list(self.metrics),
            "non_claims": list(self.non_claims),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> BenchmarkScenario:
        return cls(
            _str(data, "benchmark_id"),
            _str(data, "description"),
            _str(data, "baseline_method"),
            _str_tuple(data, "controlled_variables"),
            _str_tuple(data, "metrics"),
            _str_tuple(data, "non_claims"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class PreRegisteredMetric:
    metric_id: str
    name: str
    definition: str
    direction: str
    required_evidence: tuple[str, ...]
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.direction not in {
            "higher_is_better",
            "lower_is_better",
            "target_range",
            "descriptive_only",
        }:
            raise ConfigurationError("PreRegisteredMetric.direction is invalid.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "metric_id": self.metric_id,
            "name": self.name,
            "definition": self.definition,
            "direction": self.direction,
            "required_evidence": list(self.required_evidence),
            "limitations": list(self.limitations),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> PreRegisteredMetric:
        return cls(
            _str(data, "metric_id"),
            _str(data, "name"),
            _str(data, "definition"),
            _str(data, "direction"),
            _str_tuple(data, "required_evidence"),
            _str_tuple(data, "limitations"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ExternalReplicationRecord:
    replication_id: str
    external_environment: str
    library_version: str
    scenario_digest: str
    seed_count: int
    evidence_digest: str
    differences: tuple[str, ...]
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            isinstance(self.seed_count, bool)
            or not isinstance(self.seed_count, int)
            or self.seed_count < 0
        ):
            raise ConfigurationError(
                "ExternalReplicationRecord.seed_count must be a non-negative integer."
            )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "replication_id": self.replication_id,
            "external_environment": self.external_environment,
            "library_version": self.library_version,
            "scenario_digest": self.scenario_digest,
            "seed_count": self.seed_count,
            "evidence_digest": self.evidence_digest,
            "differences": list(self.differences),
            "limitations": list(self.limitations),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ExternalReplicationRecord:
        return cls(
            _str(data, "replication_id"),
            _str(data, "external_environment"),
            _str(data, "library_version"),
            _str(data, "scenario_digest"),
            _int(data, "seed_count"),
            _str(data, "evidence_digest"),
            _str_tuple(data, "differences"),
            _str_tuple(data, "limitations"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


def _digest(payload: Mapping[str, JsonValue]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _str(data: Mapping[str, JsonValue], key: str, default: str | None = None) -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        raise ConfigurationError(f"{key} must be a string.")
    return value


def _int(data: Mapping[str, JsonValue], key: str) -> int:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{key} must be an integer.")
    return value


def _str_tuple(data: Mapping[str, JsonValue], key: str) -> tuple[str, ...]:
    raw = data.get(key, [])
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise ConfigurationError(f"{key} must be a list of strings.")
    return tuple(str(item) for item in raw)
