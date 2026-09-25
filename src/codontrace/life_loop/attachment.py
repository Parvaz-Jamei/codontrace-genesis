"""Domain-free agent–agent attachment seats for the life-loop.

Occupancy is individual–individual (not WorldObject cells). Emits
``AttachmentEvent`` from Phase 1 contracts. No discipline vocabulary.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

from codontrace._types import JsonValue
from codontrace.contracts.banned import BANNED_DOMAIN_TOKENS
from codontrace.contracts.life_loop_events import AttachmentEvent
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest

SCHEMA_VERSION = "life_loop_attachment_v1"

AttachFailReason = Literal[
    "seat_full",
    "already_occupant",
    "self_attach",
    "not_occupant",
    "unknown_slot",
    "banned_fragment",
]

ATTACH_FAIL_REASONS: frozenset[str] = frozenset(
    {
        "seat_full",
        "already_occupant",
        "self_attach",
        "not_occupant",
        "unknown_slot",
        "banned_fragment",
    }
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


def _optional_str(value: object, name: str) -> str | None:
    if value is None:
        return None
    return _as_str(value, name)


def _refuse_banned_fragment(text: str, name: str) -> str:
    lowered = text.casefold()
    for token in BANNED_DOMAIN_TOKENS:
        if token.casefold() in lowered:
            raise ConfigurationError(f"{name} contains a banned fragment.")
    return text


def _canonical_occupants(occupant_ids: Iterable[str]) -> tuple[str, ...]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in occupant_ids:
        oid = _refuse_banned_fragment(_as_str(raw, "occupant_id"), "occupant_id")
        if oid in seen:
            raise ConfigurationError(f"duplicate occupant_id {oid!r} in slot.")
        seen.add(oid)
        cleaned.append(oid)
    return tuple(sorted(cleaned))


def _check_digest(existing: str, computed: str, label: str) -> str:
    if existing and existing != computed:
        raise ConfigurationError(f"{label} digest mismatch.")
    return computed


@dataclass(frozen=True, slots=True)
class AttachmentSlot:
    """Immutable agent–agent occupancy seat (capacity ≥ 1)."""

    slot_id: str
    owner_id: str
    capacity: int = 1
    occupant_ids: tuple[str, ...] = ()
    label: str | None = None
    tick: int = 0
    digest: str = ""

    def __post_init__(self) -> None:
        sid = _refuse_banned_fragment(_as_str(self.slot_id, "slot_id"), "slot_id")
        oid = _refuse_banned_fragment(_as_str(self.owner_id, "owner_id"), "owner_id")
        object.__setattr__(self, "slot_id", sid)
        object.__setattr__(self, "owner_id", oid)
        capacity = _as_int(self.capacity, "capacity", minimum=1)
        object.__setattr__(self, "capacity", capacity)
        occupants = _canonical_occupants(self.occupant_ids)
        if len(occupants) > capacity:
            raise ConfigurationError("occupant_ids exceed capacity.")
        if oid in occupants:
            raise ConfigurationError("owner cannot occupy own seat.")
        object.__setattr__(self, "occupant_ids", occupants)
        label = _optional_str(self.label, "label")
        if label is not None:
            label = _refuse_banned_fragment(label, "label")
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "tick", _as_int(self.tick, "tick", minimum=0))
        computed = canonical_digest(self._body(), prefix="attachslot")
        object.__setattr__(
            self, "digest", _check_digest(self.digest, computed, "AttachmentSlot")
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "schema_version": SCHEMA_VERSION,
            "slot_id": self.slot_id,
            "owner_id": self.owner_id,
            "capacity": self.capacity,
            "occupant_ids": list(self.occupant_ids),
            "label": self.label,
            "tick": self.tick,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> AttachmentSlot:
        occ_raw = data.get("occupant_ids", ())
        if not isinstance(occ_raw, (list, tuple)):
            raise ConfigurationError("occupant_ids must be a list or tuple.")
        return cls(
            slot_id=_as_str(data.get("slot_id"), "slot_id"),
            owner_id=_as_str(data.get("owner_id"), "owner_id"),
            capacity=_as_int(data.get("capacity", 1), "capacity", minimum=1),
            occupant_ids=tuple(str(item) for item in occ_raw),
            label=_optional_str(data.get("label"), "label"),
            tick=_as_int(data.get("tick", 0), "tick", minimum=0),
            digest=_as_str(data.get("digest", ""), "digest", allow_empty=True),
        )

    @property
    def free_capacity(self) -> int:
        return self.capacity - len(self.occupant_ids)

    @property
    def is_full(self) -> bool:
        return len(self.occupant_ids) >= self.capacity

    def has_occupant(self, individual_id: str) -> bool:
        return _as_str(individual_id, "individual_id") in self.occupant_ids

    def linked(self, a: str, b: str) -> bool:
        """True if one id is owner and the other is an occupant."""

        left = _as_str(a, "a")
        right = _as_str(b, "b")
        if left == self.owner_id and right in self.occupant_ids:
            return True
        if right == self.owner_id and left in self.occupant_ids:
            return True
        return False

    def _event(self, occupant_id: str | None) -> AttachmentEvent:
        return AttachmentEvent(
            slot_id=self.slot_id,
            owner_id=self.owner_id,
            occupant_id=occupant_id,
            capacity=self.capacity,
            tick=self.tick,
        )

    def attach(self, occupant_id: str) -> tuple[AttachmentSlot, AttachmentEvent]:
        oid = _refuse_banned_fragment(
            _as_str(occupant_id, "occupant_id"), "occupant_id"
        )
        if oid == self.owner_id:
            raise ConfigurationError("self_attach")
        if oid in self.occupant_ids:
            raise ConfigurationError("already_occupant")
        if self.is_full:
            raise ConfigurationError("seat_full")
        updated = AttachmentSlot(
            slot_id=self.slot_id,
            owner_id=self.owner_id,
            capacity=self.capacity,
            occupant_ids=self.occupant_ids + (oid,),
            label=self.label,
            tick=self.tick,
        )
        return updated, updated._event(oid)

    def detach(self, occupant_id: str) -> tuple[AttachmentSlot, AttachmentEvent]:
        oid = _as_str(occupant_id, "occupant_id")
        if oid not in self.occupant_ids:
            raise ConfigurationError("not_occupant")
        updated = AttachmentSlot(
            slot_id=self.slot_id,
            owner_id=self.owner_id,
            capacity=self.capacity,
            occupant_ids=tuple(x for x in self.occupant_ids if x != oid),
            label=self.label,
            tick=self.tick,
        )
        return updated, updated._event(oid)

    def advance_tick(self, tick: int) -> AttachmentSlot:
        new_tick = _as_int(tick, "tick", minimum=0)
        if new_tick < self.tick:
            raise ConfigurationError("tick must not decrease.")
        return AttachmentSlot(
            slot_id=self.slot_id,
            owner_id=self.owner_id,
            capacity=self.capacity,
            occupant_ids=self.occupant_ids,
            label=self.label,
            tick=new_tick,
        )


@dataclass(frozen=True, slots=True)
class AttachmentBook:
    """Immutable collection of attachment slots (domain-free)."""

    tick: int = 0
    slots: tuple[AttachmentSlot, ...] = ()
    digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "tick", _as_int(self.tick, "tick", minimum=0))
        records = tuple(self.slots)
        ids = [s.slot_id for s in records]
        if len(ids) != len(set(ids)):
            raise ConfigurationError("slot ids must be unique.")
        ordered = tuple(sorted(records, key=lambda s: s.slot_id))
        # Normalize nested ticks to book tick for digest stability of collection.
        normalized: list[AttachmentSlot] = []
        for slot in ordered:
            if slot.tick != self.tick:
                slot = AttachmentSlot(
                    slot_id=slot.slot_id,
                    owner_id=slot.owner_id,
                    capacity=slot.capacity,
                    occupant_ids=slot.occupant_ids,
                    label=slot.label,
                    tick=self.tick,
                    digest="",
                )
            normalized.append(slot)
        object.__setattr__(self, "slots", tuple(normalized))
        computed = canonical_digest(self._body(), prefix="attachbook")
        object.__setattr__(
            self, "digest", _check_digest(self.digest, computed, "AttachmentBook")
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "schema_version": SCHEMA_VERSION,
            "tick": self.tick,
            "slots": [s._body() for s in self.slots],
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": SCHEMA_VERSION,
            "tick": self.tick,
            "slots": [s.to_dict() for s in self.slots],
            "digest": self.digest,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> AttachmentBook:
        raw = data.get("slots", ())
        if not isinstance(raw, (list, tuple)):
            raise ConfigurationError("slots must be a list or tuple.")
        slots = tuple(
            AttachmentSlot.from_dict(item) for item in raw if isinstance(item, Mapping)
        )
        if len(slots) != len(raw):
            raise ConfigurationError("slots entries must be mappings.")
        return cls(
            tick=_as_int(data.get("tick", 0), "tick", minimum=0),
            slots=slots,
            digest=_as_str(data.get("digest", ""), "digest", allow_empty=True),
        )

    def list_slot_ids(self) -> tuple[str, ...]:
        return tuple(s.slot_id for s in self.slots)

    def _index(self, slot_id: str) -> int:
        sid = _as_str(slot_id, "slot_id")
        for i, slot in enumerate(self.slots):
            if slot.slot_id == sid:
                return i
        raise ConfigurationError("unknown_slot")

    def get(self, slot_id: str) -> AttachmentSlot:
        return self.slots[self._index(slot_id)]

    def add_slot(self, slot: AttachmentSlot) -> AttachmentBook:
        if not isinstance(slot, AttachmentSlot):
            raise ConfigurationError("slot must be an AttachmentSlot.")
        if slot.slot_id in self.list_slot_ids():
            raise ConfigurationError(f"slot_id {slot.slot_id!r} already exists.")
        synced = AttachmentSlot(
            slot_id=slot.slot_id,
            owner_id=slot.owner_id,
            capacity=slot.capacity,
            occupant_ids=slot.occupant_ids,
            label=slot.label,
            tick=self.tick,
        )
        return AttachmentBook(tick=self.tick, slots=self.slots + (synced,))

    def attach(
        self, slot_id: str, occupant_id: str
    ) -> tuple[AttachmentBook, AttachmentEvent]:
        idx = self._index(slot_id)
        updated_slot, event = self.slots[idx].attach(occupant_id)
        slots = list(self.slots)
        slots[idx] = updated_slot
        return AttachmentBook(tick=self.tick, slots=tuple(slots)), event

    def detach(
        self, slot_id: str, occupant_id: str
    ) -> tuple[AttachmentBook, AttachmentEvent]:
        idx = self._index(slot_id)
        updated_slot, event = self.slots[idx].detach(occupant_id)
        slots = list(self.slots)
        slots[idx] = updated_slot
        return AttachmentBook(tick=self.tick, slots=tuple(slots)), event

    def any_link(self, a: str, b: str) -> bool:
        return any(slot.linked(a, b) for slot in self.slots)

    def advance_tick(self, tick: int) -> AttachmentBook:
        new_tick = _as_int(tick, "tick", minimum=0)
        if new_tick < self.tick:
            raise ConfigurationError("tick must not decrease.")
        return AttachmentBook(tick=new_tick, slots=self.slots)


__all__ = [
    "ATTACH_FAIL_REASONS",
    "SCHEMA_VERSION",
    "AttachFailReason",
    "AttachmentBook",
    "AttachmentSlot",
]
