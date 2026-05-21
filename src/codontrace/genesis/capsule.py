"""Causal Capsule and Nexus stigmergy foundation for GENESIS experiments.

All objects are in-memory, deterministic, serializable, and dependency-free.
This module models environment-mediated capsule transfer scaffolding; it does
not prove knowledge transfer, causal learning, open-ended discovery, or full
stigmergic intelligence.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, cast

from codontrace._types import JsonValue, Position
from codontrace._numeric import finite_float, finite_json_dumps
from codontrace.errors import ConfigurationError
from codontrace.genesis.atp import GenesisATPState
from codontrace.genesis.causal_graph import CausalGraph, CausalNode
from codontrace.genesis.memory import EpisodicMemory


class CapsuleStatus(str, Enum):
    PROPOSED = "proposed"
    EMITTED = "emitted"
    ACTIVE = "active"
    EXPIRED = "expired"
    ADOPTED = "adopted"
    REJECTED = "rejected"
    DECAYED = "decayed"


class CapsuleAdoptionPolicy(str, Enum):
    NEVER = "never"
    THRESHOLD = "threshold"
    FITNESS_WEIGHTED = "fitness_weighted"
    NOVELTY_WEIGHTED = "novelty_weighted"
    SAFE_EXPERIMENTAL = "safe_experimental"


class SourceFitnessStatus(str, Enum):
    MEASURED = "measured"
    LAST_KNOWN = "last_known"
    PROVISIONAL = "provisional"
    UNAVAILABLE = "unavailable"


class CapsuleAdoptionBlockedReason(str, Enum):
    SOURCE_FITNESS_BELOW_THRESHOLD = "source_fitness_below_threshold"
    SOURCE_FITNESS_UNAVAILABLE = "source_fitness_unavailable"
    SOURCE_FITNESS_PROVISIONAL_NOT_ACCEPTED = "source_fitness_provisional_not_accepted"
    CONFIDENCE_BELOW_THRESHOLD = "confidence_below_threshold"
    INSUFFICIENT_LEARNING_ATP = "insufficient_learning_atp"
    INSUFFICIENT_RUNTIME_ATP = "insufficient_runtime_atp"
    GRAPH_DIGEST_REJECTED = "graph_digest_rejected"
    ADOPTION_POLICY_REJECTED = "adoption_policy_rejected"
    ADOPTION_POLICY_NEVER = "adoption_policy_never"
    TTL_EXPIRED = "ttl_expired"
    RADIUS_OUT_OF_RANGE = "radius_out_of_range"
    CAPSULE_LIMIT_REACHED = "capsule_limit_reached"
    DUPLICATE_CAPSULE = "duplicate_capsule"
    TARGET_CAPACITY_REACHED = "target_capacity_reached"
    TARGET_ALREADY_ADOPTED = "target_already_adopted"
    SOURCE_TARGET_SAME = "source_target_same"
    SHUFFLE_CONTROL_NOT_CLAIM_ELIGIBLE = "shuffle_control_not_claim_eligible"
    UNKNOWN = "unknown"


class CapsulePolicyProfile(str, Enum):
    SAFE = "safe"
    MODERATE = "moderate"
    SPAM_DIAGNOSTIC = "spam_diagnostic"
    OFF = "off"


class CapsuleShuffleMode(str, Enum):
    OFF = "off"
    CONTENT = "content"
    SOURCE = "source"
    TIMING = "timing"
    CONTENT_SOURCE_TIMING = "content_source_timing"
    RANDOM_METADATA = "random_metadata"


@dataclass(frozen=True, slots=True)
class CausalCapsule:
    """Serializable evidence capsule prepared for environment-mediated exchange."""

    capsule_id: str
    source_organism_id: str
    source_fitness: float
    source_graph_digest: str
    event_pattern: tuple[str, ...]
    predicted_outcome: str
    confidence: float
    emitted_tick: int
    ttl: int
    metadata: dict[str, JsonValue] = field(default_factory=dict)
    source_fitness_status: SourceFitnessStatus | str = SourceFitnessStatus.MEASURED
    source_fitness_tick: int | None = None
    source_fitness_digest: str = ""
    source_lineage_id: str = ""

    def __post_init__(self) -> None:
        if not self.capsule_id or not self.source_organism_id:
            msg = "CausalCapsule ids must not be empty."
            raise ConfigurationError(msg)
        object.__setattr__(self, "source_fitness", finite_float("CausalCapsule.source_fitness", self.source_fitness))
        object.__setattr__(self, "confidence", finite_float("CausalCapsule.confidence", self.confidence, probability=True))
        if self.emitted_tick < 0 or self.ttl < 0:
            msg = "CausalCapsule emitted_tick/ttl must be non-negative."
            raise ConfigurationError(msg)
        status = _source_fitness_status(self.source_fitness_status)
        object.__setattr__(self, "source_fitness_status", status)
        if self.source_fitness_tick is not None and self.source_fitness_tick < 0:
            msg = "CausalCapsule.source_fitness_tick must be non-negative or None."
            raise ConfigurationError(msg)
        if not self.source_fitness_digest:
            object.__setattr__(
                self,
                "source_fitness_digest",
                _digest(
                    {
                        "source_organism_id": self.source_organism_id,
                        "source_fitness": self.source_fitness,
                        "source_fitness_status": status.value,
                        "source_fitness_tick": self.source_fitness_tick,
                    }
                ),
            )

    @property
    def source_fitness_numeric_for_threshold(self) -> float | None:
        """Return numeric fitness only when threshold comparisons are valid."""

        return (
            None
            if self.source_fitness_status is SourceFitnessStatus.UNAVAILABLE
            else self.source_fitness
        )

    @property
    def created_tick(self) -> int:
        """Alias for emitted_tick used by schema-versioned capsule records."""

        return self.emitted_tick

    @property
    def expires_tick(self) -> int:
        """Alias for absolute expiry tick used by schema-versioned exports."""

        return self.expires_at

    @property
    def content_digest(self) -> str:
        """Digest only capsule content, excluding source/timing metadata."""

        return _digest(
            {
                "event_pattern": list(self.event_pattern),
                "predicted_outcome": self.predicted_outcome,
                "source_graph_digest": self.source_graph_digest,
            }
        )

    @property
    def expires_at(self) -> int:
        """Return the absolute tick at which this capsule expires."""

        return self.emitted_tick + self.ttl

    def active_at(self, tick: int) -> bool:
        """Return whether the capsule is active at an absolute tick."""

        return self.emitted_tick <= tick < self.expires_at

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "capsule_id": self.capsule_id,
            "source_organism_id": self.source_organism_id,
            "source_fitness": self.source_fitness,
            "source_fitness_status": _source_fitness_status(self.source_fitness_status).value,
            "source_fitness_numeric_for_threshold": self.source_fitness_numeric_for_threshold,
            "source_fitness_tick": self.source_fitness_tick,
            "source_fitness_digest": self.source_fitness_digest,
            "created_tick": self.created_tick,
            "expires_tick": self.expires_tick,
            "content_digest": self.content_digest,
            "source_lineage_id": self.source_lineage_id,
            "source_graph_digest": self.source_graph_digest,
            "event_pattern": list(self.event_pattern),
            "predicted_outcome": self.predicted_outcome,
            "confidence": self.confidence,
            "emitted_tick": self.emitted_tick,
            "ttl": self.ttl,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> CausalCapsule:
        metadata = data.get("metadata", {})
        if not isinstance(metadata, dict):
            msg = "CausalCapsule.metadata must be an object."
            raise ConfigurationError(msg)
        return cls(
            capsule_id=_str(data, "capsule_id"),
            source_organism_id=_str(data, "source_organism_id"),
            source_fitness=_float(data, "source_fitness", 0.0),
            source_fitness_status=SourceFitnessStatus(
                _str(data, "source_fitness_status", SourceFitnessStatus.MEASURED.value)
            ),
            source_fitness_tick=_optional_int(data, "source_fitness_tick"),
            source_fitness_digest=_str(data, "source_fitness_digest", ""),
            source_lineage_id=_str(data, "source_lineage_id", ""),
            source_graph_digest=_str(data, "source_graph_digest"),
            event_pattern=_str_tuple(data, "event_pattern"),
            predicted_outcome=_str(data, "predicted_outcome"),
            confidence=_float(data, "confidence", 0.0),
            emitted_tick=_int(data, "emitted_tick", 0),
            ttl=_int(data, "ttl", 0),
            metadata={str(k): v for k, v in metadata.items()},
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class CapsuleEmissionConfig:
    """Backward-compatible guarded config for capsule emission; disabled by default."""

    enabled: bool = False
    min_confidence: float = 0.5
    min_source_fitness: float = 0.0
    emission_cost_runtime_atp: float = 0.5
    emission_cost_learning_atp: float = 0.5
    ttl: int = 32
    max_capsules_per_tick: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "min_confidence", finite_float("min_confidence", self.min_confidence, probability=True))
        for value, name in (
            (self.min_source_fitness, "min_source_fitness"),
            (self.emission_cost_runtime_atp, "emission_cost_runtime_atp"),
            (self.emission_cost_learning_atp, "emission_cost_learning_atp"),
        ):
            if value < 0:
                msg = f"{name} must be >= 0."
                raise ConfigurationError(msg)
        if self.ttl < 0 or self.max_capsules_per_tick <= 0:
            msg = "ttl must be non-negative and max_capsules_per_tick must be > 0."
            raise ConfigurationError(msg)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "enabled": self.enabled,
            "min_confidence": self.min_confidence,
            "min_source_fitness": self.min_source_fitness,
            "emission_cost_runtime_atp": self.emission_cost_runtime_atp,
            "emission_cost_learning_atp": self.emission_cost_learning_atp,
            "ttl": self.ttl,
            "max_capsules_per_tick": self.max_capsules_per_tick,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> CapsuleEmissionConfig:
        return cls(
            enabled=_bool(data, "enabled", False),
            min_confidence=_float(data, "min_confidence", 0.5),
            min_source_fitness=_float(data, "min_source_fitness", 0.0),
            emission_cost_runtime_atp=_float(data, "emission_cost_runtime_atp", 0.5),
            emission_cost_learning_atp=_float(data, "emission_cost_learning_atp", 0.5),
            ttl=_int(data, "ttl", 32),
            max_capsules_per_tick=_int(data, "max_capsules_per_tick", 1),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class CapsuleEmissionResult:
    """Audit value for a capsule emission attempt."""

    attempted: bool
    succeeded: bool
    blocked_reason: str | None
    capsule: CausalCapsule | None
    consumed_runtime_atp: float
    consumed_learning_atp: float
    runtime_ledger_entry_id: int | None
    learning_ledger_entry_id: int | None

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "attempted": self.attempted,
            "succeeded": self.succeeded,
            "blocked_reason": self.blocked_reason,
            "capsule": None if self.capsule is None else self.capsule.to_dict(),
            "consumed_runtime_atp": self.consumed_runtime_atp,
            "consumed_learning_atp": self.consumed_learning_atp,
            "runtime_ledger_entry_id": self.runtime_ledger_entry_id,
            "learning_ledger_entry_id": self.learning_ledger_entry_id,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> CapsuleEmissionResult:
        capsule_raw = data.get("capsule")
        return cls(
            attempted=_bool(data, "attempted", False),
            succeeded=_bool(data, "succeeded", False),
            blocked_reason=_optional_str(data, "blocked_reason"),
            capsule=CausalCapsule.from_dict(capsule_raw)
            if isinstance(capsule_raw, Mapping)
            else None,
            consumed_runtime_atp=_float(data, "consumed_runtime_atp", 0.0),
            consumed_learning_atp=_float(data, "consumed_learning_atp", 0.0),
            runtime_ledger_entry_id=_optional_int(data, "runtime_ledger_entry_id"),
            learning_ledger_entry_id=_optional_int(data, "learning_ledger_entry_id"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class NexusSignal:
    """In-memory environment-mediated Nexus signal carrying a capsule id and TTL."""

    position: Position | None
    capsule_id: str
    emitted_tick: int
    ttl_remaining: int
    signal_digest: str = ""

    def __post_init__(self) -> None:
        if not self.capsule_id:
            msg = "NexusSignal.capsule_id must not be empty."
            raise ConfigurationError(msg)
        if self.emitted_tick < 0 or self.ttl_remaining < 0:
            msg = "NexusSignal emitted_tick/ttl_remaining must be non-negative."
            raise ConfigurationError(msg)
        if not self.signal_digest:
            object.__setattr__(self, "signal_digest", self._computed_digest())

    @classmethod
    def from_capsule(cls, capsule: CausalCapsule, position: Position | None = None) -> NexusSignal:
        return cls(position, capsule.capsule_id, capsule.emitted_tick, capsule.ttl)

    @property
    def expires_at(self) -> int:
        """Return the absolute tick at which this signal expires."""

        return self.emitted_tick + self.ttl_remaining

    def active_at(self, tick: int) -> bool:
        """Return whether the signal is active at an absolute tick."""

        return self.emitted_tick <= tick < self.expires_at

    def _computed_digest(self) -> str:
        payload: dict[str, JsonValue] = {
            "position": None if self.position is None else [self.position[0], self.position[1]],
            "capsule_id": self.capsule_id,
            "emitted_tick": self.emitted_tick,
            "ttl_remaining": self.ttl_remaining,
        }
        return _digest(payload)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "position": None if self.position is None else [self.position[0], self.position[1]],
            "capsule_id": self.capsule_id,
            "emitted_tick": self.emitted_tick,
            "ttl_remaining": self.ttl_remaining,
            "signal_digest": self.signal_digest,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> NexusSignal:
        return cls(
            position=_position_or_none(data.get("position")),
            capsule_id=_str(data, "capsule_id"),
            emitted_tick=_int(data, "emitted_tick", 0),
            ttl_remaining=_int(data, "ttl_remaining", 0),
            signal_digest=_str(data, "signal_digest", ""),
        )

    def digest(self) -> str:
        return self.signal_digest


@dataclass(frozen=True, slots=True)
class CapsuleTransferConfig:
    """Config for guarded in-memory capsule emission/read/adoption."""

    enabled: bool = False
    min_confidence: float = 0.5
    min_source_fitness: float = 0.0
    max_capsules_per_tick: int = 4
    read_radius: int = 1
    capsule_ttl: int = 32
    emission_cost_runtime_atp: float = 0.5
    emission_cost_learning_atp: float = 0.5
    read_cost_runtime_atp: float = 0.1
    adoption_cost_learning_atp: float = 1.0
    max_adoptions_per_organism: int = 1
    adoption_policy: CapsuleAdoptionPolicy = CapsuleAdoptionPolicy.THRESHOLD
    require_graph_digest_match: bool = False
    allow_cross_lineage_transfer: bool = True
    emit_on_nexus_action: bool = True
    emit_on_causal_update_success: bool = False
    max_capsules_read_per_tick: int | None = None
    adoption_min_confidence: float | None = None
    adoption_requires_atp_learning: bool = True
    max_emits_per_organism_per_tick: int = 1
    min_atp_runtime_to_emit: float = 1.0
    policy_profile: CapsulePolicyProfile | str = CapsulePolicyProfile.SAFE
    shuffle_mode: CapsuleShuffleMode | str = CapsuleShuffleMode.OFF
    accept_provisional_source_fitness: bool = True

    @property
    def effective_max_capsules_read_per_tick(self) -> int:
        return (
            self.max_capsules_per_tick
            if self.max_capsules_read_per_tick is None
            else self.max_capsules_read_per_tick
        )

    @property
    def effective_adoption_min_confidence(self) -> float:
        return (
            self.min_confidence
            if self.adoption_min_confidence is None
            else max(self.min_confidence, self.adoption_min_confidence)
        )

    @property
    def effective_adoption_cost_learning_atp(self) -> float:
        return self.adoption_cost_learning_atp if self.adoption_requires_atp_learning else 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "min_confidence", finite_float("min_confidence", self.min_confidence, probability=True))
        if not isinstance(self.adoption_policy, CapsuleAdoptionPolicy):
            object.__setattr__(
                self, "adoption_policy", CapsuleAdoptionPolicy(str(self.adoption_policy))
            )
        for field_name in (
            "min_source_fitness",
            "emission_cost_runtime_atp",
            "emission_cost_learning_atp",
            "read_cost_runtime_atp",
            "adoption_cost_learning_atp",
            "min_atp_runtime_to_emit",
        ):
            object.__setattr__(self, field_name, finite_float(field_name, getattr(self, field_name), non_negative=True))
        if (
            self.max_capsules_per_tick <= 0
            or self.effective_max_capsules_read_per_tick <= 0
            or self.read_radius < 0
            or self.capsule_ttl < 0
            or self.max_adoptions_per_organism < 0
            or self.max_emits_per_organism_per_tick <= 0
            or self.min_atp_runtime_to_emit < 0
        ):
            msg = "Capsule transfer counts/ttl are invalid."
            raise ConfigurationError(msg)
        if self.adoption_min_confidence is not None:
            object.__setattr__(self, "adoption_min_confidence", finite_float("adoption_min_confidence", self.adoption_min_confidence, probability=True))

    @classmethod
    def from_emission_config(cls, config: CapsuleEmissionConfig) -> CapsuleTransferConfig:
        return cls(
            enabled=config.enabled,
            min_confidence=config.min_confidence,
            min_source_fitness=config.min_source_fitness,
            max_capsules_per_tick=config.max_capsules_per_tick,
            capsule_ttl=config.ttl,
            emission_cost_runtime_atp=config.emission_cost_runtime_atp,
            emission_cost_learning_atp=config.emission_cost_learning_atp,
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "enabled": self.enabled,
            "min_confidence": self.min_confidence,
            "min_source_fitness": self.min_source_fitness,
            "max_capsules_per_tick": self.max_capsules_per_tick,
            "read_radius": self.read_radius,
            "capsule_ttl": self.capsule_ttl,
            "emission_cost_runtime_atp": self.emission_cost_runtime_atp,
            "emission_cost_learning_atp": self.emission_cost_learning_atp,
            "read_cost_runtime_atp": self.read_cost_runtime_atp,
            "adoption_cost_learning_atp": self.adoption_cost_learning_atp,
            "max_adoptions_per_organism": self.max_adoptions_per_organism,
            "adoption_policy": self.adoption_policy.value,
            "require_graph_digest_match": self.require_graph_digest_match,
            "allow_cross_lineage_transfer": self.allow_cross_lineage_transfer,
            "emit_on_nexus_action": self.emit_on_nexus_action,
            "emit_on_causal_update_success": self.emit_on_causal_update_success,
            "max_capsules_read_per_tick": self.max_capsules_read_per_tick,
            "adoption_min_confidence": self.adoption_min_confidence,
            "adoption_requires_atp_learning": self.adoption_requires_atp_learning,
            "max_emits_per_organism_per_tick": self.max_emits_per_organism_per_tick,
            "min_atp_runtime_to_emit": self.min_atp_runtime_to_emit,
            "policy_profile": _capsule_policy_profile(self.policy_profile).value,
            "shuffle_mode": _capsule_shuffle_mode(self.shuffle_mode).value,
            "accept_provisional_source_fitness": self.accept_provisional_source_fitness,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> CapsuleTransferConfig:
        return cls(
            enabled=_bool(data, "enabled", False),
            min_confidence=_float(data, "min_confidence", 0.5),
            min_source_fitness=_float(data, "min_source_fitness", 0.0),
            max_capsules_per_tick=_int(data, "max_capsules_per_tick", 4),
            read_radius=_int(data, "read_radius", 1),
            capsule_ttl=_int(data, "capsule_ttl", 32),
            emission_cost_runtime_atp=_float(data, "emission_cost_runtime_atp", 0.5),
            emission_cost_learning_atp=_float(data, "emission_cost_learning_atp", 0.5),
            read_cost_runtime_atp=_float(data, "read_cost_runtime_atp", 0.1),
            adoption_cost_learning_atp=_float(data, "adoption_cost_learning_atp", 1.0),
            max_adoptions_per_organism=_int(data, "max_adoptions_per_organism", 1),
            adoption_policy=CapsuleAdoptionPolicy(
                _str(data, "adoption_policy", CapsuleAdoptionPolicy.THRESHOLD.value)
            ),
            require_graph_digest_match=_bool(data, "require_graph_digest_match", False),
            allow_cross_lineage_transfer=_bool(data, "allow_cross_lineage_transfer", True),
            emit_on_nexus_action=_bool(data, "emit_on_nexus_action", True),
            emit_on_causal_update_success=_bool(data, "emit_on_causal_update_success", False),
            max_capsules_read_per_tick=None
            if data.get("max_capsules_read_per_tick") is None
            else _int(data, "max_capsules_read_per_tick", 4),
            adoption_min_confidence=None
            if data.get("adoption_min_confidence") is None
            else _float(data, "adoption_min_confidence", 0.0),
            adoption_requires_atp_learning=_bool(data, "adoption_requires_atp_learning", True),
            max_emits_per_organism_per_tick=_int(data, "max_emits_per_organism_per_tick", 1),
            min_atp_runtime_to_emit=_float(data, "min_atp_runtime_to_emit", 1.0),
            policy_profile=CapsulePolicyProfile(
                _str(data, "policy_profile", CapsulePolicyProfile.SAFE.value)
            ),
            shuffle_mode=CapsuleShuffleMode(
                _str(data, "shuffle_mode", CapsuleShuffleMode.OFF.value)
            ),
            accept_provisional_source_fitness=_bool(
                data, "accept_provisional_source_fitness", True
            ),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(slots=True)
class CapsuleStore:
    """In-memory deterministic store for causal capsules."""

    capsules: tuple[CausalCapsule, ...] = ()

    def deposit(self, capsule: CausalCapsule, *, replace_existing: bool = False) -> None:
        existing = {item.capsule_id: item for item in self.capsules}
        if capsule.capsule_id in existing and not replace_existing:
            msg = f"Capsule {capsule.capsule_id!r} already exists."
            raise ConfigurationError(msg)
        existing[capsule.capsule_id] = capsule
        self.capsules = tuple(existing[key] for key in sorted(existing))

    def active_at(self, tick: int) -> tuple[CausalCapsule, ...]:
        return tuple(
            sorted(
                (capsule for capsule in self.capsules if capsule.active_at(tick)),
                key=lambda item: (item.emitted_tick, item.capsule_id, item.digest()),
            )
        )

    def nearby(
        self,
        position: Position | None,
        radius: int,
        *,
        tick: int | None = None,
        include_global: bool = False,
    ) -> tuple[CausalCapsule, ...]:
        """Return active capsules within Manhattan ``radius`` of ``position``.

        Capsules without a stored ``metadata["position"]`` are treated as
        global. A local query includes those global capsules only when
        ``include_global=True``; ``position=None`` returns only global capsules.
        """

        if radius < 0:
            msg = "radius cannot be negative."
            raise ConfigurationError(msg)
        resolved_tick = (
            tick
            if tick is not None
            else max((capsule.emitted_tick for capsule in self.capsules), default=0)
        )
        matches: list[CausalCapsule] = []
        for capsule in self.active_at(resolved_tick):
            capsule_position = _capsule_position(capsule)
            if position is None:
                if capsule_position is None:
                    matches.append(capsule)
                continue
            if capsule_position is None:
                if include_global:
                    matches.append(capsule)
                continue
            if _manhattan(position, capsule_position) <= radius:
                matches.append(capsule)
        return tuple(
            sorted(matches, key=lambda item: (item.emitted_tick, item.capsule_id, item.digest()))
        )

    def decay(self, tick: int) -> None:
        """Expire old capsules without rewriting TTL into remaining time."""

        self.expire(tick)

    def expire(self, tick: int) -> None:
        self.capsules = self.active_at(tick)

    def digest(self) -> str:
        return _digest(self.to_dict())

    def to_dict(self) -> dict[str, JsonValue]:
        return {"capsules": [capsule.to_dict() for capsule in self.capsules]}

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> CapsuleStore:
        raw = data.get("capsules", [])
        if not isinstance(raw, list):
            msg = "CapsuleStore.capsules must be a list."
            raise ConfigurationError(msg)
        return cls(
            tuple(CausalCapsule.from_dict(item) for item in raw if isinstance(item, Mapping))
        )


@dataclass(frozen=True, slots=True)
class CapsuleReadResult:
    attempted: bool
    succeeded: bool
    blocked_reason: str | None
    capsules_seen: int
    capsules_read: tuple[CausalCapsule, ...]
    consumed_runtime_atp: float
    runtime_ledger_entry_id: int | None
    store_digest_before: str
    store_digest_after: str
    shuffle_records: tuple[CapsuleShuffleRecord, ...] = ()

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "attempted": self.attempted,
            "succeeded": self.succeeded,
            "blocked_reason": self.blocked_reason,
            "capsules_seen": self.capsules_seen,
            "capsules_read": [capsule.to_dict() for capsule in self.capsules_read],
            "consumed_runtime_atp": self.consumed_runtime_atp,
            "runtime_ledger_entry_id": self.runtime_ledger_entry_id,
            "store_digest_before": self.store_digest_before,
            "store_digest_after": self.store_digest_after,
            "shuffle_records": [record.to_dict() for record in self.shuffle_records],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> CapsuleReadResult:
        raw = data.get("capsules_read", [])
        if not isinstance(raw, list):
            msg = "capsules_read must be a list."
            raise ConfigurationError(msg)
        raw_shuffle = data.get("shuffle_records", [])
        if not isinstance(raw_shuffle, list):
            msg = "shuffle_records must be a list."
            raise ConfigurationError(msg)
        return cls(
            attempted=_bool(data, "attempted", False),
            succeeded=_bool(data, "succeeded", False),
            blocked_reason=_optional_str(data, "blocked_reason"),
            capsules_seen=_int(data, "capsules_seen", 0),
            capsules_read=tuple(
                CausalCapsule.from_dict(item) for item in raw if isinstance(item, Mapping)
            ),
            consumed_runtime_atp=_float(data, "consumed_runtime_atp", 0.0),
            runtime_ledger_entry_id=_optional_int(data, "runtime_ledger_entry_id"),
            store_digest_before=_str(data, "store_digest_before"),
            store_digest_after=_str(data, "store_digest_after"),
            shuffle_records=tuple(
                CapsuleShuffleRecord.from_dict(item)
                for item in raw_shuffle
                if isinstance(item, Mapping)
            ),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class CapsuleAdoptionResult:
    attempted: bool
    succeeded: bool
    blocked_reason: str | None
    capsule_id: str | None
    target_organism_id: str
    consumed_learning_atp: float
    learning_ledger_entry_id: int | None
    graph_digest_before: str
    graph_digest_after: str
    memory_digest_before: str | None
    memory_digest_after: str | None
    adopted_edges: int
    rejected_edges: int
    transfer_effect_estimate: float

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "attempted": self.attempted,
            "succeeded": self.succeeded,
            "blocked_reason": self.blocked_reason,
            "capsule_id": self.capsule_id,
            "target_organism_id": self.target_organism_id,
            "consumed_learning_atp": self.consumed_learning_atp,
            "learning_ledger_entry_id": self.learning_ledger_entry_id,
            "graph_digest_before": self.graph_digest_before,
            "graph_digest_after": self.graph_digest_after,
            "memory_digest_before": self.memory_digest_before,
            "memory_digest_after": self.memory_digest_after,
            "adopted_edges": self.adopted_edges,
            "rejected_edges": self.rejected_edges,
            "transfer_effect_estimate": self.transfer_effect_estimate,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> CapsuleAdoptionResult:
        return cls(
            attempted=_bool(data, "attempted", False),
            succeeded=_bool(data, "succeeded", False),
            blocked_reason=_optional_str(data, "blocked_reason"),
            capsule_id=_optional_str(data, "capsule_id"),
            target_organism_id=_str(data, "target_organism_id"),
            consumed_learning_atp=_float(data, "consumed_learning_atp", 0.0),
            learning_ledger_entry_id=_optional_int(data, "learning_ledger_entry_id"),
            graph_digest_before=_str(data, "graph_digest_before"),
            graph_digest_after=_str(data, "graph_digest_after"),
            memory_digest_before=_optional_str(data, "memory_digest_before"),
            memory_digest_after=_optional_str(data, "memory_digest_after"),
            adopted_edges=_int(data, "adopted_edges", 0),
            rejected_edges=_int(data, "rejected_edges", 0),
            transfer_effect_estimate=_float(data, "transfer_effect_estimate", 0.0),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class CapsuleAdoptionRecord:
    """Machine-readable per-capsule adoption attempt record."""

    capsule_id: str
    source_organism_id: str
    target_organism_id: str
    emitted_tick: int
    read_tick: int
    adoption_attempt_tick: int
    adoption_success: bool
    blocked_reason: str | None
    source_fitness: float
    source_fitness_status: SourceFitnessStatus | str
    confidence: float
    runtime_atp_before: float
    learning_atp_before: float
    runtime_atp_after: float | None = None
    learning_atp_after: float | None = None
    source_fitness_numeric_for_threshold: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "source_fitness_status", _source_fitness_status(self.source_fitness_status)
        )
        for field_name in ("source_fitness", "confidence", "runtime_atp_before", "learning_atp_before"):
            object.__setattr__(self, field_name, finite_float(f"CapsuleAdoptionRecord.{field_name}", getattr(self, field_name)))
        if self.source_fitness_numeric_for_threshold is not None:
            object.__setattr__(self, "source_fitness_numeric_for_threshold", finite_float("CapsuleAdoptionRecord.source_fitness_numeric_for_threshold", self.source_fitness_numeric_for_threshold))
        if self.runtime_atp_after is None:
            object.__setattr__(self, "runtime_atp_after", self.runtime_atp_before)
        if self.learning_atp_after is None:
            object.__setattr__(self, "learning_atp_after", self.learning_atp_before)
        object.__setattr__(self, "runtime_atp_after", finite_float("CapsuleAdoptionRecord.runtime_atp_after", self.runtime_atp_after))
        object.__setattr__(self, "learning_atp_after", finite_float("CapsuleAdoptionRecord.learning_atp_after", self.learning_atp_after))
        if (
            self.source_fitness_numeric_for_threshold is None
            and _source_fitness_status(self.source_fitness_status)
            is not SourceFitnessStatus.UNAVAILABLE
        ):
            object.__setattr__(self, "source_fitness_numeric_for_threshold", self.source_fitness)
        if _source_fitness_status(self.source_fitness_status) is SourceFitnessStatus.UNAVAILABLE:
            object.__setattr__(self, "source_fitness_numeric_for_threshold", None)
        if self.blocked_reason is None and not self.adoption_success:
            object.__setattr__(self, "blocked_reason", CapsuleAdoptionBlockedReason.UNKNOWN.value)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "capsule_id": self.capsule_id,
            "source_organism_id": self.source_organism_id,
            "target_organism_id": self.target_organism_id,
            "emitted_tick": self.emitted_tick,
            "read_tick": self.read_tick,
            "adoption_attempt_tick": self.adoption_attempt_tick,
            "adoption_success": self.adoption_success,
            "blocked_reason": self.blocked_reason,
            "source_fitness": self.source_fitness,
            "source_fitness_status": _source_fitness_status(self.source_fitness_status).value,
            "source_fitness_numeric_for_threshold": self.source_fitness_numeric_for_threshold,
            "confidence": self.confidence,
            "runtime_atp_before": self.runtime_atp_before,
            "learning_atp_before": self.learning_atp_before,
            "runtime_atp_after": self.runtime_atp_after,
            "learning_atp_after": self.learning_atp_after,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> CapsuleAdoptionRecord:
        return cls(
            capsule_id=_str(data, "capsule_id"),
            source_organism_id=_str(data, "source_organism_id"),
            target_organism_id=_str(data, "target_organism_id"),
            emitted_tick=_int(data, "emitted_tick", 0),
            read_tick=_int(data, "read_tick", 0),
            adoption_attempt_tick=_int(data, "adoption_attempt_tick", 0),
            adoption_success=_bool(data, "adoption_success", False),
            blocked_reason=_optional_str(data, "blocked_reason"),
            source_fitness=_float(data, "source_fitness", 0.0),
            source_fitness_status=SourceFitnessStatus(
                _str(data, "source_fitness_status", SourceFitnessStatus.UNAVAILABLE.value)
            ),
            confidence=_float(data, "confidence", 0.0),
            runtime_atp_before=_float(data, "runtime_atp_before", 0.0),
            learning_atp_before=_float(data, "learning_atp_before", 0.0),
            runtime_atp_after=_optional_float(data, "runtime_atp_after"),
            learning_atp_after=_optional_float(data, "learning_atp_after"),
            source_fitness_numeric_for_threshold=_optional_float(
                data, "source_fitness_numeric_for_threshold"
            ),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


def capsule_policy_profile_config(profile: CapsulePolicyProfile | str) -> CapsuleTransferConfig:
    """Return a standard capsule policy profile without mutating global state."""

    resolved = _capsule_policy_profile(profile)
    if resolved is CapsulePolicyProfile.OFF:
        return CapsuleTransferConfig(enabled=False, policy_profile=resolved)
    if resolved is CapsulePolicyProfile.SPAM_DIAGNOSTIC:
        return CapsuleTransferConfig(
            enabled=True,
            min_confidence=0.0,
            adoption_min_confidence=0.0,
            min_source_fitness=0.0,
            max_capsules_per_tick=32,
            max_capsules_read_per_tick=32,
            max_adoptions_per_organism=16,
            adoption_requires_atp_learning=False,
            emission_cost_runtime_atp=0.0,
            emission_cost_learning_atp=0.0,
            adoption_cost_learning_atp=0.0,
            min_atp_runtime_to_emit=0.0,
            policy_profile=resolved,
        )
    if resolved is CapsulePolicyProfile.MODERATE:
        return CapsuleTransferConfig(
            enabled=True,
            min_confidence=0.45,
            adoption_min_confidence=0.55,
            min_source_fitness=2.0,
            max_capsules_per_tick=4,
            max_capsules_read_per_tick=4,
            max_adoptions_per_organism=2,
            adoption_requires_atp_learning=True,
            min_atp_runtime_to_emit=5.0,
            emission_cost_runtime_atp=0.4,
            emission_cost_learning_atp=0.2,
            adoption_cost_learning_atp=0.4,
            policy_profile=resolved,
        )
    return CapsuleTransferConfig(
        enabled=True,
        min_confidence=0.55,
        adoption_min_confidence=0.60,
        min_source_fitness=5.0,
        max_capsules_per_tick=2,
        max_capsules_read_per_tick=2,
        max_adoptions_per_organism=1,
        adoption_requires_atp_learning=True,
        min_atp_runtime_to_emit=8.0,
        emission_cost_runtime_atp=0.5,
        emission_cost_learning_atp=0.25,
        adoption_cost_learning_atp=0.5,
        policy_profile=resolved,
    )


@dataclass(frozen=True, slots=True)
class CapsuleShuffleRecord:
    real_capsule_digest: str
    shuffled_capsule_digest: str
    shuffle_mode: CapsuleShuffleMode | str
    source_changed: bool
    content_changed: bool
    timing_changed: bool
    claim_eligible: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "shuffle_mode", _capsule_shuffle_mode(self.shuffle_mode))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "real_capsule_digest": self.real_capsule_digest,
            "shuffled_capsule_digest": self.shuffled_capsule_digest,
            "shuffle_mode": _capsule_shuffle_mode(self.shuffle_mode).value,
            "source_changed": self.source_changed,
            "content_changed": self.content_changed,
            "timing_changed": self.timing_changed,
            "claim_eligible": self.claim_eligible,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> CapsuleShuffleRecord:
        return cls(
            real_capsule_digest=_str(data, "real_capsule_digest"),
            shuffled_capsule_digest=_str(data, "shuffled_capsule_digest"),
            shuffle_mode=CapsuleShuffleMode(
                _str(data, "shuffle_mode", CapsuleShuffleMode.OFF.value)
            ),
            source_changed=_bool(data, "source_changed", False),
            content_changed=_bool(data, "content_changed", False),
            timing_changed=_bool(data, "timing_changed", False),
            claim_eligible=_bool(data, "claim_eligible", False),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class CapsuleTransferResult:
    emitted: int
    read: int
    adopted: int
    expired: int
    capsule_store_digest_before: str
    capsule_store_digest_after: str
    results: tuple[CapsuleEmissionResult | CapsuleReadResult | CapsuleAdoptionResult, ...]

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "emitted": self.emitted,
            "read": self.read,
            "adopted": self.adopted,
            "expired": self.expired,
            "capsule_store_digest_before": self.capsule_store_digest_before,
            "capsule_store_digest_after": self.capsule_store_digest_after,
            "results": [result.to_dict() for result in self.results],
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(slots=True)
class NexusStigmergyLayer:
    """Environment-mediated in-memory capsule/signal layer."""

    store: CapsuleStore = field(default_factory=CapsuleStore)
    signals: tuple[NexusSignal, ...] = ()

    def deposit(self, capsule: CausalCapsule, position: Position | None = None) -> NexusSignal:
        stored_capsule = capsule
        if position is not None and _capsule_position(capsule) is None:
            stored_capsule = replace(
                capsule,
                metadata={**capsule.metadata, "position": [position[0], position[1]]},
            )
        self.store.deposit(stored_capsule)
        signal = NexusSignal.from_capsule(stored_capsule, position=position)
        self.signals = tuple(
            sorted(
                (*self.signals, signal),
                key=lambda item: (item.emitted_tick, item.capsule_id, str(item.position)),
            )
        )
        return signal

    def active_signals(self, tick: int) -> tuple[NexusSignal, ...]:
        return tuple(signal for signal in self.signals if signal.active_at(tick))

    def decay(self, tick: int) -> None:
        """Expire old signals/capsules without shortening absolute TTL."""

        self.expire(tick)

    def expire(self, tick: int) -> None:
        active_ids = {signal.capsule_id for signal in self.active_signals(tick)}
        self.signals = tuple(signal for signal in self.signals if signal.capsule_id in active_ids)
        self.store.capsules = tuple(
            capsule for capsule in self.store.capsules if capsule.capsule_id in active_ids
        )

    def digest(self) -> str:
        return _digest(self.to_dict())

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "store": self.store.to_dict(),
            "signals": [signal.to_dict() for signal in self.signals],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> NexusStigmergyLayer:
        raw_signals = data.get("signals", [])
        store_raw = data.get("store", {})
        if not isinstance(raw_signals, list) or not isinstance(store_raw, Mapping):
            msg = "NexusStigmergyLayer requires store and signals."
            raise ConfigurationError(msg)
        return cls(
            store=CapsuleStore.from_dict(store_raw),
            signals=tuple(
                NexusSignal.from_dict(item) for item in raw_signals if isinstance(item, Mapping)
            ),
        )


@dataclass(frozen=True, slots=True)
class CapsuleTransferMetric:
    source_capsule_id: str
    target_organism_id: str
    pre_adoption_fitness: float | None
    post_adoption_fitness: float | None
    pre_behavior_digest: str | None
    post_behavior_digest: str | None
    pre_graph_digest: str
    post_graph_digest: str
    effect_score: float
    confidence: float
    interpretation: str

    def __post_init__(self) -> None:
        if self.pre_adoption_fitness is not None:
            object.__setattr__(self, "pre_adoption_fitness", finite_float("CapsuleTransferMetric.pre_adoption_fitness", self.pre_adoption_fitness))
        if self.post_adoption_fitness is not None:
            object.__setattr__(self, "post_adoption_fitness", finite_float("CapsuleTransferMetric.post_adoption_fitness", self.post_adoption_fitness))
        object.__setattr__(self, "effect_score", finite_float("CapsuleTransferMetric.effect_score", self.effect_score))
        object.__setattr__(self, "confidence", finite_float("CapsuleTransferMetric.confidence", self.confidence, probability=True))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "source_capsule_id": self.source_capsule_id,
            "target_organism_id": self.target_organism_id,
            "pre_adoption_fitness": self.pre_adoption_fitness,
            "post_adoption_fitness": self.post_adoption_fitness,
            "pre_behavior_digest": self.pre_behavior_digest,
            "post_behavior_digest": self.post_behavior_digest,
            "pre_graph_digest": self.pre_graph_digest,
            "post_graph_digest": self.post_graph_digest,
            "effect_score": self.effect_score,
            "confidence": self.confidence,
            "interpretation": self.interpretation,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> CapsuleTransferMetric:
        return cls(
            source_capsule_id=_str(data, "source_capsule_id"),
            target_organism_id=_str(data, "target_organism_id"),
            pre_adoption_fitness=_optional_float(data, "pre_adoption_fitness"),
            post_adoption_fitness=_optional_float(data, "post_adoption_fitness"),
            pre_behavior_digest=_optional_str(data, "pre_behavior_digest"),
            post_behavior_digest=_optional_str(data, "post_behavior_digest"),
            pre_graph_digest=_str(data, "pre_graph_digest"),
            post_graph_digest=_str(data, "post_graph_digest"),
            effect_score=_float(data, "effect_score", 0.0),
            confidence=_float(data, "confidence", 0.0),
            interpretation=_str(data, "interpretation"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


def emit_causal_capsule(
    organism: Any,
    graph: CausalGraph,
    fitness_result: Any,
    atp_state: GenesisATPState,
    config: CapsuleTransferConfig,
    *,
    tick: int,
) -> CapsuleEmissionResult:
    """Emit a capsule after threshold and ATP checks; no graph merge occurs."""

    if not config.enabled:
        return _emission_blocked("capsule_transfer_disabled")
    fitness = finite_float("fitness_result.score", getattr(fitness_result, "score", 0.0))
    if fitness < config.min_source_fitness:
        return _emission_blocked("source_fitness_below_threshold")
    confidence = _capsule_confidence(graph, fitness)
    if confidence < config.min_confidence:
        return _emission_blocked("confidence_below_threshold")
    if not atp_state.can_execute(config.emission_cost_runtime_atp):
        return _emission_blocked("insufficient_runtime_atp")
    if not atp_state.can_learn(config.emission_cost_learning_atp):
        return _emission_blocked("insufficient_learning_atp")
    organism_id = str(getattr(organism, "id", getattr(organism, "organism_id", "organism")))
    runtime_id = atp_state.debit_runtime(
        config.emission_cost_runtime_atp,
        tick=tick,
        organism_id=organism_id,
        codon="capsule",
        action="EMIT_CAUSAL_CAPSULE",
        reason="capsule_emission_runtime_cost",
    )
    learning_id = atp_state.debit_learning(
        config.emission_cost_learning_atp,
        tick=tick,
        organism_id=organism_id,
        reason="capsule_emission_learning_cost",
        event_ref=graph.digest(),
    )
    pattern = tuple(edge.relation for edge in graph.edges[: min(3, len(graph.edges))]) or (
        "no_edges",
    )
    outcome = graph.edges[0].target if graph.edges else "outcome:unknown"
    capsule = CausalCapsule(
        capsule_id=_stable_id("capsule", organism_id, graph.digest(), tick, fitness),
        source_organism_id=organism_id,
        source_fitness=fitness,
        source_graph_digest=graph.digest(),
        event_pattern=pattern,
        predicted_outcome=outcome,
        confidence=confidence,
        emitted_tick=tick,
        ttl=config.capsule_ttl,
        metadata={"status": CapsuleStatus.EMITTED.value},
    )
    return CapsuleEmissionResult(
        attempted=True,
        succeeded=True,
        blocked_reason=None,
        capsule=capsule,
        consumed_runtime_atp=config.emission_cost_runtime_atp,
        consumed_learning_atp=config.emission_cost_learning_atp,
        runtime_ledger_entry_id=runtime_id,
        learning_ledger_entry_id=learning_id,
    )


def read_nexus_capsules(
    organism: Any,
    layer: NexusStigmergyLayer,
    atp_state: GenesisATPState,
    config: CapsuleTransferConfig,
    *,
    tick: int,
) -> CapsuleReadResult:
    before = layer.digest()
    if not config.enabled:
        return _read_blocked("capsule_transfer_disabled", before)
    if not atp_state.can_execute(config.read_cost_runtime_atp):
        return _read_blocked("insufficient_runtime_atp", before)
    organism_id = str(getattr(organism, "id", getattr(organism, "organism_id", "organism")))
    ledger_id = atp_state.debit_runtime(
        config.read_cost_runtime_atp,
        tick=tick,
        organism_id=organism_id,
        codon="capsule",
        action="READ_NEXUS_CAPSULE",
        reason="capsule_read_runtime_cost",
    )
    position = getattr(organism, "position", None)
    nearby_capsules = layer.store.nearby(
        position if position is None or isinstance(position, tuple) else None,
        config.read_radius,
        tick=tick,
        include_global=True,
    )
    capsules = nearby_capsules[: config.effective_max_capsules_read_per_tick]
    capsules, shuffle_records = apply_capsule_shuffle_control(
        capsules, config.shuffle_mode, tick=tick, target_organism_id=organism_id
    )
    return CapsuleReadResult(
        attempted=True,
        succeeded=bool(capsules),
        blocked_reason=None if capsules else "no_nearby_active_capsules",
        capsules_seen=len(nearby_capsules),
        capsules_read=capsules,
        consumed_runtime_atp=config.read_cost_runtime_atp,
        runtime_ledger_entry_id=ledger_id,
        store_digest_before=before,
        store_digest_after=layer.digest(),
        shuffle_records=shuffle_records,
    )


def adopt_causal_capsule(
    organism: Any,
    capsule: CausalCapsule,
    graph: CausalGraph,
    memory: EpisodicMemory | None,
    atp_state: GenesisATPState,
    config: CapsuleTransferConfig,
    *,
    tick: int,
) -> CapsuleAdoptionResult:
    graph_before = graph.digest()
    memory_before = None if memory is None else memory.digest()
    organism_id = str(getattr(organism, "id", getattr(organism, "organism_id", "organism")))
    if not config.enabled:
        return _adoption_blocked(
            "capsule_transfer_disabled", capsule, organism_id, graph_before, memory_before
        )
    if organism_id == capsule.source_organism_id:
        return _adoption_blocked(
            CapsuleAdoptionBlockedReason.SOURCE_TARGET_SAME.value,
            capsule,
            organism_id,
            graph_before,
            memory_before,
        )
    if config.adoption_policy is CapsuleAdoptionPolicy.NEVER:
        return _adoption_blocked(
            CapsuleAdoptionBlockedReason.ADOPTION_POLICY_NEVER.value,
            capsule,
            organism_id,
            graph_before,
            memory_before,
        )
    if capsule.confidence < config.effective_adoption_min_confidence:
        return _adoption_blocked(
            CapsuleAdoptionBlockedReason.CONFIDENCE_BELOW_THRESHOLD.value,
            capsule,
            organism_id,
            graph_before,
            memory_before,
        )
    source_status = _source_fitness_status(capsule.source_fitness_status)
    if source_status is SourceFitnessStatus.UNAVAILABLE and config.min_source_fitness > 0:
        return _adoption_blocked(
            CapsuleAdoptionBlockedReason.SOURCE_FITNESS_UNAVAILABLE.value,
            capsule,
            organism_id,
            graph_before,
            memory_before,
        )
    if (
        source_status is SourceFitnessStatus.PROVISIONAL
        and config.min_source_fitness > 0
        and not config.accept_provisional_source_fitness
    ):
        return _adoption_blocked(
            CapsuleAdoptionBlockedReason.SOURCE_FITNESS_PROVISIONAL_NOT_ACCEPTED.value,
            capsule,
            organism_id,
            graph_before,
            memory_before,
        )
    threshold_fitness = capsule.source_fitness_numeric_for_threshold
    if threshold_fitness is None and config.min_source_fitness > 0:
        return _adoption_blocked(
            CapsuleAdoptionBlockedReason.SOURCE_FITNESS_UNAVAILABLE.value,
            capsule,
            organism_id,
            graph_before,
            memory_before,
        )
    if threshold_fitness is not None and threshold_fitness < config.min_source_fitness:
        return _adoption_blocked(
            CapsuleAdoptionBlockedReason.SOURCE_FITNESS_BELOW_THRESHOLD.value,
            capsule,
            organism_id,
            graph_before,
            memory_before,
        )
    adoption_cost = config.effective_adoption_cost_learning_atp
    if not atp_state.can_learn(adoption_cost):
        return _adoption_blocked(
            CapsuleAdoptionBlockedReason.INSUFFICIENT_LEARNING_ATP.value,
            capsule,
            organism_id,
            graph_before,
            memory_before,
        )
    ledger_id = atp_state.debit_learning(
        adoption_cost,
        tick=tick,
        organism_id=organism_id,
        reason="capsule_adoption_learning_cost",
        event_ref=capsule.digest(),
    )
    node_id = f"capsule:{capsule.capsule_id}"
    outcome_id = f"outcome:{capsule.predicted_outcome}"
    adopted_edges = 0
    rejected_edges = 0
    if graph.add_node(
        CausalNode(node_id, "memory", "capsule evidence", {"source_capsule_id": capsule.capsule_id})
    ):
        graph.add_node(CausalNode(outcome_id, "outcome", capsule.predicted_outcome))
        if graph.add_or_update_edge(
            node_id,
            outcome_id,
            "predicts_local",
            tick=tick,
            evidence_ref=capsule.digest(),
            metadata={
                "source_graph_digest": capsule.source_graph_digest,
                "adopted_by": organism_id,
            },
        ):
            adopted_edges += 1
        else:
            rejected_edges += 1
    else:
        rejected_edges += 1
    graph_after = graph.digest()
    return CapsuleAdoptionResult(
        attempted=True,
        succeeded=adopted_edges > 0,
        blocked_reason=None
        if adopted_edges > 0
        else CapsuleAdoptionBlockedReason.GRAPH_DIGEST_REJECTED.value,
        capsule_id=capsule.capsule_id,
        target_organism_id=organism_id,
        consumed_learning_atp=adoption_cost,
        learning_ledger_entry_id=ledger_id,
        graph_digest_before=graph_before,
        graph_digest_after=graph_after,
        memory_digest_before=memory_before,
        memory_digest_after=None if memory is None else memory.digest(),
        adopted_edges=adopted_edges,
        rejected_edges=rejected_edges,
        transfer_effect_estimate=0.0,
    )


def apply_capsule_shuffle_control(
    capsules: tuple[CausalCapsule, ...],
    mode: CapsuleShuffleMode | str,
    *,
    tick: int,
    target_organism_id: str = "",
) -> tuple[tuple[CausalCapsule, ...], tuple[CapsuleShuffleRecord, ...]]:
    """Return actually shuffled capsules plus audit records for negative controls.

    The shuffle is deterministic and payload-level: downstream adoption sees the
    shuffled capsule objects rather than a post-hoc score adjustment.  OFF returns
    the original tuple and no records. RANDOM_METADATA is intentionally marked
    claim-ineligible because it does not disrupt source/content/timing signal.
    """

    resolved = _capsule_shuffle_mode(mode)
    if resolved is CapsuleShuffleMode.OFF or not capsules:
        return capsules, ()
    ordered = tuple(sorted(capsules, key=lambda capsule: capsule.digest()))
    shuffled: list[CausalCapsule] = []
    records: list[CapsuleShuffleRecord] = []
    for index, capsule in enumerate(ordered):
        control_peer = ordered[(index + 1) % len(ordered)]
        changed = _shuffle_one_capsule(
            capsule,
            control_peer,
            resolved,
            tick=tick,
            target_organism_id=target_organism_id,
        )
        shuffled.append(changed)
        records.append(
            CapsuleShuffleRecord(
                real_capsule_digest=capsule.digest(),
                shuffled_capsule_digest=changed.digest(),
                shuffle_mode=resolved,
                source_changed=changed.source_organism_id != capsule.source_organism_id,
                content_changed=(
                    changed.event_pattern != capsule.event_pattern
                    or changed.predicted_outcome != capsule.predicted_outcome
                    or changed.source_graph_digest != capsule.source_graph_digest
                ),
                timing_changed=(
                    changed.emitted_tick != capsule.emitted_tick or changed.ttl != capsule.ttl
                ),
                claim_eligible=changed.digest() != capsule.digest()
                and resolved is not CapsuleShuffleMode.RANDOM_METADATA,
            )
        )
    return tuple(shuffled), tuple(records)


def _shuffle_one_capsule(
    capsule: CausalCapsule,
    peer: CausalCapsule,
    mode: CapsuleShuffleMode,
    *,
    tick: int,
    target_organism_id: str,
) -> CausalCapsule:
    metadata = dict(capsule.metadata)
    metadata.update(
        {
            "shuffle_control": mode.value,
            "real_capsule_digest": capsule.digest(),
            "control_peer_digest": peer.digest(),
            "target_organism_id": target_organism_id,
        }
    )
    source_organism_id = capsule.source_organism_id
    source_fitness = capsule.source_fitness
    source_fitness_status = capsule.source_fitness_status
    source_fitness_tick = capsule.source_fitness_tick
    source_graph_digest = capsule.source_graph_digest
    event_pattern = capsule.event_pattern
    predicted_outcome = capsule.predicted_outcome
    emitted_tick = capsule.emitted_tick
    ttl = capsule.ttl
    if (
        mode
        in {
            CapsuleShuffleMode.SOURCE,
            CapsuleShuffleMode.CONTENT_SOURCE_TIMING,
            CapsuleShuffleMode.RANDOM_METADATA,
        }
        and mode is not CapsuleShuffleMode.RANDOM_METADATA
    ):
        source_organism_id = peer.source_organism_id
        source_fitness = peer.source_fitness
        source_fitness_status = peer.source_fitness_status
        source_fitness_tick = peer.source_fitness_tick
        source_graph_digest = peer.source_graph_digest
    if mode in {CapsuleShuffleMode.CONTENT, CapsuleShuffleMode.CONTENT_SOURCE_TIMING}:
        event_pattern = peer.event_pattern
        predicted_outcome = peer.predicted_outcome
        source_graph_digest = peer.source_graph_digest
    if mode in {CapsuleShuffleMode.TIMING, CapsuleShuffleMode.CONTENT_SOURCE_TIMING}:
        emitted_tick = max(0, tick)
        ttl = max(0, capsule.ttl)
    return replace(
        capsule,
        capsule_id=f"{capsule.capsule_id}:shuffle:{mode.value}:{peer.digest()[:12]}",
        source_organism_id=source_organism_id,
        source_fitness=source_fitness,
        source_fitness_status=source_fitness_status,
        source_fitness_tick=source_fitness_tick,
        source_fitness_digest="",
        source_graph_digest=source_graph_digest,
        event_pattern=event_pattern,
        predicted_outcome=predicted_outcome,
        emitted_tick=emitted_tick,
        ttl=ttl,
        metadata=metadata,
    )


class CausalCapsuleAdoptionPolicy:
    """Deterministic scaffold-level capsule adoption policy.

    The store remains storage only; this policy decides whether a capsule can be
    read/adopted and delegates graph mutation to ``adopt_causal_capsule``. This
    is scaffold-level capsule adoption, not full uncertainty-reducing MDL graph
    merge.
    """

    def should_read(self, capsule: CausalCapsule, config: CapsuleTransferConfig) -> bool:
        return config.enabled and capsule.confidence >= config.effective_adoption_min_confidence

    def should_adopt(self, capsule: CausalCapsule, config: CapsuleTransferConfig) -> bool:
        return (
            self.should_read(capsule, config)
            and config.adoption_policy is not CapsuleAdoptionPolicy.NEVER
        )

    def apply(
        self,
        organism: Any,
        capsule: CausalCapsule,
        graph: CausalGraph,
        memory: EpisodicMemory | None,
        atp_state: GenesisATPState,
        config: CapsuleTransferConfig,
        *,
        tick: int,
    ) -> CapsuleAdoptionResult:
        graph_digest = graph.digest()
        memory_digest = None if memory is None else memory.digest()
        organism_id = str(getattr(organism, "id", getattr(organism, "organism_id", "organism")))
        if not config.enabled:
            return _adoption_blocked(
                "capsule_transfer_disabled", capsule, organism_id, graph_digest, memory_digest
            )
        if config.adoption_policy is CapsuleAdoptionPolicy.NEVER:
            return _adoption_blocked(
                CapsuleAdoptionBlockedReason.ADOPTION_POLICY_NEVER.value,
                capsule,
                organism_id,
                graph_digest,
                memory_digest,
            )
        if capsule.confidence < config.effective_adoption_min_confidence:
            return _adoption_blocked(
                CapsuleAdoptionBlockedReason.CONFIDENCE_BELOW_THRESHOLD.value,
                capsule,
                organism_id,
                graph_digest,
                memory_digest,
            )
        source_status = _source_fitness_status(capsule.source_fitness_status)
        if source_status is SourceFitnessStatus.UNAVAILABLE and config.min_source_fitness > 0:
            return _adoption_blocked(
                CapsuleAdoptionBlockedReason.SOURCE_FITNESS_UNAVAILABLE.value,
                capsule,
                organism_id,
                graph_digest,
                memory_digest,
            )
        if capsule.source_fitness_numeric_for_threshold is None and config.min_source_fitness > 0:
            return _adoption_blocked(
                CapsuleAdoptionBlockedReason.SOURCE_FITNESS_UNAVAILABLE.value,
                capsule,
                organism_id,
                graph_digest,
                memory_digest,
            )
        if not self.should_adopt(capsule, config):
            return _adoption_blocked(
                CapsuleAdoptionBlockedReason.ADOPTION_POLICY_REJECTED.value,
                capsule,
                organism_id,
                graph_digest,
                memory_digest,
            )
        return adopt_causal_capsule(organism, capsule, graph, memory, atp_state, config, tick=tick)


def build_capsule_adoption_record(
    *,
    capsule: CausalCapsule,
    result: CapsuleAdoptionResult,
    read_tick: int,
    adoption_attempt_tick: int,
    runtime_atp_before: float,
    learning_atp_before: float,
) -> CapsuleAdoptionRecord:
    return CapsuleAdoptionRecord(
        capsule_id=capsule.capsule_id,
        source_organism_id=capsule.source_organism_id,
        target_organism_id=result.target_organism_id,
        emitted_tick=capsule.emitted_tick,
        read_tick=read_tick,
        adoption_attempt_tick=adoption_attempt_tick,
        adoption_success=result.succeeded,
        blocked_reason=result.blocked_reason,
        source_fitness=capsule.source_fitness,
        source_fitness_status=capsule.source_fitness_status,
        source_fitness_numeric_for_threshold=capsule.source_fitness_numeric_for_threshold,
        confidence=capsule.confidence,
        runtime_atp_before=runtime_atp_before,
        learning_atp_before=learning_atp_before,
        runtime_atp_after=getattr(result, "runtime_atp_after", runtime_atp_before),
        learning_atp_after=(learning_atp_before - result.consumed_learning_atp)
        if result.succeeded
        else learning_atp_before,
    )


def estimate_capsule_transfer_effect(
    *,
    source_capsule_id: str,
    target_organism_id: str,
    pre_adoption_fitness: float | None = None,
    post_adoption_fitness: float | None = None,
    pre_behavior_digest: str | None = None,
    post_behavior_digest: str | None = None,
    pre_graph_digest: str = "",
    post_graph_digest: str = "",
    confidence: float = 0.0,
) -> CapsuleTransferMetric:
    if pre_adoption_fitness is None or post_adoption_fitness is None:
        score = 0.0
        interpretation = "insufficient_evidence"
    else:
        score = round(post_adoption_fitness - pre_adoption_fitness, 10)
        interpretation = "measured_delta_not_causal_proof"
    return CapsuleTransferMetric(
        source_capsule_id=source_capsule_id,
        target_organism_id=target_organism_id,
        pre_adoption_fitness=pre_adoption_fitness,
        post_adoption_fitness=post_adoption_fitness,
        pre_behavior_digest=pre_behavior_digest,
        post_behavior_digest=post_behavior_digest,
        pre_graph_digest=pre_graph_digest,
        post_graph_digest=post_graph_digest,
        effect_score=score,
        confidence=max(0.0, min(1.0, confidence)),
        interpretation=interpretation,
    )


def _source_fitness_status(value: SourceFitnessStatus | str) -> SourceFitnessStatus:
    if isinstance(value, SourceFitnessStatus):
        return value
    return SourceFitnessStatus(str(value))


def _capsule_policy_profile(value: CapsulePolicyProfile | str) -> CapsulePolicyProfile:
    if isinstance(value, CapsulePolicyProfile):
        return value
    return CapsulePolicyProfile(str(value))


def _capsule_shuffle_mode(value: CapsuleShuffleMode | str) -> CapsuleShuffleMode:
    if isinstance(value, CapsuleShuffleMode):
        return value
    return CapsuleShuffleMode(str(value))


def _capsule_position(capsule: CausalCapsule) -> Position | None:
    raw = capsule.metadata.get("position")
    return _position_or_none(raw)


def _manhattan(left: Position, right: Position) -> int:
    return abs(left[0] - right[0]) + abs(left[1] - right[1])


def _emission_blocked(reason: str) -> CapsuleEmissionResult:
    return CapsuleEmissionResult(True, False, reason, None, 0.0, 0.0, None, None)


def _read_blocked(reason: str, digest: str) -> CapsuleReadResult:
    return CapsuleReadResult(True, False, reason, 0, (), 0.0, None, digest, digest, ())


def _adoption_blocked(
    reason: str,
    capsule: CausalCapsule,
    organism_id: str,
    graph_digest: str,
    memory_digest: str | None,
) -> CapsuleAdoptionResult:
    return CapsuleAdoptionResult(
        attempted=True,
        succeeded=False,
        blocked_reason=reason,
        capsule_id=capsule.capsule_id,
        target_organism_id=organism_id,
        consumed_learning_atp=0.0,
        learning_ledger_entry_id=None,
        graph_digest_before=graph_digest,
        graph_digest_after=graph_digest,
        memory_digest_before=memory_digest,
        memory_digest_after=memory_digest,
        adopted_edges=0,
        rejected_edges=0,
        transfer_effect_estimate=0.0,
    )


def _capsule_confidence(graph: CausalGraph, fitness: float) -> float:
    edge_component = min(1.0, len(graph.edges) / 10.0)
    fitness_component = min(1.0, max(0.0, fitness / 10.0))
    return round(max(edge_component, fitness_component), 10)


def _stable_id(prefix: str, *parts: object) -> str:
    encoded = finite_json_dumps(parts, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(encoded).hexdigest()[:16]}"


def _digest(payload: Mapping[str, JsonValue]) -> str:
    encoded = finite_json_dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _str(data: Mapping[str, JsonValue], key: str, default: str | None = None) -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        msg = f"{key} must be a string."
        raise ConfigurationError(msg)
    return value


def _optional_str(data: Mapping[str, JsonValue], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        msg = f"{key} must be a string or null."
        raise ConfigurationError(msg)
    return value


def _bool(data: Mapping[str, JsonValue], key: str, default: bool) -> bool:
    value = data.get(key, default)
    if not isinstance(value, bool):
        msg = f"{key} must be a boolean."
        raise ConfigurationError(msg)
    return value


def _int(data: Mapping[str, JsonValue], key: str, default: int) -> int:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{key} must be an integer."
        raise ConfigurationError(msg)
    return value


def _optional_int(data: Mapping[str, JsonValue], key: str) -> int | None:
    value = data.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{key} must be an integer or null."
        raise ConfigurationError(msg)
    return value


def _float(data: Mapping[str, JsonValue], key: str, default: float) -> float:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int | float):
        msg = f"{key} must be numeric."
        raise ConfigurationError(msg)
    return finite_float(key, value)  # type: ignore[return-value]


def _optional_float(data: Mapping[str, JsonValue], key: str) -> float | None:
    value = data.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        msg = f"{key} must be numeric or null."
        raise ConfigurationError(msg)
    return finite_float(key, value)  # type: ignore[return-value]


def _str_tuple(data: Mapping[str, JsonValue], key: str) -> tuple[str, ...]:
    raw = data.get(key, [])
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        msg = f"{key} must be a list of strings."
        raise ConfigurationError(msg)
    return tuple(str(item) for item in raw)


def _position_or_none(value: JsonValue | None) -> Position | None:
    if value is None:
        return None
    if (
        isinstance(value, list)
        and len(value) == 2
        and all(isinstance(part, int) and not isinstance(part, bool) for part in value)
    ):
        return (cast(int, value[0]), cast(int, value[1]))
    msg = "position must be [x, y] or null."
    raise ConfigurationError(msg)
