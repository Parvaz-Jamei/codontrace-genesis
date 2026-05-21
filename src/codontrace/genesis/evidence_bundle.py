"""Auditable evidence-bundle objects for GENESIS validation.

These objects store references and digests only. They do not run experiments,
write files, generate reports, or perform publication automation.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.research_validation import ValidationScenario


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    evidence_id: str
    evidence_type: str
    source_component: str
    seed: int
    config_digest: str
    trace_digest: str
    replay_digest: str = ""
    behavior_digest: str = ""
    graph_digest: str = ""
    qd_archive_digest: str = ""
    witness_digest: str = ""
    limitation_ids: tuple[str, ...] = ()
    metadata: dict[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.evidence_id or not self.evidence_type or not self.source_component:
            raise ConfigurationError("EvidenceRecord id/type/source_component must not be empty.")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise ConfigurationError("EvidenceRecord.seed must be an integer.")
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "evidence_id": self.evidence_id,
            "evidence_type": self.evidence_type,
            "source_component": self.source_component,
            "seed": self.seed,
            "config_digest": self.config_digest,
            "trace_digest": self.trace_digest,
            "replay_digest": self.replay_digest,
            "behavior_digest": self.behavior_digest,
            "graph_digest": self.graph_digest,
            "qd_archive_digest": self.qd_archive_digest,
            "witness_digest": self.witness_digest,
            "limitation_ids": list(self.limitation_ids),
            "metadata": dict(sorted(self.metadata.items())),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> EvidenceRecord:
        return cls(
            _str(data, "evidence_id"),
            _str(data, "evidence_type"),
            _str(data, "source_component"),
            _int(data, "seed", 0),
            _str(data, "config_digest", ""),
            _str(data, "trace_digest", ""),
            _str(data, "replay_digest", ""),
            _str(data, "behavior_digest", ""),
            _str(data, "graph_digest", ""),
            _str(data, "qd_archive_digest", ""),
            _str(data, "witness_digest", ""),
            _str_tuple(data, "limitation_ids"),
            _mapping_to_dict(data.get("metadata", {}), "metadata"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class EvidenceBundle:
    bundle_id: str
    version: str
    records: tuple[EvidenceRecord, ...]
    scenarios: tuple[ValidationScenario, ...] = ()
    claim_limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.bundle_id or not self.version:
            raise ConfigurationError("EvidenceBundle.bundle_id and version must not be empty.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "bundle_id": self.bundle_id,
            "version": self.version,
            "records": [item.to_dict() for item in self.records],
            "scenarios": [item.to_dict() for item in self.scenarios],
            "claim_limitations": list(self.claim_limitations),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> EvidenceBundle:
        raw_records = data.get("records", [])
        raw_scenarios = data.get("scenarios", [])
        if not isinstance(raw_records, list) or not isinstance(raw_scenarios, list):
            raise ConfigurationError("EvidenceBundle records/scenarios must be lists.")
        return cls(
            _str(data, "bundle_id"),
            _str(data, "version"),
            tuple(EvidenceRecord.from_dict(_mapping(item, "record")) for item in raw_records),
            tuple(
                ValidationScenario.from_dict(_mapping(item, "scenario")) for item in raw_scenarios
            ),
            _str_tuple(data, "claim_limitations"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class EvidenceBundleValidationResult:
    attempted: bool
    succeeded: bool
    record_count: int
    missing_trace_digests: tuple[str, ...] = ()
    missing_config_digests: tuple[str, ...] = ()
    missing_limitations: tuple[str, ...] = ()
    duplicate_evidence_ids: tuple[str, ...] = ()
    unknown_limitation_ids: tuple[str, ...] = ()
    duplicate_limitation_ids: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "attempted": self.attempted,
            "succeeded": self.succeeded,
            "record_count": self.record_count,
            "missing_trace_digests": list(self.missing_trace_digests),
            "missing_config_digests": list(self.missing_config_digests),
            "missing_limitations": list(self.missing_limitations),
            "duplicate_evidence_ids": list(self.duplicate_evidence_ids),
            "unknown_limitation_ids": list(self.unknown_limitation_ids),
            "duplicate_limitation_ids": list(self.duplicate_limitation_ids),
            "reasons": list(self.reasons),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> EvidenceBundleValidationResult:
        return cls(
            _bool(data, "attempted", False),
            _bool(data, "succeeded", False),
            _int(data, "record_count", 0),
            _str_tuple(data, "missing_trace_digests"),
            _str_tuple(data, "missing_config_digests"),
            _str_tuple(data, "missing_limitations"),
            _str_tuple(data, "duplicate_evidence_ids"),
            _str_tuple(data, "unknown_limitation_ids"),
            _str_tuple(data, "duplicate_limitation_ids"),
            _str_tuple(data, "reasons"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


def validate_evidence_bundle(bundle: EvidenceBundle) -> EvidenceBundleValidationResult:
    ids = tuple(record.evidence_id for record in bundle.records)
    duplicates = tuple(sorted({item for item in ids if ids.count(item) > 1}))
    missing_trace = tuple(
        sorted(record.evidence_id for record in bundle.records if not record.trace_digest)
    )
    missing_config = tuple(
        sorted(record.evidence_id for record in bundle.records if not record.config_digest)
    )
    missing_limits = tuple(
        sorted(record.evidence_id for record in bundle.records if not record.limitation_ids)
    )
    known_limits = set(bundle.claim_limitations)
    referenced_limits = tuple(
        limitation_id for record in bundle.records for limitation_id in record.limitation_ids
    )
    unknown_limits = tuple(sorted({item for item in referenced_limits if item not in known_limits}))
    duplicate_limits = tuple(
        sorted(
            {item for item in bundle.claim_limitations if bundle.claim_limitations.count(item) > 1}
        )
    )
    reasons: list[str] = []
    if duplicates:
        reasons.append("duplicate_evidence_ids")
    if missing_trace:
        reasons.append("missing_trace_digest")
    if missing_config:
        reasons.append("missing_config_digest")
    if missing_limits or not bundle.claim_limitations:
        reasons.append("missing_limitations")
    if unknown_limits:
        reasons.append("unknown_limitation_ids")
    if duplicate_limits:
        reasons.append("duplicate_limitation_ids")
    return EvidenceBundleValidationResult(
        True,
        not reasons,
        len(bundle.records),
        missing_trace,
        missing_config,
        missing_limits,
        duplicates,
        unknown_limits,
        duplicate_limits,
        tuple(reasons) if reasons else ("evidence_bundle_validated",),
    )


def _digest(payload: Mapping[str, JsonValue]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _mapping(value: object, name: str) -> Mapping[str, JsonValue]:
    if not isinstance(value, Mapping):
        raise ConfigurationError(f"{name} must be an object.")
    return value


def _mapping_to_dict(value: object, name: str) -> dict[str, JsonValue]:
    if not isinstance(value, Mapping):
        raise ConfigurationError(f"{name} must be an object.")
    return dict(value)


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
