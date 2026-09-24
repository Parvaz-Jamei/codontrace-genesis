"""Domain-free multi-population registry for the life-loop.

Named populations coexist as digest-stable membership snapshots on the
existing Simulation / PopulationState spine. No organism tick physics and
no discipline vocabulary. Emits ``PopulationRegistryEvent`` from Phase 1
contracts. Optional ``schedule_partition`` is an opaque tag for later
schedule lock wiring — not a scheduler.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from codontrace._types import JsonValue
from codontrace.contracts.banned import BANNED_DOMAIN_TOKENS
from codontrace.contracts.life_loop_events import PopulationRegistryEvent
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest

SCHEMA_VERSION = "life_loop_populations_v1"

_MEMBER_ACTIONS = frozenset({"add", "remove", "create", "census"})


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
    """Refuse ids/tags that embed banned domain fragments (case-insensitive)."""

    lowered = text.casefold()
    for token in BANNED_DOMAIN_TOKENS:
        if token.casefold() in lowered:
            raise ConfigurationError(f"{name} contains a banned fragment.")
    return text


def _canonical_members(member_ids: Iterable[str]) -> tuple[str, ...]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in member_ids:
        mid = _as_str(raw, "member_id")
        _refuse_banned_fragment(mid, "member_id")
        if mid in seen:
            raise ConfigurationError(f"duplicate member_id {mid!r} in population.")
        seen.add(mid)
        cleaned.append(mid)
    return tuple(sorted(cleaned))


def _check_digest(existing: str, computed: str, label: str) -> str:
    if existing and existing != computed:
        raise ConfigurationError(f"{label} digest mismatch.")
    return computed


@dataclass(frozen=True, slots=True)
class PopulationRecord:
    """One named population: sorted membership + optional schedule partition tag."""

    population_id: str
    member_ids: tuple[str, ...] = ()
    schedule_partition: str | None = None
    digest: str = ""

    def __post_init__(self) -> None:
        pid = _refuse_banned_fragment(
            _as_str(self.population_id, "population_id"), "population_id"
        )
        object.__setattr__(self, "population_id", pid)
        members = _canonical_members(self.member_ids)
        object.__setattr__(self, "member_ids", members)
        part = _optional_str(self.schedule_partition, "schedule_partition")
        if part is not None:
            part = _refuse_banned_fragment(part, "schedule_partition")
        object.__setattr__(self, "schedule_partition", part)
        computed = canonical_digest(self._body(), prefix="poprec")
        object.__setattr__(
            self, "digest", _check_digest(self.digest, computed, "PopulationRecord")
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "population_id": self.population_id,
            "member_ids": list(self.member_ids),
            "schedule_partition": self.schedule_partition,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> PopulationRecord:
        members_raw = data.get("member_ids", ())
        if not isinstance(members_raw, (list, tuple)):
            raise ConfigurationError("member_ids must be a list or tuple.")
        return cls(
            population_id=_as_str(data.get("population_id"), "population_id"),
            member_ids=tuple(str(item) for item in members_raw),
            schedule_partition=_optional_str(
                data.get("schedule_partition"), "schedule_partition"
            ),
            digest=_as_str(data.get("digest", ""), "digest", allow_empty=True),
        )

    @property
    def census(self) -> int:
        return len(self.member_ids)

    @property
    def is_empty(self) -> bool:
        return len(self.member_ids) == 0


@dataclass(frozen=True, slots=True)
class PopulationRegistry:
    """Immutable multi-population membership registry (domain-free).

    Advances only a tick / membership snapshot. Does not execute organisms
    and must not be treated as a second world ``step()`` loop.
    """

    tick: int = 0
    populations: tuple[PopulationRecord, ...] = ()
    digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "tick", _as_int(self.tick, "tick", minimum=0))
        records = tuple(self.populations)
        ids = [rec.population_id for rec in records]
        if len(ids) != len(set(ids)):
            raise ConfigurationError("population ids must be unique.")
        # Individual belongs to at most one population.
        owner: dict[str, str] = {}
        for rec in records:
            for mid in rec.member_ids:
                if mid in owner:
                    raise ConfigurationError(
                        f"individual {mid!r} already in population {owner[mid]!r}."
                    )
                owner[mid] = rec.population_id
        ordered = tuple(sorted(records, key=lambda r: r.population_id))
        object.__setattr__(self, "populations", ordered)
        computed = canonical_digest(self._body(), prefix="popregsnap")
        object.__setattr__(
            self, "digest", _check_digest(self.digest, computed, "PopulationRegistry")
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "schema_version": SCHEMA_VERSION,
            "tick": self.tick,
            "populations": [rec._body() for rec in self.populations],
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": SCHEMA_VERSION,
            "tick": self.tick,
            "populations": [rec.to_dict() for rec in self.populations],
            "digest": self.digest,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> PopulationRegistry:
        pops_raw = data.get("populations", ())
        if not isinstance(pops_raw, (list, tuple)):
            raise ConfigurationError("populations must be a list or tuple.")
        records = tuple(
            PopulationRecord.from_dict(item)
            for item in pops_raw
            if isinstance(item, Mapping)
        )
        if len(records) != len(pops_raw):
            raise ConfigurationError("populations entries must be mappings.")
        return cls(
            tick=_as_int(data.get("tick", 0), "tick", minimum=0),
            populations=records,
            digest=_as_str(data.get("digest", ""), "digest", allow_empty=True),
        )

    def list_population_ids(self) -> tuple[str, ...]:
        return tuple(rec.population_id for rec in self.populations)

    def _index(self, population_id: str) -> int:
        pid = _as_str(population_id, "population_id")
        for i, rec in enumerate(self.populations):
            if rec.population_id == pid:
                return i
        raise ConfigurationError(f"unknown population_id {pid!r}.")

    def get(self, population_id: str) -> PopulationRecord:
        return self.populations[self._index(population_id)]

    def census(self, population_id: str) -> int:
        return self.get(population_id).census

    def is_empty(self, population_id: str) -> bool:
        return self.get(population_id).is_empty

    def coexistence(self, *population_ids: str) -> bool:
        if not population_ids:
            raise ConfigurationError("coexistence requires at least one population_id.")
        # Resolve every id first so missing names cannot be masked by all() short-circuit.
        records = [self.get(pid) for pid in population_ids]
        return all(not rec.is_empty for rec in records)

    def membership_of(self, individual_id: str) -> str | None:
        mid = _as_str(individual_id, "individual_id")
        for rec in self.populations:
            if mid in rec.member_ids:
                return rec.population_id
        return None

    def create_population(
        self,
        population_id: str,
        *,
        member_ids: Sequence[str] = (),
        schedule_partition: str | None = None,
    ) -> PopulationRegistry:
        pid = _refuse_banned_fragment(
            _as_str(population_id, "population_id"), "population_id"
        )
        if pid in self.list_population_ids():
            raise ConfigurationError(f"population_id {pid!r} already exists.")
        record = PopulationRecord(
            population_id=pid,
            member_ids=tuple(member_ids),
            schedule_partition=schedule_partition,
        )
        return PopulationRegistry(
            tick=self.tick,
            populations=self.populations + (record,),
        )

    def add_member(
        self, population_id: str, individual_id: str
    ) -> tuple[PopulationRegistry, PopulationRegistryEvent]:
        mid = _refuse_banned_fragment(
            _as_str(individual_id, "individual_id"), "individual_id"
        )
        owner = self.membership_of(mid)
        if owner is not None:
            raise ConfigurationError(
                f"individual {mid!r} already in population {owner!r}."
            )
        idx = self._index(population_id)
        current = self.populations[idx]
        updated = PopulationRecord(
            population_id=current.population_id,
            member_ids=current.member_ids + (mid,),
            schedule_partition=current.schedule_partition,
        )
        pops = list(self.populations)
        pops[idx] = updated
        registry = PopulationRegistry(tick=self.tick, populations=tuple(pops))
        event = PopulationRegistryEvent(
            population_id=updated.population_id,
            individual_id=mid,
            action="add",
            tick=registry.tick,
            count_after=updated.census,
        )
        return registry, event

    def remove_member(
        self, population_id: str, individual_id: str
    ) -> tuple[PopulationRegistry, PopulationRegistryEvent]:
        mid = _as_str(individual_id, "individual_id")
        idx = self._index(population_id)
        current = self.populations[idx]
        if mid not in current.member_ids:
            raise ConfigurationError(
                f"individual {mid!r} not in population {current.population_id!r}."
            )
        updated = PopulationRecord(
            population_id=current.population_id,
            member_ids=tuple(m for m in current.member_ids if m != mid),
            schedule_partition=current.schedule_partition,
        )
        pops = list(self.populations)
        pops[idx] = updated
        registry = PopulationRegistry(tick=self.tick, populations=tuple(pops))
        event = PopulationRegistryEvent(
            population_id=updated.population_id,
            individual_id=mid,
            action="remove",
            tick=registry.tick,
            count_after=updated.census,
        )
        return registry, event

    def advance_tick(self, tick: int) -> PopulationRegistry:
        """Return a copy with updated tick metadata only (no organism execution)."""

        new_tick = _as_int(tick, "tick", minimum=0)
        if new_tick < self.tick:
            raise ConfigurationError("tick must not decrease.")
        return PopulationRegistry(tick=new_tick, populations=self.populations)


__all__ = [
    "SCHEMA_VERSION",
    "PopulationRecord",
    "PopulationRegistry",
]
