"""Structured trace and timeline objects for replayable CodonTrace runs."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import ClassVar, cast

from codontrace._types import JsonValue, Position
from codontrace.errors import ReplayError

WORLD_EVENT_RESOURCE_PLACED = "resource_placed"
WORLD_EVENT_RESOURCE_REMOVED = "resource_removed"
WORLD_EVENT_RESOURCE_CHANGED = "resource_changed"
WORLD_EVENT_WALL_ADDED = "wall_added"
WORLD_EVENT_WALL_REMOVED = "wall_removed"
WORLD_EVENT_CUSTOM_CELL_SET = "custom_cell_set"
WORLD_EVENT_CUSTOM_CELL_CLEARED = "custom_cell_cleared"
WORLD_EVENT_OBJECT_ADDED = "object_added"
WORLD_EVENT_OBJECT_REMOVED = "object_removed"
WORLD_EVENT_AGENT_REGISTERED = "agent_registered"
WORLD_EVENT_AGENT_MOVED = "agent_moved"
WORLD_EVENT_AGENT_REMOVED = "agent_removed"
WORLD_EVENT_EXTERNAL_REPLENISHMENT = "external_replenishment"
WORLD_EVENT_SNAPSHOT_MARKER = "snapshot_marker"


@dataclass(frozen=True, slots=True)
class TraceEvent:
    """One structured decision event emitted by an agent."""

    __hash__: ClassVar[None] = None  # type: ignore[assignment]

    step: int
    agent_id: str
    codon: str
    action: str
    atp_before: float
    atp_after: float
    position_before: Position
    position_after: Position
    world_delta: dict[str, JsonValue] = field(default_factory=dict)
    status: str = "executed"
    reason: str = ""
    ledger_entry_ids: tuple[int, ...] = ()
    genome_digest: str | None = None
    world_digest_before: str | None = None
    cause_refs: tuple[str, ...] = ()
    config_hash: str | None = None

    @property
    def event_kind(self) -> str:
        """Return the timeline kind for agent decision events."""

        return "agent_action"

    @property
    def schema_version(self) -> int:
        """Return the TraceEvent schema version."""

        return 1

    @property
    def ledger_entry_id(self) -> int | None:
        """Backward-compatible single-entry view for older callers."""

        return self.ledger_entry_ids[0] if self.ledger_entry_ids else None

    @property
    def ledger_entry_refs(self) -> tuple[str, ...]:
        """Return trace-level ATP ledger refs unique across agents."""

        return tuple(f"{self.agent_id}:{entry_id}" for entry_id in self.ledger_entry_ids)

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a JSON-friendly event dictionary."""

        return {
            "event_kind": self.event_kind,
            "schema_version": self.schema_version,
            "step": self.step,
            "agent_id": self.agent_id,
            "codon": self.codon,
            "action": self.action,
            "atp_before": self.atp_before,
            "atp_after": self.atp_after,
            "position_before": _position_to_json(self.position_before),
            "position_after": _position_to_json(self.position_after),
            "world_delta": dict(self.world_delta),
            "status": self.status,
            "reason": self.reason,
            "ledger_entry_ids": [entry_id for entry_id in self.ledger_entry_ids],
            "ledger_entry_refs": [ref for ref in self.ledger_entry_refs],
            "ledger_entry_id": self.ledger_entry_id,
            "genome_digest": self.genome_digest,
            "world_digest_before": self.world_digest_before,
            "cause_refs": [ref for ref in self.cause_refs],
            "config_hash": self.config_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> TraceEvent:
        """Restore a TraceEvent from ``to_dict()`` output."""

        try:
            step = data["step"]
            agent_id = data["agent_id"]
            codon = data["codon"]
            action = data["action"]
            atp_before = data["atp_before"]
            atp_after = data["atp_after"]
            position_before = data["position_before"]
            position_after = data["position_after"]
        except KeyError as exc:
            msg = f"TraceEvent data missing required field {exc.args[0]!r}."
            raise ReplayError(msg) from exc
        if not _is_int_not_bool(step):
            msg = "TraceEvent.step must be an integer."
            raise ReplayError(msg)
        if (
            not isinstance(agent_id, str)
            or not isinstance(codon, str)
            or not isinstance(action, str)
        ):
            msg = "TraceEvent agent_id, codon, and action must be strings."
            raise ReplayError(msg)
        if not _is_number_not_bool(atp_before) or not _is_number_not_bool(atp_after):
            msg = "TraceEvent ATP values must be numeric."
            raise ReplayError(msg)
        ledger_ids_value = data.get("ledger_entry_ids", [])
        if not isinstance(ledger_ids_value, list):
            msg = "TraceEvent.ledger_entry_ids must be a list of integers."
            raise ReplayError(msg)
        ledger_entry_ids: list[int] = []
        for value in ledger_ids_value:
            if not _is_int_not_bool(value):
                msg = "TraceEvent.ledger_entry_ids must be a list of integers."
                raise ReplayError(msg)
            ledger_entry_ids.append(cast(int, value))
        world_delta = data.get("world_delta", {})
        if not isinstance(world_delta, dict):
            msg = "TraceEvent.world_delta must be a dictionary."
            raise ReplayError(msg)
        status = data.get("status", "executed")
        reason = data.get("reason", "")
        if not isinstance(status, str) or not isinstance(reason, str):
            msg = "TraceEvent.status and reason must be strings."
            raise ReplayError(msg)
        genome_digest = data.get("genome_digest")
        world_digest_before = data.get("world_digest_before")
        config_hash = data.get("config_hash")
        for value, name in (
            (genome_digest, "TraceEvent.genome_digest"),
            (world_digest_before, "TraceEvent.world_digest_before"),
            (config_hash, "TraceEvent.config_hash"),
        ):
            if value is not None and not isinstance(value, str):
                msg = f"{name} must be a string or null."
                raise ReplayError(msg)
        cause_refs_value = data.get("cause_refs", [])
        if not isinstance(cause_refs_value, list) or not all(
            isinstance(item, str) for item in cause_refs_value
        ):
            msg = "TraceEvent.cause_refs must be a list of strings."
            raise ReplayError(msg)
        step_int = cast(int, step)
        atp_before_number = cast(int | float, atp_before)
        atp_after_number = cast(int | float, atp_after)
        return cls(
            step=step_int,
            agent_id=agent_id,
            codon=codon,
            action=action,
            atp_before=float(atp_before_number),
            atp_after=float(atp_after_number),
            position_before=_position(position_before),
            position_after=_position(position_after),
            world_delta=world_delta,
            status=status,
            reason=reason,
            ledger_entry_ids=tuple(ledger_entry_ids),
            genome_digest=cast(str | None, genome_digest),
            world_digest_before=cast(str | None, world_digest_before),
            cause_refs=tuple(cast(list[str], cause_refs_value)),
            config_hash=cast(str | None, config_hash),
        )


@dataclass(frozen=True, slots=True)
class WorldEvent:
    """One structured world/environment mutation event."""

    __hash__: ClassVar[None] = None  # type: ignore[assignment]

    schema_version: int
    step: int
    sequence: int
    event_type: str
    position: Position | None = None
    source: str = "environment"
    reason: str = ""
    amount: float = 0.0
    before: dict[str, JsonValue] = field(default_factory=dict)
    after: dict[str, JsonValue] = field(default_factory=dict)
    delta: dict[str, JsonValue] = field(default_factory=dict)
    metadata: dict[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not _is_int_not_bool(self.schema_version) or self.schema_version < 1:
            msg = "WorldEvent.schema_version must be an integer >= 1."
            raise ReplayError(msg)
        if not _is_int_not_bool(self.step) or self.step < 0:
            msg = "WorldEvent.step must be an integer >= 0."
            raise ReplayError(msg)
        if not _is_int_not_bool(self.sequence) or self.sequence < 0:
            msg = "WorldEvent.sequence must be an integer >= 0."
            raise ReplayError(msg)
        if not isinstance(self.event_type, str) or not self.event_type:
            msg = "WorldEvent.event_type must be a non-empty string."
            raise ReplayError(msg)
        if self.position is not None and (
            not isinstance(self.position, tuple)
            or len(self.position) != 2
            or not _is_int_not_bool(self.position[0])
            or not _is_int_not_bool(self.position[1])
        ):
            msg = "WorldEvent.position must be None or a Position tuple."
            raise ReplayError(msg)
        if not isinstance(self.source, str) or not isinstance(self.reason, str):
            msg = "WorldEvent.source and reason must be strings."
            raise ReplayError(msg)
        if not _is_number_not_bool(self.amount):
            msg = "WorldEvent.amount must be numeric."
            raise ReplayError(msg)
        if not all(
            isinstance(item, dict) for item in (self.before, self.after, self.delta, self.metadata)
        ):
            msg = "WorldEvent before/after/delta/metadata must be dictionaries."
            raise ReplayError(msg)

    @property
    def event_kind(self) -> str:
        """Return the timeline kind for world mutation events."""

        return "world_event"

    @property
    def idempotency_key(self) -> str:
        """Return a stable key for detecting repeated application."""

        pos = "none" if self.position is None else f"{self.position[0]},{self.position[1]}"
        return f"v{self.schema_version}:{self.step}:{self.sequence}:{self.event_type}:{pos}"

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a JSON-friendly world event dictionary."""

        return {
            "event_kind": self.event_kind,
            "schema_version": self.schema_version,
            "step": self.step,
            "sequence": self.sequence,
            "event_type": self.event_type,
            "position": None if self.position is None else _position_to_json(self.position),
            "source": self.source,
            "reason": self.reason,
            "amount": float(self.amount),
            "before": dict(self.before),
            "after": dict(self.after),
            "delta": dict(self.delta),
            "metadata": dict(self.metadata),
            "idempotency_key": self.idempotency_key,
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> WorldEvent:
        """Restore a WorldEvent from ``to_dict()`` output."""

        schema_version = _required_int(data, "schema_version")
        step = _required_int(data, "step")
        sequence = _required_int(data, "sequence")
        event_type = data.get("event_type")
        source = data.get("source", "environment")
        reason = data.get("reason", "")
        amount = data.get("amount", 0.0)
        position_value = data.get("position")
        before = data.get("before", {})
        after = data.get("after", {})
        delta = data.get("delta", {})
        metadata = data.get("metadata", {})
        if not isinstance(event_type, str) or not event_type:
            msg = "WorldEvent.event_type must be a non-empty string."
            raise ReplayError(msg)
        if not isinstance(source, str) or not isinstance(reason, str):
            msg = "WorldEvent.source and reason must be strings."
            raise ReplayError(msg)
        if not _is_number_not_bool(amount):
            msg = "WorldEvent.amount must be numeric."
            raise ReplayError(msg)
        if (
            not isinstance(before, dict)
            or not isinstance(after, dict)
            or not isinstance(delta, dict)
            or not isinstance(metadata, dict)
        ):
            msg = "WorldEvent before/after/delta/metadata must be dictionaries."
            raise ReplayError(msg)
        position = None if position_value is None else _position(position_value)
        amount_number = cast(int | float, amount)
        return cls(
            schema_version=schema_version,
            step=step,
            sequence=sequence,
            event_type=event_type,
            position=position,
            source=source,
            reason=reason,
            amount=float(amount_number),
            before=before,
            after=after,
            delta=delta,
            metadata=metadata,
        )


@dataclass(frozen=True, slots=True)
class TimelineFrame:
    """One UI/game-engine-friendly frame of a simulation timeline."""

    __hash__: ClassVar[None] = None  # type: ignore[assignment]

    schema_version: int
    step: int
    world_size: tuple[int, int]
    agents: tuple[dict[str, JsonValue], ...] = ()
    resources: tuple[dict[str, JsonValue], ...] = ()
    walls: tuple[list[int], ...] = ()
    objects: tuple[dict[str, JsonValue], ...] = ()
    events: tuple[dict[str, JsonValue], ...] = ()
    metrics: dict[str, JsonValue] = field(default_factory=dict)

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a JSON-friendly frame dictionary."""

        return {
            "schema_version": self.schema_version,
            "step": self.step,
            "world_size": [self.world_size[0], self.world_size[1]],
            "agents": [dict(agent) for agent in self.agents],
            "resources": [dict(resource) for resource in self.resources],
            "walls": [[point[0], point[1]] for point in self.walls],
            "objects": [dict(obj) for obj in self.objects],
            "events": [dict(event) for event in self.events],
            "metrics": dict(self.metrics),
        }


class Trace:
    """Append-only trace of agent and world timeline events."""

    def __init__(self) -> None:
        self._events: list[TraceEvent] = []
        self._event_sequences: list[int] = []
        self._world_events: list[WorldEvent] = []
        self._next_sequence: int = 0

    def append(self, event: TraceEvent) -> None:
        """Append one agent decision event and reserve its private sequence."""

        self._append_agent_event(event, self.next_sequence())

    def _append_agent_event(self, event: TraceEvent, sequence: int) -> None:
        if sequence < 0:
            msg = "TraceEvent timeline sequence must be non-negative."
            raise ReplayError(msg)
        self._events.append(event)
        self._event_sequences.append(sequence)
        self._next_sequence = max(self._next_sequence, sequence + 1)

    def next_sequence(self) -> int:
        """Return and reserve the next deterministic timeline sequence number."""

        value = self._next_sequence
        self._next_sequence += 1
        return value

    def append_world_event(self, event: WorldEvent) -> None:
        """Append one world/environment mutation event."""

        self._world_events.append(event)
        self._next_sequence = max(self._next_sequence, event.sequence + 1)

    @property
    def events(self) -> tuple[TraceEvent, ...]:
        """Return agent events as an immutable tuple for autocomplete-friendly reads."""

        return tuple(self._events)

    @property
    def world_events(self) -> tuple[WorldEvent, ...]:
        """Return world mutation events as an immutable tuple."""

        return tuple(self._world_events)

    def all_events(self) -> tuple[TraceEvent | WorldEvent, ...]:
        """Return agent and world events in deterministic timeline order."""

        return tuple(item[3] for item in self._timeline_items())

    def last(self) -> TraceEvent:
        """Return the most recent agent decision event."""

        if not self._events:
            msg = "Trace is empty."
            raise IndexError(msg)
        return self._events[-1]

    def to_list(self) -> list[dict[str, JsonValue]]:
        """Return agent events as JSON-friendly dictionaries."""

        return [event.to_dict() for event in self._events]

    @classmethod
    def from_list(cls, items: list[dict[str, JsonValue]]) -> Trace:
        """Restore a trace from agent-event ``to_list()`` output."""

        trace = cls()
        for item in items:
            trace.append(TraceEvent.from_dict(item))
        return trace

    def to_json(self, *, indent: int | None = 2) -> str:
        """Serialize agent events to JSON."""

        return json.dumps(self.to_list(), indent=indent, sort_keys=True)

    def to_jsonl(self) -> str:
        """Serialize only agent decision events as newline-delimited JSON."""

        return "\n".join(
            json.dumps(event.to_dict(), sort_keys=True, separators=(",", ":"))
            for event in self._events
        )

    def to_jsonl_string(self) -> str:
        """Return agent-event newline-delimited JSON as a string; no file I/O is performed."""

        return self.to_jsonl()

    @classmethod
    def from_jsonl_string(cls, text: str) -> Trace:
        """Restore a Trace from a newline-delimited JSON string."""

        return cls.from_jsonl(text)

    @classmethod
    def from_jsonl(cls, text: str) -> Trace:
        """Restore a Trace from newline-delimited agent decision events."""

        trace = cls()
        for line_number, raw_line in enumerate(text.splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                msg = f"Invalid JSONL trace at line {line_number}: {exc.msg}."
                raise ReplayError(msg) from exc
            if not isinstance(value, dict):
                msg = f"Invalid JSONL trace at line {line_number}: expected object."
                raise ReplayError(msg)
            trace.append(TraceEvent.from_dict(cast(dict[str, JsonValue], value)))
        return trace

    def to_bundle(self) -> dict[str, JsonValue]:
        """Return a complete timeline bundle for replay/viewer tooling."""

        return {
            "schema_version": 1,
            "format": "codontrace.timeline.bundle",
            "agent_events": [event.to_dict() for event in self._events],
            "world_events": [event.to_dict() for event in self._world_events],
            "timeline": [
                self._timeline_ref(sequence, order, event)
                for sequence, order, event in self._timeline_items_raw_sorted()
            ],
        }

    def to_bundle_json(self, *, indent: int | None = 2) -> str:
        """Serialize the full timeline bundle to JSON."""

        return json.dumps(self.to_bundle(), indent=indent, sort_keys=True)

    @classmethod
    def from_bundle(cls, data: dict[str, JsonValue]) -> Trace:
        """Restore a Trace from a complete or backward-compatible bundle."""

        agent_values = data.get("agent_events", [])
        world_values = data.get("world_events", [])
        if not isinstance(agent_values, list):
            msg = "Timeline bundle agent_events must be a list."
            raise ReplayError(msg)
        if not isinstance(world_values, list):
            msg = "Timeline bundle world_events must be a list."
            raise ReplayError(msg)
        agent_events: list[TraceEvent] = []
        world_events: list[WorldEvent] = []
        for item in agent_values:
            if not isinstance(item, dict):
                msg = "Timeline bundle agent_events entries must be dictionaries."
                raise ReplayError(msg)
            agent_events.append(TraceEvent.from_dict(item))
        for item in world_values:
            if not isinstance(item, dict):
                msg = "Timeline bundle world_events entries must be dictionaries."
                raise ReplayError(msg)
            world_events.append(WorldEvent.from_dict(item))
        timeline = data.get("timeline")
        if timeline is None:
            trace = cls()
            for agent_event in agent_events:
                trace.append(agent_event)
            for world_event in world_events:
                trace.append_world_event(world_event)
            return trace
        if not isinstance(timeline, list):
            msg = "Timeline bundle timeline must be a list when present."
            raise ReplayError(msg)
        agent_sequences = _restore_agent_sequences(agent_events, world_events, timeline)
        trace = cls()
        for event, sequence in zip(agent_events, agent_sequences, strict=True):
            trace._append_agent_event(event, sequence)
        for world_event in world_events:
            trace.append_world_event(world_event)
        if trace.to_bundle()["timeline"] != timeline:
            msg = "Timeline bundle refs are inconsistent with agent_events/world_events."
            raise ReplayError(msg)
        return trace

    def bundle_digest(self) -> str:
        """Return a stable digest for the full timeline bundle."""

        payload = json.dumps(self.to_bundle(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_engine_events(self) -> list[dict[str, JsonValue]]:
        """Return a compact Unity/Godot/WebGL-friendly mixed event list."""

        items: list[dict[str, JsonValue]] = []
        for sequence, _order, event in self._timeline_items_raw_sorted():
            if isinstance(event, WorldEvent):
                compact: dict[str, JsonValue] = {
                    "t": event.step,
                    "seq": sequence,
                    "kind": "world",
                    "type": event.event_type,
                    "pos": None if event.position is None else _position_to_json(event.position),
                    "value": float(event.amount),
                }
                if event.reason:
                    compact["reason"] = event.reason
                if event.delta:
                    compact["delta"] = dict(event.delta)
                items.append(compact)
            else:
                items.append(
                    {
                        "t": event.step,
                        "seq": sequence,
                        "kind": "agent",
                        "type": event.action,
                        "agent": event.agent_id,
                        "from": _position_to_json(event.position_before),
                        "to": _position_to_json(event.position_after),
                        "status": event.status,
                        "delta": dict(event.world_delta),
                    }
                )
        return items

    def to_engine_json(self, *, indent: int | None = 2) -> str:
        """Serialize compact engine events to JSON."""

        return json.dumps(self.to_engine_events(), indent=indent, sort_keys=True)

    def digest(self) -> str:
        """Return a stable hash for agent-event replay equality checks."""

        return hashlib.sha256(self.to_json(indent=None).encode("utf-8")).hexdigest()

    def causal_slice(self, *, last_n: int = 1) -> list[TraceEvent]:
        """Return the last ``n`` agent events as a compact causal slice."""

        if last_n <= 0:
            msg = "last_n must be positive."
            raise ReplayError(msg)
        return self._events[-last_n:]

    def _timeline_items_raw_sorted(self) -> list[tuple[int, int, TraceEvent | WorldEvent]]:
        items: list[tuple[int, int, TraceEvent | WorldEvent]] = []
        for index, event in enumerate(self._events):
            items.append((self._event_sequences[index], index, event))
        offset = len(self._events)
        for index, world_event in enumerate(self._world_events):
            items.append((world_event.sequence, offset + index, world_event))
        return sorted(
            items,
            key=lambda item: (
                item[2].step,
                item[0],
                _event_kind_order(item[2]),
                item[1],
            ),
        )

    def _timeline_items(self) -> list[tuple[int, int, int, TraceEvent | WorldEvent]]:
        return [
            (event.step, sequence, order, event)
            for sequence, order, event in self._timeline_items_raw_sorted()
        ]

    def _timeline_ref(
        self,
        sequence: int,
        order: int,
        event: TraceEvent | WorldEvent,
    ) -> dict[str, JsonValue]:
        if isinstance(event, WorldEvent):
            return {
                "event_kind": event.event_kind,
                "step": event.step,
                "sequence": sequence,
                "event_type": event.event_type,
            }
        return {
            "event_kind": event.event_kind,
            "step": event.step,
            "sequence": sequence,
            "agent_event_index": order,
            "agent_id": event.agent_id,
            "action": event.action,
            "status": event.status,
        }

    def __len__(self) -> int:
        return len(self._events)

    def __iter__(self) -> Iterator[TraceEvent]:
        return iter(self._events)


def _restore_agent_sequences(
    agent_events: list[TraceEvent],
    world_events: list[WorldEvent],
    timeline: list[JsonValue],
) -> list[int]:
    sequences: list[int | None] = [None for _ in agent_events]
    used_world_keys: set[tuple[int, int, str]] = set()
    used_step_sequences: set[tuple[int, int]] = set()
    seen_refs = 0
    for raw_ref in timeline:
        if not isinstance(raw_ref, dict):
            msg = "Timeline refs must be dictionaries."
            raise ReplayError(msg)
        kind = raw_ref.get("event_kind")
        step = _ref_int(raw_ref, "step")
        sequence = _ref_int(raw_ref, "sequence")
        step_sequence = (step, sequence)
        if step_sequence in used_step_sequences:
            msg = "Timeline refs must not repeat the same step/sequence pair."
            raise ReplayError(msg)
        used_step_sequences.add(step_sequence)
        if kind == "agent_action":
            index_value = raw_ref.get("agent_event_index")
            index = cast(int, index_value) if _is_int_not_bool(index_value) else -1
            if 0 <= index < len(agent_events):
                event = agent_events[index]
                _validate_agent_ref(raw_ref, event)
                if sequences[index] is not None:
                    msg = "Timeline references the same agent event more than once."
                    raise ReplayError(msg)
                sequences[index] = sequence
                seen_refs += 1
                continue
            matches = [
                i
                for i, event in enumerate(agent_events)
                if sequences[i] is None and _agent_ref_matches(raw_ref, event)
            ]
            if len(matches) != 1:
                msg = "Timeline agent ref does not uniquely match an agent event."
                raise ReplayError(msg)
            sequences[matches[0]] = sequence
            seen_refs += 1
        elif kind == "world_event":
            event_type = raw_ref.get("event_type")
            if not isinstance(event_type, str):
                msg = "Timeline world ref requires string event_type."
                raise ReplayError(msg)
            key = (step, sequence, event_type)
            world_matches = [
                world_event
                for world_event in world_events
                if (world_event.step, world_event.sequence, world_event.event_type) == key
            ]
            if len(world_matches) != 1 or key in used_world_keys:
                msg = "Timeline world ref does not uniquely match a world event."
                raise ReplayError(msg)
            used_world_keys.add(key)
            seen_refs += 1
        else:
            msg = "Timeline ref event_kind must be 'agent_action' or 'world_event'."
            raise ReplayError(msg)
    if seen_refs != len(agent_events) + len(world_events):
        msg = "Timeline refs must cover every agent and world event exactly once."
        raise ReplayError(msg)
    restored: list[int] = []
    for value in sequences:
        if value is None:
            msg = "Timeline refs did not assign every agent event sequence."
            raise ReplayError(msg)
        restored.append(value)
    return restored


def _validate_agent_ref(ref: dict[str, JsonValue], event: TraceEvent) -> None:
    if not _agent_ref_matches(ref, event):
        msg = "Timeline agent ref does not match the indexed agent event."
        raise ReplayError(msg)


def _agent_ref_matches(ref: dict[str, JsonValue], event: TraceEvent) -> bool:
    return (
        ref.get("step") == event.step
        and ref.get("agent_id") == event.agent_id
        and ref.get("action") == event.action
        and ref.get("status") == event.status
    )


def _event_kind_order(event: TraceEvent | WorldEvent) -> int:
    if isinstance(event, WorldEvent):
        if event.event_type == WORLD_EVENT_SNAPSHOT_MARKER:
            return 3
        return 0
    return 1


def _position_to_json(position: Position) -> list[JsonValue]:
    return [position[0], position[1]]


def _position(value: JsonValue) -> Position:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or not _is_int_not_bool(value[0])
        or not _is_int_not_bool(value[1])
    ):
        msg = "Position fields must be [x, y]."
        raise ReplayError(msg)
    return (cast(int, value[0]), cast(int, value[1]))


def _required_int(data: dict[str, JsonValue], key: str) -> int:
    value = data.get(key)
    if not _is_int_not_bool(value):
        msg = f"WorldEvent.{key} must be an integer."
        raise ReplayError(msg)
    return cast(int, value)


def _ref_int(data: dict[str, JsonValue], key: str) -> int:
    value = data.get(key)
    if not _is_int_not_bool(value):
        msg = f"Timeline ref {key!r} must be an integer."
        raise ReplayError(msg)
    return cast(int, value)


def _is_int_not_bool(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number_not_bool(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)
