"""Research validation bundle records for GENESIS evidence audits.

These are typed evidence-bundle objects only. They do not run experiments,
generate reports, write files, or assert proof-grade claims.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError


@dataclass(frozen=True, slots=True)
class ValidationScenario:
    scenario_id: str
    description: str
    required_components: tuple[str, ...]
    config_digest: str
    expected_evidence: tuple[str, ...] = ()
    non_claims: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.scenario_id:
            msg = "ValidationScenario.scenario_id must not be empty."
            raise ConfigurationError(msg)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "scenario_id": self.scenario_id,
            "description": self.description,
            "required_components": list(self.required_components),
            "config_digest": self.config_digest,
            "expected_evidence": list(self.expected_evidence),
            "non_claims": list(self.non_claims),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ValidationScenario:
        return cls(
            scenario_id=_str(data, "scenario_id"),
            description=_str(data, "description", ""),
            required_components=_str_tuple(data, "required_components"),
            config_digest=_str(data, "config_digest"),
            expected_evidence=_str_tuple(data, "expected_evidence"),
            non_claims=_str_tuple(data, "non_claims"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ValidationRunRecord:
    run_id: str
    scenario_id: str
    seed: int
    trace_digest: str
    behavior_digest: str
    qd_archive_digest: str = ""
    witness_digest: str = ""
    ablation_digest: str = ""
    statistical_protocol_digest: str = ""
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.run_id or not self.scenario_id:
            msg = "ValidationRunRecord.run_id and scenario_id must not be empty."
            raise ConfigurationError(msg)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "run_id": self.run_id,
            "scenario_id": self.scenario_id,
            "seed": self.seed,
            "trace_digest": self.trace_digest,
            "behavior_digest": self.behavior_digest,
            "qd_archive_digest": self.qd_archive_digest,
            "witness_digest": self.witness_digest,
            "ablation_digest": self.ablation_digest,
            "statistical_protocol_digest": self.statistical_protocol_digest,
            "limitations": list(self.limitations),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ValidationRunRecord:
        return cls(
            run_id=_str(data, "run_id"),
            scenario_id=_str(data, "scenario_id"),
            seed=_int(data, "seed", 0),
            trace_digest=_str(data, "trace_digest"),
            behavior_digest=_str(data, "behavior_digest"),
            qd_archive_digest=_str(data, "qd_archive_digest", ""),
            witness_digest=_str(data, "witness_digest", ""),
            ablation_digest=_str(data, "ablation_digest", ""),
            statistical_protocol_digest=_str(data, "statistical_protocol_digest", ""),
            limitations=_str_tuple(data, "limitations"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ValidationBundle:
    bundle_id: str
    version: str
    scenarios: tuple[ValidationScenario, ...]
    run_records: tuple[ValidationRunRecord, ...]
    evidence_digests: tuple[str, ...] = ()
    claim_limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.bundle_id or not self.version:
            msg = "ValidationBundle.bundle_id and version must not be empty."
            raise ConfigurationError(msg)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "bundle_id": self.bundle_id,
            "version": self.version,
            "scenarios": [item.to_dict() for item in self.scenarios],
            "run_records": [item.to_dict() for item in self.run_records],
            "evidence_digests": list(self.evidence_digests),
            "claim_limitations": list(self.claim_limitations),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ValidationBundle:
        raw_scenarios = data.get("scenarios", [])
        raw_records = data.get("run_records", [])
        if not isinstance(raw_scenarios, list) or not isinstance(raw_records, list):
            msg = "ValidationBundle scenarios/run_records must be lists."
            raise ConfigurationError(msg)
        return cls(
            bundle_id=_str(data, "bundle_id"),
            version=_str(data, "version"),
            scenarios=tuple(
                ValidationScenario.from_dict(_mapping(item, "scenario")) for item in raw_scenarios
            ),
            run_records=tuple(
                ValidationRunRecord.from_dict(_mapping(item, "run_record")) for item in raw_records
            ),
            evidence_digests=_str_tuple(data, "evidence_digests"),
            claim_limitations=_str_tuple(data, "claim_limitations"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


def _digest(payload: Mapping[str, JsonValue]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _mapping(value: object, name: str) -> Mapping[str, JsonValue]:
    if not isinstance(value, Mapping):
        msg = f"{name} must be an object."
        raise ConfigurationError(msg)
    return value


def _str(data: Mapping[str, JsonValue], key: str, default: str | None = None) -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        msg = f"{key} must be a string."
        raise ConfigurationError(msg)
    return value


def _int(data: Mapping[str, JsonValue], key: str, default: int) -> int:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{key} must be an integer."
        raise ConfigurationError(msg)
    return value


def _str_tuple(data: Mapping[str, JsonValue], key: str) -> tuple[str, ...]:
    raw = data.get(key, [])
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        msg = f"{key} must be a list of strings."
        raise ConfigurationError(msg)
    return tuple(str(item) for item in raw)
