"""Limitation and failure-mode records for GENESIS evidence audits."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.claim_audit import ClaimType


class LimitationSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class LimitationRecord:
    limitation_id: str
    severity: LimitationSeverity
    component: str
    description: str
    impact: str
    mitigation: str = ""
    blocks_claims: tuple[ClaimType, ...] = ()

    def __post_init__(self) -> None:
        if not self.limitation_id or not self.component:
            raise ConfigurationError("LimitationRecord id/component must not be empty.")
        if not isinstance(self.severity, LimitationSeverity):
            object.__setattr__(self, "severity", LimitationSeverity(str(self.severity)))
        object.__setattr__(
            self,
            "blocks_claims",
            tuple(
                item if isinstance(item, ClaimType) else ClaimType(str(item))
                for item in self.blocks_claims
            ),
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "limitation_id": self.limitation_id,
            "severity": self.severity.value,
            "component": self.component,
            "description": self.description,
            "impact": self.impact,
            "mitigation": self.mitigation,
            "blocks_claims": [item.value for item in self.blocks_claims],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> LimitationRecord:
        return cls(
            _str(data, "limitation_id"),
            LimitationSeverity(_str(data, "severity", LimitationSeverity.INFO.value)),
            _str(data, "component"),
            _str(data, "description", ""),
            _str(data, "impact", ""),
            _str(data, "mitigation", ""),
            tuple(ClaimType(item) for item in _str_tuple(data, "blocks_claims")),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class FailureModeRecord:
    failure_id: str
    component: str
    trigger: str
    observed_behavior: str
    expected_behavior: str
    reproducible: bool
    seed: int | None = None
    trace_digest: str = ""
    mitigation: str = ""

    def __post_init__(self) -> None:
        if not self.failure_id or not self.component:
            raise ConfigurationError("FailureModeRecord failure_id/component must not be empty.")
        if self.seed is not None and (
            isinstance(self.seed, bool) or not isinstance(self.seed, int)
        ):
            raise ConfigurationError("FailureModeRecord.seed must be an integer or None.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "failure_id": self.failure_id,
            "component": self.component,
            "trigger": self.trigger,
            "observed_behavior": self.observed_behavior,
            "expected_behavior": self.expected_behavior,
            "reproducible": self.reproducible,
            "seed": self.seed,
            "trace_digest": self.trace_digest,
            "mitigation": self.mitigation,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> FailureModeRecord:
        seed_raw = data.get("seed")
        seed = None if seed_raw is None else _int(data, "seed", 0)
        return cls(
            _str(data, "failure_id"),
            _str(data, "component"),
            _str(data, "trigger", ""),
            _str(data, "observed_behavior", ""),
            _str(data, "expected_behavior", ""),
            _bool(data, "reproducible", False),
            seed,
            _str(data, "trace_digest", ""),
            _str(data, "mitigation", ""),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class LimitationsAuditResult:
    attempted: bool
    succeeded: bool
    critical_count: int
    blocked_claim_types: tuple[ClaimType, ...] = ()
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "blocked_claim_types",
            tuple(ClaimType(str(item)) for item in self.blocked_claim_types),
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "attempted": self.attempted,
            "succeeded": self.succeeded,
            "critical_count": self.critical_count,
            "blocked_claim_types": [item.value for item in self.blocked_claim_types],
            "reasons": list(self.reasons),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> LimitationsAuditResult:
        return cls(
            _bool(data, "attempted", False),
            _bool(data, "succeeded", False),
            _int(data, "critical_count", 0),
            tuple(ClaimType(item) for item in _str_tuple(data, "blocked_claim_types")),
            _str_tuple(data, "reasons"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


def audit_limitations(limitations: tuple[LimitationRecord, ...]) -> LimitationsAuditResult:
    critical = tuple(item for item in limitations if item.severity == LimitationSeverity.CRITICAL)
    blocked = tuple(
        sorted(
            {claim for item in critical for claim in item.blocks_claims},
            key=lambda item: item.value,
        )
    )
    reasons = ("critical_limitations",) if critical else ("limitations_validated",)
    return LimitationsAuditResult(True, not critical, len(critical), blocked, reasons)


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
