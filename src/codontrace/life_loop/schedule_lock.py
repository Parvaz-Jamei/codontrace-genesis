"""Domain-free schedule lock for the life-loop.

Freeze / replay / unlock arms target a population id or a schedule_partition
tag from Phase 2. Replay uses caller-supplied frames — no second
world step() engine and no discipline vocabulary.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from codontrace._types import JsonValue
from codontrace.contracts.banned import BANNED_DOMAIN_TOKENS
from codontrace.contracts.life_loop_events import ScheduleLockEvent
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.life_loop.populations import PopulationRegistry

SCHEMA_VERSION = "life_loop_schedule_lock_v1"

LockMode = Literal["freeze", "replay_schedule", "unlock"]

LOCK_MODES: frozenset[str] = frozenset({"freeze", "replay_schedule", "unlock"})

ScheduleLockFailReason = Literal[
    "success",
    "unknown_mode",
    "target_required",
    "target_ambiguous",
    "unknown_population",
    "partition_empty",
    "snapshot_missing",
    "frames_required",
    "frame_index_oob",
    "member_missing",
    "banned_fragment",
    "not_locked",
    "bag_not_mapping",
]

SCHEDULE_LOCK_FAIL_REASONS: frozenset[str] = frozenset(
    {
        "success",
        "unknown_mode",
        "target_required",
        "target_ambiguous",
        "unknown_population",
        "partition_empty",
        "snapshot_missing",
        "frames_required",
        "frame_index_oob",
        "member_missing",
        "banned_fragment",
        "not_locked",
        "bag_not_mapping",
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


def _check_digest(existing: str, computed: str, label: str) -> str:
    if existing and existing != computed:
        raise ConfigurationError(f"{label} digest mismatch.")
    return computed


def _bag_digest(bag: Mapping[str, Any]) -> str:
    return canonical_digest(dict(sorted(bag.items())), prefix="state_bag")


def _canonical_bag(bag: Mapping[str, Any]) -> dict[str, JsonValue]:
    if not isinstance(bag, Mapping):
        raise ConfigurationError("bag must be a mapping.")
    return {str(k): bag[k] for k in sorted(str(x) for x in bag.keys())}


@dataclass(frozen=True, slots=True)
class ScheduleLockAttemptCensus:
    """Attempt ledger: attempts == sum(counts.values())."""

    attempts: int = 0
    counts: Mapping[str, int] | None = None
    digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "attempts", _as_int(self.attempts, "attempts", minimum=0))
        raw = self.counts if self.counts is not None else {}
        if not isinstance(raw, Mapping):
            raise ConfigurationError("counts must be a mapping.")
        cleaned: dict[str, int] = {}
        for key, value in raw.items():
            reason = _as_str(key, "reason")
            if reason not in SCHEDULE_LOCK_FAIL_REASONS:
                raise ConfigurationError(f"unknown schedule lock fail reason {reason!r}.")
            cleaned[reason] = _as_int(value, "count", minimum=0)
        object.__setattr__(self, "counts", cleaned)
        total = sum(cleaned.values())
        if total != self.attempts:
            raise ConfigurationError("attempts must equal sum of reason counts.")
        computed = canonical_digest(
            {"attempts": self.attempts, "counts": dict(sorted(cleaned.items()))},
            prefix="schedlock_census",
        )
        object.__setattr__(
            self,
            "digest",
            _check_digest(self.digest, computed, "ScheduleLockAttemptCensus"),
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "attempts": self.attempts,
            "counts": dict(sorted((self.counts or {}).items())),
            "digest": self.digest,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ScheduleLockAttemptCensus:
        return cls(
            attempts=_as_int(data.get("attempts", 0), "attempts", minimum=0),
            counts=data.get("counts") or {},
            digest=_as_str(data.get("digest", ""), "digest", allow_empty=True),
        )

    def record(self, reason: str) -> ScheduleLockAttemptCensus:
        if reason not in SCHEDULE_LOCK_FAIL_REASONS:
            raise ConfigurationError(f"unknown schedule lock fail reason {reason!r}.")
        counts = dict(self.counts or {})
        counts[reason] = counts.get(reason, 0) + 1
        return ScheduleLockAttemptCensus(attempts=self.attempts + 1, counts=counts)


@dataclass(frozen=True, slots=True)
class ScheduleLock:
    """Immutable freeze / replay / unlock policy targeting a subpopulation."""

    schedule_id: str
    lock_mode: LockMode = "unlock"
    population_id: str | None = None
    schedule_partition: str | None = None
    digest: str = ""

    def __post_init__(self) -> None:
        sid = _refuse_banned_fragment(
            _as_str(self.schedule_id, "schedule_id"), "schedule_id"
        )
        object.__setattr__(self, "schedule_id", sid)
        mode = _as_str(self.lock_mode, "lock_mode").casefold()
        if mode not in LOCK_MODES:
            raise ConfigurationError(f"unknown lock_mode {self.lock_mode!r}.")
        object.__setattr__(self, "lock_mode", mode)
        pop = _optional_str(self.population_id, "population_id")
        part = _optional_str(self.schedule_partition, "schedule_partition")
        if pop is not None:
            pop = _refuse_banned_fragment(pop, "population_id")
        if part is not None:
            part = _refuse_banned_fragment(part, "schedule_partition")
        if pop is None and part is None:
            raise ConfigurationError("population_id or schedule_partition required.")
        if pop is not None and part is not None:
            raise ConfigurationError(
                "provide exactly one of population_id or schedule_partition."
            )
        object.__setattr__(self, "population_id", pop)
        object.__setattr__(self, "schedule_partition", part)
        computed = canonical_digest(self._body(), prefix="schedule_lock")
        object.__setattr__(
            self, "digest", _check_digest(self.digest, computed, "ScheduleLock")
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "schema_version": SCHEMA_VERSION,
            "schedule_id": self.schedule_id,
            "lock_mode": self.lock_mode,
            "population_id": self.population_id,
            "schedule_partition": self.schedule_partition,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ScheduleLock:
        return cls(
            schedule_id=_as_str(data.get("schedule_id"), "schedule_id"),
            lock_mode=_as_str(data.get("lock_mode", "unlock"), "lock_mode"),  # type: ignore[arg-type]
            population_id=_optional_str(data.get("population_id"), "population_id"),
            schedule_partition=_optional_str(
                data.get("schedule_partition"), "schedule_partition"
            ),
            digest=_as_str(data.get("digest", ""), "digest", allow_empty=True),
        )


@dataclass(frozen=True, slots=True)
class ScheduleLockState:
    """Runtime lock book: snapshots, optional replay frames, cursor.

    Not a world tick engine. Callers advance ticks elsewhere and invoke
    resolve / apply_replay_frame hooks.
    """

    schedule_id: str
    lock_mode: LockMode = "unlock"
    population_id: str | None = None
    schedule_partition: str | None = None
    member_ids: tuple[str, ...] = ()
    snapshots: Mapping[str, Mapping[str, JsonValue]] | None = None
    frames: tuple[Mapping[str, Mapping[str, JsonValue]], ...] = ()
    frame_index: int = 0
    tick: int = 0
    digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "schedule_id",
            _refuse_banned_fragment(_as_str(self.schedule_id, "schedule_id"), "schedule_id"),
        )
        mode = _as_str(self.lock_mode, "lock_mode").casefold()
        if mode not in LOCK_MODES:
            raise ConfigurationError(f"unknown lock_mode {self.lock_mode!r}.")
        object.__setattr__(self, "lock_mode", mode)
        pop = _optional_str(self.population_id, "population_id")
        part = _optional_str(self.schedule_partition, "schedule_partition")
        if pop is not None:
            pop = _refuse_banned_fragment(pop, "population_id")
        if part is not None:
            part = _refuse_banned_fragment(part, "schedule_partition")
        object.__setattr__(self, "population_id", pop)
        object.__setattr__(self, "schedule_partition", part)
        members = tuple(
            sorted(
                {
                    _refuse_banned_fragment(_as_str(m, "member_id"), "member_id")
                    for m in self.member_ids
                }
            )
        )
        object.__setattr__(self, "member_ids", members)
        snaps_raw = self.snapshots if self.snapshots is not None else {}
        if not isinstance(snaps_raw, Mapping):
            raise ConfigurationError("snapshots must be a mapping.")
        snaps: dict[str, dict[str, JsonValue]] = {}
        for mid, bag in snaps_raw.items():
            key = _refuse_banned_fragment(_as_str(mid, "member_id"), "member_id")
            snaps[key] = _canonical_bag(bag)
        object.__setattr__(self, "snapshots", snaps)
        frames_clean: list[dict[str, dict[str, JsonValue]]] = []
        for frame in self.frames:
            if not isinstance(frame, Mapping):
                raise ConfigurationError("each frame must be a mapping.")
            frame_bags: dict[str, dict[str, JsonValue]] = {}
            for mid, bag in frame.items():
                key = _refuse_banned_fragment(_as_str(mid, "member_id"), "member_id")
                frame_bags[key] = _canonical_bag(bag)
            frames_clean.append(frame_bags)
        object.__setattr__(self, "frames", tuple(frames_clean))
        object.__setattr__(
            self, "frame_index", _as_int(self.frame_index, "frame_index", minimum=0)
        )
        object.__setattr__(self, "tick", _as_int(self.tick, "tick", minimum=0))
        computed = canonical_digest(self._body(), prefix="schedlock_state")
        object.__setattr__(
            self, "digest", _check_digest(self.digest, computed, "ScheduleLockState")
        )

    def _body(self) -> dict[str, JsonValue]:
        snaps = {
            mid: dict(sorted(bag.items()))
            for mid, bag in sorted((self.snapshots or {}).items())
        }
        frames = [
            {mid: dict(sorted(bag.items())) for mid, bag in sorted(frame.items())}
            for frame in self.frames
        ]
        return {
            "schema_version": SCHEMA_VERSION,
            "schedule_id": self.schedule_id,
            "lock_mode": self.lock_mode,
            "population_id": self.population_id,
            "schedule_partition": self.schedule_partition,
            "member_ids": list(self.member_ids),
            "snapshots": snaps,
            "frames": frames,
            "frame_index": self.frame_index,
            "tick": self.tick,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}

    @property
    def is_active(self) -> bool:
        return self.lock_mode in {"freeze", "replay_schedule"}


def resolve_target_members(
    registry: PopulationRegistry,
    *,
    population_id: str | None = None,
    schedule_partition: str | None = None,
) -> tuple[str, ...]:
    """Return sorted member ids for a population id XOR schedule_partition."""

    pop = _optional_str(population_id, "population_id")
    part = _optional_str(schedule_partition, "schedule_partition")
    if pop is None and part is None:
        raise ConfigurationError("population_id or schedule_partition required.")
    if pop is not None and part is not None:
        raise ConfigurationError(
            "provide exactly one of population_id or schedule_partition."
        )
    if pop is not None:
        return registry.get(pop).member_ids
    members: list[str] = []
    for rec in registry.populations:
        if rec.schedule_partition == part:
            members.extend(rec.member_ids)
    if not members:
        raise ConfigurationError(f"schedule_partition {part!r} matches no members.")
    return tuple(sorted(set(members)))


@dataclass(frozen=True, slots=True)
class ScheduleLockApplyRecord:
    """Digest-stable record of one schedule-lock operation."""

    schedule_id: str
    lock_mode: str
    reason: ScheduleLockFailReason
    tick: int
    state_digest: str
    event: ScheduleLockEvent | None
    digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "schedule_id", _as_str(self.schedule_id, "schedule_id"))
        object.__setattr__(self, "lock_mode", _as_str(self.lock_mode, "lock_mode"))
        reason = _as_str(self.reason, "reason")
        if reason not in SCHEDULE_LOCK_FAIL_REASONS:
            raise ConfigurationError(f"unknown schedule lock fail reason {reason!r}.")
        object.__setattr__(self, "reason", reason)
        object.__setattr__(self, "tick", _as_int(self.tick, "tick", minimum=0))
        object.__setattr__(self, "state_digest", _as_str(self.state_digest, "state_digest"))
        computed = canonical_digest(
            {
                "schedule_id": self.schedule_id,
                "lock_mode": self.lock_mode,
                "reason": self.reason,
                "tick": self.tick,
                "state_digest": self.state_digest,
                "event_digest": None if self.event is None else self.event.digest,
            },
            prefix="schedlock_apply",
        )
        object.__setattr__(
            self, "digest", _check_digest(self.digest, computed, "ScheduleLockApplyRecord")
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schedule_id": self.schedule_id,
            "lock_mode": self.lock_mode,
            "reason": self.reason,
            "tick": self.tick,
            "state_digest": self.state_digest,
            "event": None if self.event is None else self.event.to_dict(),
            "digest": self.digest,
        }


def _event_for(
    lock: ScheduleLock, *, tick: int, population_id: str
) -> ScheduleLockEvent:
    return ScheduleLockEvent(
        population_id=population_id,
        lock_mode=lock.lock_mode,
        tick=tick,
        schedule_id=lock.schedule_id,
    )


def apply_schedule_lock(
    lock: ScheduleLock,
    registry: PopulationRegistry,
    live_bags: Mapping[str, Mapping[str, Any]],
    *,
    tick: int = 0,
    frames: Sequence[Mapping[str, Mapping[str, Any]]] = (),
    prior: ScheduleLockState | None = None,
    census: ScheduleLockAttemptCensus | None = None,
) -> tuple[ScheduleLockState, ScheduleLockApplyRecord, ScheduleLockAttemptCensus]:
    """Apply freeze / replay_schedule / unlock against registry members.

    ``live_bags`` maps member_id → opaque heritable state. Freeze captures
    snapshots; replay stores caller frames; unlock clears. No world step().
    """

    if not isinstance(lock, ScheduleLock):
        raise ConfigurationError("lock must be a ScheduleLock.")
    if not isinstance(registry, PopulationRegistry):
        raise ConfigurationError("registry must be a PopulationRegistry.")
    census_state = census if census is not None else ScheduleLockAttemptCensus()
    tick_i = _as_int(tick, "tick", minimum=0)

    try:
        members = resolve_target_members(
            registry,
            population_id=lock.population_id,
            schedule_partition=lock.schedule_partition,
        )
    except ConfigurationError as exc:
        msg = str(exc)
        if "unknown population" in msg or "unknown population_id" in msg:
            reason: ScheduleLockFailReason = "unknown_population"
        elif "matches no members" in msg:
            reason = "partition_empty"
        elif "exactly one" in msg:
            reason = "target_ambiguous"
        else:
            reason = "target_required"
        census_state = census_state.record(reason)
        empty = ScheduleLockState(
            schedule_id=lock.schedule_id,
            lock_mode="unlock",
            population_id=lock.population_id,
            schedule_partition=lock.schedule_partition,
            tick=tick_i,
        )
        record = ScheduleLockApplyRecord(
            schedule_id=lock.schedule_id,
            lock_mode=lock.lock_mode,
            reason=reason,
            tick=tick_i,
            state_digest=empty.digest,
            event=None,
        )
        return empty, record, census_state

    pop_label = lock.population_id or f"partition:{lock.schedule_partition}"

    if lock.lock_mode == "freeze":
        snaps: dict[str, dict[str, JsonValue]] = {}
        for mid in members:
            if mid not in live_bags:
                census_state = census_state.record("member_missing")
                empty = ScheduleLockState(
                    schedule_id=lock.schedule_id,
                    lock_mode="unlock",
                    population_id=lock.population_id,
                    schedule_partition=lock.schedule_partition,
                    member_ids=members,
                    tick=tick_i,
                )
                record = ScheduleLockApplyRecord(
                    schedule_id=lock.schedule_id,
                    lock_mode=lock.lock_mode,
                    reason="member_missing",
                    tick=tick_i,
                    state_digest=empty.digest,
                    event=None,
                )
                return empty, record, census_state
            try:
                snaps[mid] = _canonical_bag(live_bags[mid])
            except ConfigurationError:
                census_state = census_state.record("bag_not_mapping")
                empty = ScheduleLockState(
                    schedule_id=lock.schedule_id,
                    lock_mode="unlock",
                    population_id=lock.population_id,
                    schedule_partition=lock.schedule_partition,
                    member_ids=members,
                    tick=tick_i,
                )
                record = ScheduleLockApplyRecord(
                    schedule_id=lock.schedule_id,
                    lock_mode=lock.lock_mode,
                    reason="bag_not_mapping",
                    tick=tick_i,
                    state_digest=empty.digest,
                    event=None,
                )
                return empty, record, census_state
        state = ScheduleLockState(
            schedule_id=lock.schedule_id,
            lock_mode="freeze",
            population_id=lock.population_id,
            schedule_partition=lock.schedule_partition,
            member_ids=members,
            snapshots=snaps,
            tick=tick_i,
        )
        event = _event_for(lock, tick=tick_i, population_id=pop_label)
        census_state = census_state.record("success")
        record = ScheduleLockApplyRecord(
            schedule_id=lock.schedule_id,
            lock_mode=lock.lock_mode,
            reason="success",
            tick=tick_i,
            state_digest=state.digest,
            event=event,
        )
        return state, record, census_state

    if lock.lock_mode == "replay_schedule":
        if not frames:
            census_state = census_state.record("frames_required")
            empty = ScheduleLockState(
                schedule_id=lock.schedule_id,
                lock_mode="unlock",
                population_id=lock.population_id,
                schedule_partition=lock.schedule_partition,
                member_ids=members,
                tick=tick_i,
            )
            record = ScheduleLockApplyRecord(
                schedule_id=lock.schedule_id,
                lock_mode=lock.lock_mode,
                reason="frames_required",
                tick=tick_i,
                state_digest=empty.digest,
                event=None,
            )
            return empty, record, census_state
        state = ScheduleLockState(
            schedule_id=lock.schedule_id,
            lock_mode="replay_schedule",
            population_id=lock.population_id,
            schedule_partition=lock.schedule_partition,
            member_ids=members,
            frames=tuple(frames),
            frame_index=0,
            tick=tick_i,
        )
        event = _event_for(lock, tick=tick_i, population_id=pop_label)
        census_state = census_state.record("success")
        record = ScheduleLockApplyRecord(
            schedule_id=lock.schedule_id,
            lock_mode=lock.lock_mode,
            reason="success",
            tick=tick_i,
            state_digest=state.digest,
            event=event,
        )
        return state, record, census_state

    # unlock
    _ = prior  # prior may be used by callers for continuity; unlock resets.
    state = ScheduleLockState(
        schedule_id=lock.schedule_id,
        lock_mode="unlock",
        population_id=lock.population_id,
        schedule_partition=lock.schedule_partition,
        member_ids=members,
        tick=tick_i,
    )
    event = _event_for(lock, tick=tick_i, population_id=pop_label)
    census_state = census_state.record("success")
    record = ScheduleLockApplyRecord(
        schedule_id=lock.schedule_id,
        lock_mode=lock.lock_mode,
        reason="success",
        tick=tick_i,
        state_digest=state.digest,
        event=event,
    )
    return state, record, census_state


def resolve_member_state(
    state: ScheduleLockState,
    member_id: str,
    live_bag: Mapping[str, Any],
) -> tuple[dict[str, JsonValue], ScheduleLockFailReason]:
    """Return the bag a locked member should use at this hook.

    freeze → frozen snapshot; replay_schedule → current frame bag;
    unlock / non-member → live bag copy.
    """

    mid = _as_str(member_id, "member_id")
    if state.lock_mode == "unlock" or mid not in state.member_ids:
        try:
            return _canonical_bag(live_bag), "success"
        except ConfigurationError:
            return {}, "bag_not_mapping"

    if state.lock_mode == "freeze":
        snaps = state.snapshots or {}
        if mid not in snaps:
            return {}, "snapshot_missing"
        return dict(snaps[mid]), "success"

    if state.lock_mode == "replay_schedule":
        if not state.frames:
            return {}, "frames_required"
        if state.frame_index >= len(state.frames):
            return {}, "frame_index_oob"
        frame = state.frames[state.frame_index]
        if mid not in frame:
            return {}, "member_missing"
        return dict(frame[mid]), "success"

    return {}, "unknown_mode"


def apply_replay_frame(
    state: ScheduleLockState,
    *,
    tick: int | None = None,
) -> tuple[ScheduleLockState, dict[str, dict[str, JsonValue]], ScheduleLockFailReason]:
    """Advance one replay frame; return (new_state, frame_bags, reason).

    Bit-identical for the same state + frames. Does not call world step().
    """

    if state.lock_mode != "replay_schedule":
        return state, {}, "not_locked"
    if not state.frames:
        return state, {}, "frames_required"
    if state.frame_index >= len(state.frames):
        return state, {}, "frame_index_oob"
    frame = {mid: dict(bag) for mid, bag in state.frames[state.frame_index].items()}
    new_tick = state.tick if tick is None else _as_int(tick, "tick", minimum=0)
    new_state = ScheduleLockState(
        schedule_id=state.schedule_id,
        lock_mode=state.lock_mode,
        population_id=state.population_id,
        schedule_partition=state.schedule_partition,
        member_ids=state.member_ids,
        snapshots=state.snapshots,
        frames=state.frames,
        frame_index=state.frame_index + 1,
        tick=new_tick,
    )
    return new_state, frame, "success"


__all__ = [
    "LOCK_MODES",
    "SCHEDULE_LOCK_FAIL_REASONS",
    "SCHEMA_VERSION",
    "LockMode",
    "ScheduleLock",
    "ScheduleLockApplyRecord",
    "ScheduleLockAttemptCensus",
    "ScheduleLockFailReason",
    "ScheduleLockState",
    "apply_replay_frame",
    "apply_schedule_lock",
    "resolve_member_state",
    "resolve_target_members",
]
