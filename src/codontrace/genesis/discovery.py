"""Typed discovery hooks for future GENESIS D0/Witness phases.

These objects are planning/audit scaffolds only. They do not implement D0,
Discovery Witness archives, open-endedness proofs, or discovery claims.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError


class DiscoveryClaimLevel(str, Enum):
    NONE = "none"
    CANDIDATE = "candidate"
    WITNESS_REQUIRED = "witness_required"
    EVIDENCE_SUPPORTED = "evidence_supported"
    SUPPORTED_BY_ABLATION = "supported_by_ablation"


@dataclass(frozen=True, slots=True)
class D0BaselineConfig:
    """D0 baseline calibration configuration; disabled until explicitly enabled."""

    enabled: bool = False
    behavior_descriptor_bins: dict[str, int] = field(default_factory=dict)
    min_reference_runs: int = 10
    min_seeds: int = 3
    novelty_threshold: float = 0.0

    def __post_init__(self) -> None:
        if self.min_reference_runs <= 0 or self.min_seeds <= 0:
            msg = "D0BaselineConfig min_reference_runs/min_seeds must be > 0."
            raise ConfigurationError(msg)
        if self.novelty_threshold < 0:
            msg = "D0BaselineConfig.novelty_threshold must be >= 0."
            raise ConfigurationError(msg)
        if any(value <= 0 for value in self.behavior_descriptor_bins.values()):
            msg = "D0BaselineConfig bins must be positive integers."
            raise ConfigurationError(msg)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "enabled": self.enabled,
            "behavior_descriptor_bins": dict(self.behavior_descriptor_bins),
            "min_reference_runs": self.min_reference_runs,
            "min_seeds": self.min_seeds,
            "novelty_threshold": self.novelty_threshold,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> D0BaselineConfig:
        bins = data.get("behavior_descriptor_bins", {})
        if not isinstance(bins, dict):
            msg = "behavior_descriptor_bins must be an object."
            raise ConfigurationError(msg)
        return cls(
            enabled=_bool(data, "enabled", False),
            behavior_descriptor_bins={
                str(k): _int_value(v, "behavior_descriptor_bins") for k, v in bins.items()
            },
            min_reference_runs=_int(data, "min_reference_runs", 10),
            min_seeds=_int(data, "min_seeds", 3),
            novelty_threshold=_float(data, "novelty_threshold", 0.0),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class DiscoveryWitnessStub:
    """Serializable planning object for a future witness archive."""

    witness_id: str
    claim_level: DiscoveryClaimLevel
    behavior_digest: str
    graph_digest: str
    vocabulary_digest: str
    capsule_store_digest: str
    required_evidence: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.witness_id:
            msg = "DiscoveryWitnessStub.witness_id must not be empty."
            raise ConfigurationError(msg)
        if not isinstance(self.claim_level, DiscoveryClaimLevel):
            object.__setattr__(self, "claim_level", DiscoveryClaimLevel(str(self.claim_level)))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "witness_id": self.witness_id,
            "claim_level": self.claim_level.value,
            "behavior_digest": self.behavior_digest,
            "graph_digest": self.graph_digest,
            "vocabulary_digest": self.vocabulary_digest,
            "capsule_store_digest": self.capsule_store_digest,
            "required_evidence": list(self.required_evidence),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> DiscoveryWitnessStub:
        return cls(
            witness_id=_str(data, "witness_id"),
            claim_level=DiscoveryClaimLevel(
                _str(data, "claim_level", DiscoveryClaimLevel.NONE.value)
            ),
            behavior_digest=_str(data, "behavior_digest"),
            graph_digest=_str(data, "graph_digest"),
            vocabulary_digest=_str(data, "vocabulary_digest"),
            capsule_store_digest=_str(data, "capsule_store_digest"),
            required_evidence=_str_tuple(data, "required_evidence"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


def _digest(payload: Mapping[str, JsonValue]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _str(data: Mapping[str, JsonValue], key: str, default: str | None = None) -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        msg = f"{key} must be a string."
        raise ConfigurationError(msg)
    return value


def _bool(data: Mapping[str, JsonValue], key: str, default: bool) -> bool:
    value = data.get(key, default)
    if not isinstance(value, bool):
        msg = f"{key} must be a boolean."
        raise ConfigurationError(msg)
    return value


def _int(data: Mapping[str, JsonValue], key: str, default: int) -> int:
    return _int_value(data.get(key, default), key)


def _int_value(value: object, key: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{key} must be an integer."
        raise ConfigurationError(msg)
    return value


def _float(data: Mapping[str, JsonValue], key: str, default: float) -> float:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int | float):
        msg = f"{key} must be numeric."
        raise ConfigurationError(msg)
    return float(value)


def _str_tuple(data: Mapping[str, JsonValue], key: str) -> tuple[str, ...]:
    raw = data.get(key, [])
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        msg = f"{key} must be a list of strings."
        raise ConfigurationError(msg)
    return tuple(str(item) for item in raw)
