"""Domain-free life-loop event schemas and digests.

Frozen serializable contracts for modular platform primitives
(multi-population registry, attachment slot, energy coupling,
contact transfer, inherit-attached, ablation template, schedule lock,
and life-hook names). No tick physics and no discipline vocabulary.

Digests use ``canonical_digest``. Reload refuses digest mismatch.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import (
    canonical_digest,
    is_real_evidence_digest,
    require_finite_float,
    require_real_evidence_digest,
)

SCHEMA_VERSION = "life_loop_events_v1"

EVENT_TYPES: frozenset[str] = frozenset(
    {
        "population_registry",
        "attachment",
        "energy_coupling",
        "contact",
        "birth_attach",
        "ablation_arm",
        "schedule_lock",
    }
)

HOOK_NAMES: frozenset[str] = frozenset(
    {"on_birth", "on_death", "on_contact", "on_resource"}
)


def _as_str(value: object, name: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ConfigurationError(f"{name} must be a string.")
    text = value.strip()
    if not text and not allow_empty:
        raise ConfigurationError(f"{name} must be a non-empty string.")
    return text


def _as_int(value: object, name: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{name} must be an integer.")
    if minimum is not None and value < minimum:
        raise ConfigurationError(f"{name} must be >= {minimum}.")
    return value


def _as_bool(value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigurationError(f"{name} must be a bool.")
    return value


def _optional_str(value: object, name: str) -> str | None:
    if value is None:
        return None
    return _as_str(value, name)


def _optional_digest(value: object, name: str) -> str | None:
    if value is None:
        return None
    return require_real_evidence_digest(name, value)


def _payload_digest(payload: Mapping[str, Any], *, prefix: str) -> str:
    return canonical_digest(dict(payload), prefix=prefix)


def _check_digest(existing: str, computed: str, label: str) -> str:
    if existing and existing != computed:
        raise ConfigurationError(f"{label} digest mismatch.")
    return computed


@dataclass(frozen=True, slots=True)
class PopulationRegistryEvent:
    """Census / membership change for a named population."""

    population_id: str
    individual_id: str
    action: str
    tick: int
    count_after: int
    digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "population_id", _as_str(self.population_id, "population_id"))
        object.__setattr__(self, "individual_id", _as_str(self.individual_id, "individual_id"))
        object.__setattr__(self, "action", _as_str(self.action, "action"))
        object.__setattr__(self, "tick", _as_int(self.tick, "tick", minimum=0))
        object.__setattr__(self, "count_after", _as_int(self.count_after, "count_after", minimum=0))
        computed = _payload_digest(self._body(), prefix="popreg")
        object.__setattr__(self, "digest", _check_digest(self.digest, computed, "PopulationRegistryEvent"))

    def _body(self) -> dict[str, JsonValue]:
        return {
            "event_type": "population_registry",
            "population_id": self.population_id,
            "individual_id": self.individual_id,
            "action": self.action,
            "tick": self.tick,
            "count_after": self.count_after,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> PopulationRegistryEvent:
        return cls(
            population_id=_as_str(data.get("population_id"), "population_id"),
            individual_id=_as_str(data.get("individual_id"), "individual_id"),
            action=_as_str(data.get("action"), "action"),
            tick=_as_int(data.get("tick"), "tick", minimum=0),
            count_after=_as_int(data.get("count_after"), "count_after", minimum=0),
            digest=_as_str(data.get("digest", ""), "digest", allow_empty=True),
        )


@dataclass(frozen=True, slots=True)
class AttachmentEvent:
    """Individual–individual occupancy seat change."""

    slot_id: str
    owner_id: str
    occupant_id: str | None
    capacity: int
    tick: int
    digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "slot_id", _as_str(self.slot_id, "slot_id"))
        object.__setattr__(self, "owner_id", _as_str(self.owner_id, "owner_id"))
        object.__setattr__(self, "occupant_id", _optional_str(self.occupant_id, "occupant_id"))
        object.__setattr__(self, "capacity", _as_int(self.capacity, "capacity", minimum=1))
        object.__setattr__(self, "tick", _as_int(self.tick, "tick", minimum=0))
        computed = _payload_digest(self._body(), prefix="attach")
        object.__setattr__(self, "digest", _check_digest(self.digest, computed, "AttachmentEvent"))

    def _body(self) -> dict[str, JsonValue]:
        return {
            "event_type": "attachment",
            "slot_id": self.slot_id,
            "owner_id": self.owner_id,
            "occupant_id": self.occupant_id,
            "capacity": self.capacity,
            "tick": self.tick,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> AttachmentEvent:
        return cls(
            slot_id=_as_str(data.get("slot_id"), "slot_id"),
            owner_id=_as_str(data.get("owner_id"), "owner_id"),
            occupant_id=_optional_str(data.get("occupant_id"), "occupant_id"),
            capacity=_as_int(data.get("capacity"), "capacity", minimum=1),
            tick=_as_int(data.get("tick"), "tick", minimum=0),
            digest=_as_str(data.get("digest", ""), "digest", allow_empty=True),
        )


@dataclass(frozen=True, slots=True)
class EnergyCouplingEvent:
    """Per-tick signed energy transfer between two individuals."""

    source_id: str
    target_id: str
    delta_energy: float
    tick: int
    coupling_id: str
    digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_id", _as_str(self.source_id, "source_id"))
        object.__setattr__(self, "target_id", _as_str(self.target_id, "target_id"))
        object.__setattr__(
            self, "delta_energy", require_finite_float("delta_energy", self.delta_energy)
        )
        object.__setattr__(self, "tick", _as_int(self.tick, "tick", minimum=0))
        object.__setattr__(self, "coupling_id", _as_str(self.coupling_id, "coupling_id"))
        computed = _payload_digest(self._body(), prefix="ecouple")
        object.__setattr__(self, "digest", _check_digest(self.digest, computed, "EnergyCouplingEvent"))

    def _body(self) -> dict[str, JsonValue]:
        return {
            "event_type": "energy_coupling",
            "source_id": self.source_id,
            "target_id": self.target_id,
            "delta_energy": self.delta_energy,
            "tick": self.tick,
            "coupling_id": self.coupling_id,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> EnergyCouplingEvent:
        return cls(
            source_id=_as_str(data.get("source_id"), "source_id"),
            target_id=_as_str(data.get("target_id"), "target_id"),
            delta_energy=require_finite_float("delta_energy", data.get("delta_energy")),
            tick=_as_int(data.get("tick"), "tick", minimum=0),
            coupling_id=_as_str(data.get("coupling_id"), "coupling_id"),
            digest=_as_str(data.get("digest", ""), "digest", allow_empty=True),
        )


@dataclass(frozen=True, slots=True)
class ContactEvent:
    """Contact between two individuals (contact-transfer surface)."""

    actor_id: str
    other_id: str
    tick: int
    rule_id: str
    score: float | None
    transfer_mode: str
    digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "actor_id", _as_str(self.actor_id, "actor_id"))
        object.__setattr__(self, "other_id", _as_str(self.other_id, "other_id"))
        object.__setattr__(self, "tick", _as_int(self.tick, "tick", minimum=0))
        object.__setattr__(self, "rule_id", _as_str(self.rule_id, "rule_id"))
        score = self.score
        if score is not None:
            score = require_finite_float("score", score)
        object.__setattr__(self, "score", score)
        object.__setattr__(self, "transfer_mode", _as_str(self.transfer_mode, "transfer_mode"))
        computed = _payload_digest(self._body(), prefix="contact")
        object.__setattr__(self, "digest", _check_digest(self.digest, computed, "ContactEvent"))

    def _body(self) -> dict[str, JsonValue]:
        return {
            "event_type": "contact",
            "actor_id": self.actor_id,
            "other_id": self.other_id,
            "tick": self.tick,
            "rule_id": self.rule_id,
            "score": self.score,
            "transfer_mode": self.transfer_mode,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ContactEvent:
        raw_score = data.get("score")
        score = None if raw_score is None else require_finite_float("score", raw_score)
        return cls(
            actor_id=_as_str(data.get("actor_id"), "actor_id"),
            other_id=_as_str(data.get("other_id"), "other_id"),
            tick=_as_int(data.get("tick"), "tick", minimum=0),
            rule_id=_as_str(data.get("rule_id"), "rule_id"),
            score=score,
            transfer_mode=_as_str(data.get("transfer_mode"), "transfer_mode"),
            digest=_as_str(data.get("digest", ""), "digest", allow_empty=True),
        )


@dataclass(frozen=True, slots=True)
class BirthAttachEvent:
    """Birth-time optional inheritance of attached occupants."""

    parent_id: str
    offspring_id: str
    slot_id: str
    inherited_occupant_id: str | None
    tick: int
    digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "parent_id", _as_str(self.parent_id, "parent_id"))
        object.__setattr__(self, "offspring_id", _as_str(self.offspring_id, "offspring_id"))
        object.__setattr__(self, "slot_id", _as_str(self.slot_id, "slot_id"))
        object.__setattr__(
            self,
            "inherited_occupant_id",
            _optional_str(self.inherited_occupant_id, "inherited_occupant_id"),
        )
        object.__setattr__(self, "tick", _as_int(self.tick, "tick", minimum=0))
        computed = _payload_digest(self._body(), prefix="birthattach")
        object.__setattr__(self, "digest", _check_digest(self.digest, computed, "BirthAttachEvent"))

    def _body(self) -> dict[str, JsonValue]:
        return {
            "event_type": "birth_attach",
            "parent_id": self.parent_id,
            "offspring_id": self.offspring_id,
            "slot_id": self.slot_id,
            "inherited_occupant_id": self.inherited_occupant_id,
            "tick": self.tick,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> BirthAttachEvent:
        return cls(
            parent_id=_as_str(data.get("parent_id"), "parent_id"),
            offspring_id=_as_str(data.get("offspring_id"), "offspring_id"),
            slot_id=_as_str(data.get("slot_id"), "slot_id"),
            inherited_occupant_id=_optional_str(
                data.get("inherited_occupant_id"), "inherited_occupant_id"
            ),
            tick=_as_int(data.get("tick"), "tick", minimum=0),
            digest=_as_str(data.get("digest", ""), "digest", allow_empty=True),
        )


@dataclass(frozen=True, slots=True)
class AblationArmEvent:
    """Ablation arm declaration (content vs structure axes)."""

    arm_id: str
    content_null: bool
    structure_null: bool
    tick: int
    digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "arm_id", _as_str(self.arm_id, "arm_id"))
        object.__setattr__(self, "content_null", _as_bool(self.content_null, "content_null"))
        object.__setattr__(self, "structure_null", _as_bool(self.structure_null, "structure_null"))
        object.__setattr__(self, "tick", _as_int(self.tick, "tick", minimum=0))
        computed = _payload_digest(self._body(), prefix="ablation")
        object.__setattr__(self, "digest", _check_digest(self.digest, computed, "AblationArmEvent"))

    def _body(self) -> dict[str, JsonValue]:
        return {
            "event_type": "ablation_arm",
            "arm_id": self.arm_id,
            "content_null": self.content_null,
            "structure_null": self.structure_null,
            "tick": self.tick,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> AblationArmEvent:
        return cls(
            arm_id=_as_str(data.get("arm_id"), "arm_id"),
            content_null=_as_bool(data.get("content_null"), "content_null"),
            structure_null=_as_bool(data.get("structure_null"), "structure_null"),
            tick=_as_int(data.get("tick"), "tick", minimum=0),
            digest=_as_str(data.get("digest", ""), "digest", allow_empty=True),
        )


@dataclass(frozen=True, slots=True)
class ScheduleLockEvent:
    """Freeze / replay / lock arm on a subpopulation id."""

    population_id: str
    lock_mode: str
    tick: int
    schedule_id: str
    digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "population_id", _as_str(self.population_id, "population_id"))
        object.__setattr__(self, "lock_mode", _as_str(self.lock_mode, "lock_mode"))
        object.__setattr__(self, "tick", _as_int(self.tick, "tick", minimum=0))
        object.__setattr__(self, "schedule_id", _as_str(self.schedule_id, "schedule_id"))
        computed = _payload_digest(self._body(), prefix="schedlock")
        object.__setattr__(self, "digest", _check_digest(self.digest, computed, "ScheduleLockEvent"))

    def _body(self) -> dict[str, JsonValue]:
        return {
            "event_type": "schedule_lock",
            "population_id": self.population_id,
            "lock_mode": self.lock_mode,
            "tick": self.tick,
            "schedule_id": self.schedule_id,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ScheduleLockEvent:
        return cls(
            population_id=_as_str(data.get("population_id"), "population_id"),
            lock_mode=_as_str(data.get("lock_mode"), "lock_mode"),
            tick=_as_int(data.get("tick"), "tick", minimum=0),
            schedule_id=_as_str(data.get("schedule_id"), "schedule_id"),
            digest=_as_str(data.get("digest", ""), "digest", allow_empty=True),
        )


LifeLoopEvent = (
    PopulationRegistryEvent
    | AttachmentEvent
    | EnergyCouplingEvent
    | ContactEvent
    | BirthAttachEvent
    | AblationArmEvent
    | ScheduleLockEvent
)

_EVENT_LOADERS = {
    "population_registry": PopulationRegistryEvent.from_dict,
    "attachment": AttachmentEvent.from_dict,
    "energy_coupling": EnergyCouplingEvent.from_dict,
    "contact": ContactEvent.from_dict,
    "birth_attach": BirthAttachEvent.from_dict,
    "ablation_arm": AblationArmEvent.from_dict,
    "schedule_lock": ScheduleLockEvent.from_dict,
}


@dataclass(frozen=True, slots=True)
class LifeLoopEventEnvelope:
    """Versioned envelope for life-loop events."""

    schema_version: str
    event_type: str
    event_id: str
    payload: Mapping[str, JsonValue]
    parent_digest: str | None = None
    digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _as_str(self.schema_version, "schema_version"))
        et = _as_str(self.event_type, "event_type")
        if et not in EVENT_TYPES:
            raise ConfigurationError(f"Unknown event_type: {et}")
        object.__setattr__(self, "event_type", et)
        eid = _as_str(self.event_id, "event_id")
        if not is_real_evidence_digest(eid):
            raise ConfigurationError("event_id must be a real evidence digest.")
        object.__setattr__(self, "event_id", eid)
        if not isinstance(self.payload, Mapping):
            raise ConfigurationError("payload must be a mapping.")
        object.__setattr__(self, "payload", dict(self.payload))
        object.__setattr__(
            self, "parent_digest", _optional_digest(self.parent_digest, "parent_digest")
        )
        computed = _payload_digest(self._body(), prefix="lle")
        object.__setattr__(
            self, "digest", _check_digest(self.digest, computed, "LifeLoopEventEnvelope")
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "event_type": self.event_type,
            "event_id": self.event_id,
            "payload": dict(self.payload),
            "parent_digest": self.parent_digest,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> LifeLoopEventEnvelope:
        raw_payload = data.get("payload")
        if not isinstance(raw_payload, Mapping):
            raise ConfigurationError("payload must be a mapping.")
        return cls(
            schema_version=_as_str(data.get("schema_version"), "schema_version"),
            event_type=_as_str(data.get("event_type"), "event_type"),
            event_id=_as_str(data.get("event_id"), "event_id"),
            payload=raw_payload,
            parent_digest=_optional_digest(data.get("parent_digest"), "parent_digest"),
            digest=_as_str(data.get("digest", ""), "digest", allow_empty=True),
        )

    @classmethod
    def wrap(
        cls,
        event: LifeLoopEvent,
        *,
        event_id: str,
        parent_digest: str | None = None,
        schema_version: str = SCHEMA_VERSION,
    ) -> LifeLoopEventEnvelope:
        body = event.to_dict()
        return cls(
            schema_version=schema_version,
            event_type=str(body["event_type"]),
            event_id=event_id,
            payload=body,
            parent_digest=parent_digest,
        )


def load_event(data: Mapping[str, Any]) -> LifeLoopEvent:
    """Load a typed life-loop event from a mapping using ``event_type``."""

    et = _as_str(data.get("event_type"), "event_type")
    loader = _EVENT_LOADERS.get(et)
    if loader is None:
        raise ConfigurationError(f"Unknown event_type: {et}")
    return loader(data)  # type: ignore[no-any-return]
