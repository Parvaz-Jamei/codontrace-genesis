"""Bounded in-memory episodic memory for GENESIS Foundation experiments."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from codontrace._types import JsonValue, Position
from codontrace.genesis.atp import GenesisATPState
from codontrace._numeric import finite_float, finite_json_dumps


@dataclass(frozen=True, slots=True)
class EpisodicEvent:
    """One bounded audit-memory event derived from a TraceEvent."""

    tick: int
    organism_id: str
    action: str
    status: str
    position_before: Position
    position_after: Position
    atp_runtime_before: float
    atp_runtime_after: float
    atp_learning_before: float
    atp_learning_after: float
    world_digest_before: str | None
    trace_event_digest: str
    observation: dict[str, JsonValue]
    outcome: dict[str, JsonValue]

    def __post_init__(self) -> None:
        if self.tick < 0:
            msg = "EpisodicEvent.tick must be non-negative."
            raise ValueError(msg)
        if not self.organism_id:
            msg = "EpisodicEvent.organism_id must not be empty."
            raise ValueError(msg)
        for field_name in (
            "atp_runtime_before",
            "atp_runtime_after",
            "atp_learning_before",
            "atp_learning_after",
        ):
            object.__setattr__(
                self,
                field_name,
                finite_float(f"EpisodicEvent.{field_name}", getattr(self, field_name)),
            )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "tick": self.tick,
            "organism_id": self.organism_id,
            "action": self.action,
            "status": self.status,
            "position_before": [self.position_before[0], self.position_before[1]],
            "position_after": [self.position_after[0], self.position_after[1]],
            "atp_runtime_before": self.atp_runtime_before,
            "atp_runtime_after": self.atp_runtime_after,
            "atp_learning_before": self.atp_learning_before,
            "atp_learning_after": self.atp_learning_after,
            "world_digest_before": self.world_digest_before,
            "trace_event_digest": self.trace_event_digest,
            "observation": dict(self.observation),
            "outcome": dict(self.outcome),
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> EpisodicEvent:
        observation = data.get("observation", {})
        outcome = data.get("outcome", {})
        if not isinstance(observation, dict) or not isinstance(outcome, dict):
            msg = "EpisodicEvent observation/outcome must be dictionaries."
            raise ValueError(msg)
        world_digest = data.get("world_digest_before")
        if world_digest is not None and not isinstance(world_digest, str):
            msg = "world_digest_before must be a string or null."
            raise ValueError(msg)
        return cls(
            tick=_int(data, "tick", 0),
            organism_id=_str(data, "organism_id"),
            action=_str(data, "action"),
            status=_str(data, "status"),
            position_before=_position(data.get("position_before")),
            position_after=_position(data.get("position_after")),
            atp_runtime_before=_float(data, "atp_runtime_before", 0.0),
            atp_runtime_after=_float(data, "atp_runtime_after", 0.0),
            atp_learning_before=_float(data, "atp_learning_before", 0.0),
            atp_learning_after=_float(data, "atp_learning_after", 0.0),
            world_digest_before=world_digest,
            trace_event_digest=_str(data, "trace_event_digest"),
            observation={str(key): value for key, value in observation.items()},
            outcome={str(key): value for key, value in outcome.items()},
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class EpisodicMemoryConfig:
    """Bounded ring-buffer memory settings."""

    capacity: int = 128
    write_enabled: bool = True
    consolidate_enabled: bool = True
    prediction_error_threshold: float = 0.25
    max_events_per_tick: int = 1

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            msg = "EpisodicMemoryConfig.capacity must be > 0."
            raise ValueError(msg)
        object.__setattr__(
            self,
            "prediction_error_threshold",
            finite_float(
                "EpisodicMemoryConfig.prediction_error_threshold",
                self.prediction_error_threshold,
                non_negative=True,
            ),
        )
        if self.max_events_per_tick <= 0:
            msg = "max_events_per_tick must be > 0."
            raise ValueError(msg)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "capacity": self.capacity,
            "write_enabled": self.write_enabled,
            "consolidate_enabled": self.consolidate_enabled,
            "prediction_error_threshold": self.prediction_error_threshold,
            "max_events_per_tick": self.max_events_per_tick,
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> EpisodicMemoryConfig:
        return cls(
            capacity=_int(data, "capacity", 128),
            write_enabled=_bool(data, "write_enabled", True),
            consolidate_enabled=_bool(data, "consolidate_enabled", True),
            prediction_error_threshold=_float(data, "prediction_error_threshold", 0.25),
            max_events_per_tick=_int(data, "max_events_per_tick", 1),
        )


@dataclass(frozen=True, slots=True)
class MemoryWriteResult:
    """Result returned by an in-memory episodic write attempt."""

    written: bool
    blocked_reason: str | None
    memory_size_before: int
    memory_size_after: int
    learning_ledger_entry_id: int | None
    memory_digest_before: str
    memory_digest_after: str
    evicted_count: int = 0
    evicted_event_digests: tuple[str, ...] = ()
    write_status: str = "written"

    def __post_init__(self) -> None:
        if self.evicted_count < 0:
            msg = "MemoryWriteResult.evicted_count must be non-negative."
            raise ValueError(msg)
        object.__setattr__(self, "evicted_event_digests", tuple(str(x) for x in self.evicted_event_digests))
        if self.evicted_count != len(self.evicted_event_digests):
            object.__setattr__(self, "evicted_count", len(self.evicted_event_digests))
        allowed = {"written", "written_with_eviction", "blocked"}
        if self.write_status not in allowed:
            msg = f"MemoryWriteResult.write_status must be one of {sorted(allowed)}."
            raise ValueError(msg)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "written": self.written,
            "blocked_reason": self.blocked_reason,
            "memory_size_before": self.memory_size_before,
            "memory_size_after": self.memory_size_after,
            "learning_ledger_entry_id": self.learning_ledger_entry_id,
            "memory_digest_before": self.memory_digest_before,
            "memory_digest_after": self.memory_digest_after,
            "evicted_count": self.evicted_count,
            "evicted_event_digests": list(self.evicted_event_digests),
            "write_status": self.write_status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> MemoryWriteResult:
        ledger = data.get("learning_ledger_entry_id")
        if ledger is not None and (isinstance(ledger, bool) or not isinstance(ledger, int)):
            msg = "learning_ledger_entry_id must be an integer or null."
            raise ValueError(msg)
        blocked = data.get("blocked_reason")
        if blocked is not None and not isinstance(blocked, str):
            msg = "blocked_reason must be a string or null."
            raise ValueError(msg)
        evicted_raw = data.get("evicted_event_digests", [])
        if not isinstance(evicted_raw, list) or not all(isinstance(x, str) for x in evicted_raw):
            msg = "evicted_event_digests must be a list of strings."
            raise ValueError(msg)
        written = _bool(data, "written", False)
        write_status_raw = data.get("write_status", "written" if written else "blocked")
        if not isinstance(write_status_raw, str):
            msg = "write_status must be a string."
            raise ValueError(msg)
        return cls(
            written=written,
            blocked_reason=blocked,
            memory_size_before=_int(data, "memory_size_before", 0),
            memory_size_after=_int(data, "memory_size_after", 0),
            learning_ledger_entry_id=ledger,
            memory_digest_before=_str(data, "memory_digest_before"),
            memory_digest_after=_str(data, "memory_digest_after"),
            evicted_count=_int(data, "evicted_count", len(evicted_raw)),
            evicted_event_digests=tuple(str(x) for x in evicted_raw),
            write_status=write_status_raw,
        )


@dataclass(frozen=True, slots=True)
class MemoryAppendAudit:
    """Append outcome with explicit ring-buffer eviction evidence."""

    appended: bool
    blocked_reason: str | None = None
    evicted_event_digests: tuple[str, ...] = ()

    @property
    def evicted_count(self) -> int:
        return len(self.evicted_event_digests)


@dataclass(slots=True)
class EpisodicMemory:
    """Bounded deterministic in-memory ring buffer."""

    config: EpisodicMemoryConfig = field(default_factory=EpisodicMemoryConfig)
    _events: list[EpisodicEvent] = field(default_factory=list, init=False, repr=False)

    @property
    def events(self) -> tuple[EpisodicEvent, ...]:
        return tuple(self._events)

    def append(self, event: EpisodicEvent) -> bool:
        """Append without ATP accounting; useful for pure deserialization/tests."""

        return self._append_unmetered_with_audit(event).appended

    def write_event(
        self,
        event: EpisodicEvent,
        atp_state: GenesisATPState,
        *,
        cost: float,
        reason: str = "episodic_memory_write",
    ) -> MemoryWriteResult:
        """Attempt an ATP_learning-metered memory write."""

        before_digest = self.digest()
        before_size = len(self._events)
        if not self.config.write_enabled:
            return MemoryWriteResult(
                written=False,
                blocked_reason="memory_write_disabled",
                memory_size_before=before_size,
                memory_size_after=before_size,
                learning_ledger_entry_id=None,
                memory_digest_before=before_digest,
                memory_digest_after=before_digest,
                write_status="blocked",
            )
        if not self._can_append(event):
            return MemoryWriteResult(
                written=False,
                blocked_reason="max_events_per_tick_reached",
                memory_size_before=before_size,
                memory_size_after=before_size,
                learning_ledger_entry_id=None,
                memory_digest_before=before_digest,
                memory_digest_after=before_digest,
                write_status="blocked",
            )
        ledger_id = atp_state.debit_learning(
            cost,
            tick=event.tick,
            organism_id=event.organism_id,
            reason=reason,
            event_ref=event.trace_event_digest,
        )
        if ledger_id is None and cost > 0:
            return MemoryWriteResult(
                written=False,
                blocked_reason="insufficient_learning_atp",
                memory_size_before=before_size,
                memory_size_after=before_size,
                learning_ledger_entry_id=None,
                memory_digest_before=before_digest,
                memory_digest_after=before_digest,
                write_status="blocked",
            )
        append_audit = self._append_unmetered_with_audit(event)
        if not append_audit.appended:  # defensive: capacity was checked above.
            return MemoryWriteResult(
                written=False,
                blocked_reason=append_audit.blocked_reason or "max_events_per_tick_reached",
                memory_size_before=before_size,
                memory_size_after=before_size,
                learning_ledger_entry_id=None,
                memory_digest_before=before_digest,
                memory_digest_after=before_digest,
                write_status="blocked",
            )
        return MemoryWriteResult(
            written=True,
            blocked_reason=None,
            memory_size_before=before_size,
            memory_size_after=len(self._events),
            learning_ledger_entry_id=ledger_id,
            memory_digest_before=before_digest,
            memory_digest_after=self.digest(),
            evicted_count=append_audit.evicted_count,
            evicted_event_digests=append_audit.evicted_event_digests,
            write_status="written_with_eviction" if append_audit.evicted_count else "written",
        )

    def recent(self, n: int) -> tuple[EpisodicEvent, ...]:
        if n < 0:
            msg = "recent(n) requires n >= 0."
            raise ValueError(msg)
        return tuple(self._events[-n:]) if n else ()

    def by_action(self, action: str) -> tuple[EpisodicEvent, ...]:
        return tuple(event for event in self._events if event.action == action)

    def digest(self) -> str:
        return _digest(self.to_dict())

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "config": self.config.to_dict(),
            "events": [event.to_dict() for event in self._events],
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> EpisodicMemory:
        config_raw = data.get("config", {})
        events_raw = data.get("events", [])
        if not isinstance(config_raw, dict):
            msg = "EpisodicMemory.config must be an object."
            raise ValueError(msg)
        if not isinstance(events_raw, list):
            msg = "EpisodicMemory.events must be a list."
            raise ValueError(msg)
        memory = cls(config=EpisodicMemoryConfig.from_dict(config_raw))
        if len(events_raw) > memory.config.capacity:
            msg = (
                "EpisodicMemory.from_dict would silently drop events; "
                "config capacity is incompatible with serialized data."
            )
            raise ValueError(msg)
        tick_counts: dict[int, int] = {}
        for item in events_raw:
            if isinstance(item, dict):
                tick = _int(item, "tick", 0)
                tick_counts[tick] = tick_counts.get(tick, 0) + 1
        if any(count > memory.config.max_events_per_tick for count in tick_counts.values()):
            msg = (
                "EpisodicMemory.from_dict would silently drop an event; "
                "config max_events_per_tick is incompatible with serialized data."
            )
            raise ValueError(msg)
        for item in events_raw:
            if not isinstance(item, dict):
                msg = "EpisodicMemory event entries must be objects."
                raise ValueError(msg)
            event = EpisodicEvent.from_dict(item)
            if not memory._append_unmetered_with_audit(event).appended:
                msg = (
                    "EpisodicMemory.from_dict would silently drop an event; "
                    "config capacity/max_events_per_tick is incompatible with serialized data."
                )
                raise ValueError(msg)
        return memory

    def _can_append(self, event: EpisodicEvent) -> bool:
        same_tick = sum(1 for existing in self._events if existing.tick == event.tick)
        return same_tick < self.config.max_events_per_tick

    def _append_unmetered(self, event: EpisodicEvent) -> bool:
        return self._append_unmetered_with_audit(event).appended

    def _append_unmetered_with_audit(self, event: EpisodicEvent) -> MemoryAppendAudit:
        if not self._can_append(event):
            return MemoryAppendAudit(appended=False, blocked_reason="max_events_per_tick_reached")
        self._events.append(event)
        overflow = len(self._events) - self.config.capacity
        evicted = tuple(item.digest() for item in self._events[:overflow]) if overflow > 0 else ()
        if overflow > 0:
            del self._events[:overflow]
        return MemoryAppendAudit(appended=True, evicted_event_digests=evicted)


def _digest(data: dict[str, JsonValue]) -> str:
    encoded = finite_json_dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _bool(data: dict[str, JsonValue], key: str, default: bool) -> bool:
    value = data.get(key, default)
    if not isinstance(value, bool):
        msg = f"{key} must be a boolean."
        raise ValueError(msg)
    return value


def _float(data: dict[str, JsonValue], key: str, default: float) -> float:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int | float):
        msg = f"{key} must be numeric."
        raise ValueError(msg)
    return finite_float(key, value)  # type: ignore[return-value]


def _int(data: dict[str, JsonValue], key: str, default: int) -> int:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{key} must be an integer."
        raise ValueError(msg)
    return int(value)


def _str(data: dict[str, JsonValue], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        msg = f"{key} must be a string."
        raise ValueError(msg)
    return value


def _position(value: JsonValue | None) -> Position:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or isinstance(value[0], bool)
        or isinstance(value[1], bool)
        or not isinstance(value[0], int)
        or not isinstance(value[1], int)
    ):
        msg = "position must be a two-item integer list."
        raise ValueError(msg)
    return (value[0], value[1])


@dataclass(frozen=True, slots=True)
class SignalActionLink:
    signal_seen_tick: int
    memory_written_tick: int | None
    memory_read_tick: int | None
    decision_tick: int
    reward_tick: int | None = None
    correct_delayed_action: bool = False
    memory_enabled: bool = True
    memory_required: bool = False
    memory_key: str | None = None
    action_after_memory: str | None = None
    reward_after_action: float | None = None
    schema_version: str = "signal_action_link_v1"

    def _payload_without_digest(self) -> dict[str, JsonValue]:
        latency = None
        if self.memory_read_tick is not None and self.signal_seen_tick is not None:
            latency = max(0, self.memory_read_tick - self.signal_seen_tick)
        return {
            "schema_version": self.schema_version,
            "signal_seen_tick": self.signal_seen_tick,
            "memory_written_tick": self.memory_written_tick,
            "memory_read_tick": self.memory_read_tick,
            "decision_tick": self.decision_tick,
            "reward_tick": self.reward_tick,
            "latency": latency,
            "memory_key": self.memory_key,
            "action_after_memory": self.action_after_memory,
            "reward_after_action": self.reward_after_action,
            "correct_delayed_action": self.correct_delayed_action,
            "memory_enabled": self.memory_enabled,
            "memory_required": self.memory_required,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        payload = self._payload_without_digest()
        payload["link_digest"] = _digest(payload)
        return payload

    def digest(self) -> str:
        return _digest(self._payload_without_digest())


@dataclass(frozen=True, slots=True)
class MemoryUseEvidence(SignalActionLink):
    schema_version: str = "memory_use_evidence_v1"


@dataclass(frozen=True, slots=True)
class DelayedRewardTrace(SignalActionLink):
    schema_version: str = "delayed_reward_trace_v1"

# ---------------------------------------------------------------------------
# Signal/capsule -> memory -> action causal evidence primitives (P0/P2)
# ---------------------------------------------------------------------------
from codontrace.genesis.canonical import canonical_digest as _genesis_canonical_digest, require_finite_float as _genesis_require_finite_float


@dataclass(frozen=True, slots=True)
class SignalMemoryCausalLinkRecord:
    """Evidence chain for capsule/signal use through memory into behavior.

    This record does not claim causality from a read count alone.  It requires a
    sequence of signal observation, memory write, later memory read, changed
    behavior digest, and reward/selection delta.  Claim eligibility remains
    false unless the chain has a real control/intervention digest.
    """

    signal_id: str
    capsule_id: str
    target_organism_id: str
    signal_seen_tick: int
    memory_write_tick: int
    memory_read_tick: int
    action_after_memory: str
    behavior_digest_before: str
    behavior_digest_after: str
    reward_delta: float
    selection_delta: float = 0.0
    memory_record_digest: str | None = None
    action_record_digest: str | None = None
    control_digest: str | None = None
    blocked_reason: str | None = None
    schema_version: str = "signal_memory_causal_link_record_v1"
    record_digest: str = ""

    def __post_init__(self) -> None:
        for name in ("signal_id", "capsule_id", "target_organism_id", "action_after_memory", "behavior_digest_before", "behavior_digest_after"):
            if not getattr(self, name):
                raise ValueError(f"{name} is required")
        if self.signal_seen_tick < 0 or self.memory_write_tick < self.signal_seen_tick or self.memory_read_tick < self.memory_write_tick:
            raise ValueError("signal/memory ticks must be ordered and non-negative")
        object.__setattr__(self, "reward_delta", round(_genesis_require_finite_float("reward_delta", self.reward_delta), 10))
        object.__setattr__(self, "selection_delta", round(_genesis_require_finite_float("selection_delta", self.selection_delta), 10))
        if not self.record_digest:
            object.__setattr__(self, "record_digest", _genesis_canonical_digest(self._payload(), prefix="signal_memory_link"))

    @property
    def behavior_changed(self) -> bool:
        return self.behavior_digest_before != self.behavior_digest_after

    @property
    def claim_eligible(self) -> bool:
        return (
            not self.blocked_reason
            and self.behavior_changed
            and bool(self.control_digest)
            and bool(self.memory_record_digest)
            and bool(self.action_record_digest)
            and (self.reward_delta > 0.0 or self.selection_delta > 0.0)
        )

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "signal_id": self.signal_id,
            "capsule_id": self.capsule_id,
            "target_organism_id": self.target_organism_id,
            "signal_seen_tick": self.signal_seen_tick,
            "memory_write_tick": self.memory_write_tick,
            "memory_read_tick": self.memory_read_tick,
            "action_after_memory": self.action_after_memory,
            "behavior_digest_before": self.behavior_digest_before,
            "behavior_digest_after": self.behavior_digest_after,
            "behavior_changed": self.behavior_changed,
            "reward_delta": self.reward_delta,
            "selection_delta": self.selection_delta,
            "memory_record_digest": self.memory_record_digest,
            "action_record_digest": self.action_record_digest,
            "control_digest": self.control_digest,
            "blocked_reason": self.blocked_reason,
            "claim_eligible": self.claim_eligible,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "record_digest": self.record_digest}

    def digest(self) -> str:
        return self.record_digest


@dataclass(frozen=True, slots=True)
class SourceReputationMemory:
    """Deterministic source reputation table for capsule senders."""

    source_scores: tuple[tuple[str, float], ...] = ()
    learning_rate: float = 0.25
    schema_version: str = "source_reputation_memory_v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "learning_rate", _genesis_require_finite_float("learning_rate", self.learning_rate, non_negative=True))
        if self.learning_rate > 1.0:
            raise ValueError("learning_rate must be <= 1.0")
        normalized = tuple(sorted((str(source), round(_genesis_require_finite_float("source_score", score), 10)) for source, score in self.source_scores))
        object.__setattr__(self, "source_scores", normalized)

    def score_for(self, source_id: str) -> float:
        return dict(self.source_scores).get(source_id, 0.0)

    def update_from_packet_outcome(self, source_id: str, *, useful: bool, outcome_delta: float) -> "SourceReputationMemory":
        delta = _genesis_require_finite_float("outcome_delta", outcome_delta)
        old = self.score_for(source_id)
        signed = abs(delta) if useful else -abs(delta)
        new = round(old + self.learning_rate * signed, 10)
        data = dict(self.source_scores)
        data[str(source_id)] = new
        return SourceReputationMemory(tuple(data.items()), learning_rate=self.learning_rate)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "learning_rate": self.learning_rate,
            "source_scores": [[source, score] for source, score in self.source_scores],
        }

    def digest(self) -> str:
        return _genesis_canonical_digest(self.to_dict(), prefix="source_reputation")
