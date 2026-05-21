"""Conservative validation matrix for GENESIS evidence bundles."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.evidence_bundle import EvidenceBundle


@dataclass(frozen=True, slots=True)
class ValidationMatrixConfig:
    require_d0: bool = True
    require_qd: bool = True
    require_ablation: bool = True
    require_replay: bool = True
    require_capsule_metrics: bool = False
    require_multi_seed: bool = True
    min_seed_count: int = 3
    required_components: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if isinstance(self.min_seed_count, bool) or self.min_seed_count <= 0:
            raise ConfigurationError("ValidationMatrixConfig.min_seed_count must be positive.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "require_d0": self.require_d0,
            "require_qd": self.require_qd,
            "require_ablation": self.require_ablation,
            "require_replay": self.require_replay,
            "require_capsule_metrics": self.require_capsule_metrics,
            "require_multi_seed": self.require_multi_seed,
            "min_seed_count": self.min_seed_count,
            "required_components": list(self.required_components),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ValidationMatrixConfig:
        return cls(
            _bool(data, "require_d0", True),
            _bool(data, "require_qd", True),
            _bool(data, "require_ablation", True),
            _bool(data, "require_replay", True),
            _bool(data, "require_capsule_metrics", False),
            _bool(data, "require_multi_seed", True),
            _int(data, "min_seed_count", 3),
            _str_tuple(data, "required_components"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ValidationMatrixResult:
    attempted: bool
    succeeded: bool
    passed_components: tuple[str, ...]
    missing_components: tuple[str, ...]
    seed_count: int
    failed_gates: tuple[str, ...]
    claim_ceiling: str
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "attempted": self.attempted,
            "succeeded": self.succeeded,
            "passed_components": list(self.passed_components),
            "missing_components": list(self.missing_components),
            "seed_count": self.seed_count,
            "failed_gates": list(self.failed_gates),
            "claim_ceiling": self.claim_ceiling,
            "reasons": list(self.reasons),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ValidationMatrixResult:
        return cls(
            _bool(data, "attempted", False),
            _bool(data, "succeeded", False),
            _str_tuple(data, "passed_components"),
            _str_tuple(data, "missing_components"),
            _int(data, "seed_count", 0),
            _str_tuple(data, "failed_gates"),
            _str(data, "claim_ceiling"),
            _str_tuple(data, "reasons"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


def evaluate_validation_matrix(
    bundle: EvidenceBundle, config: ValidationMatrixConfig
) -> ValidationMatrixResult:
    present = {record.source_component for record in bundle.records}
    if any(
        _is_d0_evidence(record.evidence_type, record.source_component) for record in bundle.records
    ):
        present.add("d0")
    if any(
        _is_qd_evidence(record.evidence_type, record.qd_archive_digest) for record in bundle.records
    ):
        present.add("qd")
    if any(record.witness_digest for record in bundle.records):
        present.add("witness")
    if any(record.replay_digest or record.evidence_type == "replay" for record in bundle.records):
        present.add("replay")
    if any(
        _is_ablation_evidence(record.evidence_type, record.source_component)
        for record in bundle.records
    ):
        present.add("ablation")
    required = set(config.required_components)
    if config.require_d0:
        required.add("d0")
    if config.require_qd:
        required.add("qd")
    if config.require_ablation:
        required.add("ablation")
    if config.require_replay:
        required.add("replay")
    if config.require_capsule_metrics:
        required.add("capsule_metrics")
    seeds = {record.seed for record in bundle.records}
    missing = tuple(sorted(required - present))
    failed: list[str] = []
    if missing:
        failed.append("missing_components")
    if config.require_multi_seed and len(seeds) < config.min_seed_count:
        failed.append("insufficient_seeds")
    if not bundle.claim_limitations:
        failed.append("missing_claim_limitations")
    if failed:
        claim_ceiling = "CANDIDATE" if len(seeds) > 0 else "NONE"
        if "missing_components" in failed:
            claim_ceiling = "CANDIDATE"
        if "insufficient_seeds" in failed or "missing_claim_limitations" in failed:
            claim_ceiling = "CANDIDATE"
    else:
        claim_ceiling = "EVIDENCE_SUPPORTED"
    return ValidationMatrixResult(
        True,
        not failed,
        tuple(sorted(present & required)),
        missing,
        len(seeds),
        tuple(failed),
        claim_ceiling,
        tuple(failed) if failed else ("validation_matrix_passed",),
    )


def _is_d0_evidence(evidence_type: str, source_component: str) -> bool:
    return evidence_type in {
        "d0_baseline",
        "d0_calibration",
        "d0_distance",
    } or source_component in {
        "d0",
        "d0_baseline",
        "discovery_witness",
    }


def _is_qd_evidence(evidence_type: str, qd_archive_digest: str) -> bool:
    return evidence_type in {"qd_archive", "qd_summary", "quality_diversity"} or bool(
        qd_archive_digest
    )


def _is_ablation_evidence(evidence_type: str, source_component: str) -> bool:
    return "ablation" in evidence_type or source_component == "ablation"


def _digest(payload: Mapping[str, JsonValue]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _str(data: Mapping[str, JsonValue], key: str, default: str | None = None) -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        raise ConfigurationError(f"{key} must be a string.")
    return value


def _bool(data: Mapping[str, JsonValue], key: str, default: bool) -> bool:
    value = data.get(key, default)
    if not isinstance(value, bool):
        raise ConfigurationError(f"{key} must be a boolean.")
    return value


def _int(data: Mapping[str, JsonValue], key: str, default: int) -> int:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{key} must be an integer.")
    return value


def _str_tuple(data: Mapping[str, JsonValue], key: str) -> tuple[str, ...]:
    raw = data.get(key, [])
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise ConfigurationError(f"{key} must be a list of strings.")
    return tuple(str(item) for item in raw)
