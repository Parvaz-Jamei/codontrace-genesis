"""Append-only ILW event ledger with causal parents and edge_id (ILW-1).

Rejects orphan / unregistered edge_ids, missing required telemetry fields, and
causal parents that are not already present in the ledger. Attempt / accepted /
applied remain separate fields when present. No fixture outcome injection.
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.genesis.ilw.dag import (
    REQUIRED_TELEMETRY_FIELDS,
    IntegrationDAG,
    load_integration_dag,
)

# Core identity/causality fields required on every append at ILW-1.
LEDGER_CORE_REQUIRED_FIELDS: tuple[str, ...] = (
    "run_id",
    "event_id",
    "edge_id",
    "causal_parent_ids",
)


class EventLedgerError(ConfigurationError):
    """Raised when an event cannot be appended to the ILW ledger."""


@dataclass(frozen=True, slots=True)
class LedgerEvent:
    """Immutable snapshot of one accepted ledger event."""

    payload: Mapping[str, JsonValue]
    sequence: int

    @property
    def event_id(self) -> str:
        return str(self.payload["event_id"])

    @property
    def edge_id(self) -> str:
        return str(self.payload["edge_id"])

    @property
    def causal_parent_ids(self) -> tuple[str, ...]:
        raw = self.payload["causal_parent_ids"]
        if isinstance(raw, list):
            return tuple(str(item) for item in raw)
        return ()

    def to_dict(self) -> dict[str, JsonValue]:
        return {"sequence": self.sequence, "payload": dict(self.payload)}

    def digest(self) -> str:
        return canonical_digest(self.to_dict(), prefix="ilw_ledger_event")


@dataclass(slots=True)
class EventLedger:
    """Append-only causal event ledger scoped to one ``run_id``."""

    run_id: str
    dag: IntegrationDAG = field(default_factory=load_integration_dag)
    require_full_telemetry: bool = False
    _events: list[LedgerEvent] = field(default_factory=list, init=False, repr=False)
    _by_id: dict[str, LedgerEvent] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        rid = str(self.run_id).strip()
        if not rid:
            raise EventLedgerError("EventLedger.run_id must be non-empty.")
        object.__setattr__(self, "run_id", rid)

    @property
    def events(self) -> tuple[LedgerEvent, ...]:
        return tuple(self._events)

    @property
    def event_ids(self) -> frozenset[str]:
        return frozenset(self._by_id)

    @property
    def observed_edge_ids(self) -> frozenset[str]:
        return frozenset(event.edge_id for event in self._events)

    def __len__(self) -> int:
        return len(self._events)

    def append(self, event: Mapping[str, Any]) -> LedgerEvent:
        if not isinstance(event, Mapping):
            raise EventLedgerError("Ledger event must be a mapping.")
        self._reject_fixture_injection(event)
        self._validate_attempt_counters(event)

        required = (
            REQUIRED_TELEMETRY_FIELDS
            if self.require_full_telemetry
            else LEDGER_CORE_REQUIRED_FIELDS
        )
        missing = [name for name in required if name not in event]
        if missing:
            raise EventLedgerError(
                "Event missing required ledger fields: " + ", ".join(missing)
            )

        run_id = str(event.get("run_id", "")).strip()
        if run_id != self.run_id:
            raise EventLedgerError(
                f"Event run_id {run_id!r} does not match ledger run_id {self.run_id!r}."
            )

        event_id = str(event.get("event_id", "")).strip()
        if not event_id:
            raise EventLedgerError("event_id must be non-empty.")
        if event_id in self._by_id:
            raise EventLedgerError(f"Duplicate event_id {event_id!r}.")

        edge_id = str(event.get("edge_id", "")).strip()
        if not edge_id:
            raise EventLedgerError("edge_id must be non-empty.")
        if edge_id not in self.dag.edge_ids:
            raise EventLedgerError(
                f"Orphan edge_id {edge_id!r} is not in INTEGRATION_DAG.json."
            )

        parents = self._parse_parent_ids(event.get("causal_parent_ids"))
        missing_parents = [pid for pid in parents if pid not in self._by_id]
        if missing_parents:
            raise EventLedgerError(
                "Orphan causal_parent_ids (not in ledger): " + ", ".join(missing_parents)
            )

        payload: dict[str, JsonValue] = {}
        for key, value in event.items():
            payload[str(key)] = self._to_json_value(value)
        # Normalize causal_parent_ids to a list for digest stability.
        payload["causal_parent_ids"] = list(parents)
        payload["event_id"] = event_id
        payload["edge_id"] = edge_id
        payload["run_id"] = run_id

        record = LedgerEvent(payload=payload, sequence=len(self._events))
        self._events.append(record)
        self._by_id[event_id] = record
        return record

    def get(self, event_id: str) -> LedgerEvent:
        try:
            return self._by_id[event_id]
        except KeyError as exc:
            raise EventLedgerError(f"Unknown event_id {event_id!r}.") from exc

    def digest(self) -> str:
        return canonical_digest(
            {
                "run_id": self.run_id,
                "events": [event.to_dict() for event in self._events],
            },
            prefix="ilw_event_ledger",
        )

    @staticmethod
    def _parse_parent_ids(raw: object) -> tuple[str, ...]:
        if raw is None:
            raise EventLedgerError("causal_parent_ids is required (use [] for roots).")
        if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
            raise EventLedgerError("causal_parent_ids must be a list/tuple of strings.")
        parents: list[str] = []
        for item in raw:
            text = str(item).strip()
            if not text:
                raise EventLedgerError("causal_parent_ids entries must be non-empty.")
            parents.append(text)
        return tuple(parents)

    @staticmethod
    def _validate_attempt_counters(event: Mapping[str, Any]) -> None:
        for banned in (
            "attempt_accepted_applied",
            "attempt_success",
            "attempts_accepted_applied",
        ):
            if banned in event:
                raise EventLedgerError(
                    f"Forbidden collapsed counter field {banned!r}; "
                    "use separate attempted, accepted, and applied fields."
                )

    @staticmethod
    def _reject_fixture_injection(event: Mapping[str, Any]) -> None:
        # Adapters / ledger must stay honest: no fixture outcome injection.
        for banned in (
            "fixture_outcome",
            "injected_outcome",
            "oracle_outcome",
            "treatment_oracle",
            "fitness_shortcut",
        ):
            if banned in event:
                raise EventLedgerError(
                    f"Forbidden fixture/oracle field {banned!r}; "
                    "outcome injection is not allowed in the ILW ledger."
                )

    @staticmethod
    def _to_json_value(value: object) -> JsonValue:
        if value is None or isinstance(value, (str, bool, int, float)):
            if isinstance(value, float):
                from codontrace.genesis.canonical import require_finite_float

                return require_finite_float("ledger_float", value)
            if isinstance(value, bool):
                return value
            if isinstance(value, int) and not isinstance(value, bool):
                return value
            return value  # type: ignore[return-value]
        if isinstance(value, Mapping):
            return {str(k): EventLedger._to_json_value(v) for k, v in value.items()}
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            return [EventLedger._to_json_value(item) for item in value]
        raise EventLedgerError(f"Unsupported ledger value type: {type(value).__name__}")

    def snapshot(self) -> MutableMapping[str, JsonValue]:
        return {
            "run_id": self.run_id,
            "event_count": len(self._events),
            "events": [event.to_dict() for event in self._events],
            "ledger_digest": self.digest(),
        }
