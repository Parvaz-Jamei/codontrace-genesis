"""Fail-first event consumer for ILW integration edges.

Events whose ``edge_id`` is unknown, or which lack a registered consumer for
that edge, are rejected loudly. Attempt / accepted / applied must remain
separate fields when present.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, MutableMapping
from typing import Any

from codontrace.errors import ConfigurationError
from codontrace.genesis.ilw.dag import IntegrationDAG, load_integration_dag

EventPayload = Mapping[str, Any]
EventHandler = Callable[[EventPayload], None]


class OrphanEventError(ConfigurationError):
    """Raised when an event has no DAG edge or no registered consumer."""


class RegisteredEventConsumer:
    """Dispatches ledger events only to consumers registered for known edges."""

    def __init__(self, dag: IntegrationDAG | None = None) -> None:
        self._dag = dag if dag is not None else load_integration_dag()
        self._consumers: dict[str, EventHandler] = {}

    @property
    def dag(self) -> IntegrationDAG:
        return self._dag

    @property
    def registered_edge_ids(self) -> frozenset[str]:
        return frozenset(self._consumers)

    def register(self, edge_id: str, handler: EventHandler) -> None:
        eid = str(edge_id).strip()
        if not eid:
            raise OrphanEventError("edge_id must be non-empty.")
        if eid not in self._dag.edge_ids:
            raise OrphanEventError(
                f"Cannot register consumer for orphan edge_id {eid!r}: "
                "not declared in INTEGRATION_DAG.json."
            )
        if not callable(handler):
            raise OrphanEventError("Event consumer handler must be callable.")
        self._consumers[eid] = handler

    def consume(self, event: EventPayload) -> None:
        if not isinstance(event, Mapping):
            raise OrphanEventError("Event payload must be a mapping.")
        edge_id = str(event.get("edge_id", "")).strip()
        if not edge_id:
            raise OrphanEventError("Event missing edge_id; rejecting orphan event.")
        if edge_id not in self._dag.edge_ids:
            raise OrphanEventError(
                f"Orphan event edge_id {edge_id!r} is not in INTEGRATION_DAG.json."
            )
        handler = self._consumers.get(edge_id)
        if handler is None:
            raise OrphanEventError(
                f"No registered consumer for edge_id {edge_id!r}; "
                "failing before full-world claim."
            )
        self._validate_attempt_counters(event, edge_id)
        handler(event)

    @staticmethod
    def _validate_attempt_counters(event: EventPayload, edge_id: str) -> None:
        # Attempt / accepted / applied must never be one collapsed counter.
        for banned in ("attempt_accepted_applied", "attempt_success", "attempts_accepted_applied"):
            if banned in event:
                raise OrphanEventError(
                    f"Edge {edge_id!r} forbids collapsed counter field {banned!r}; "
                    "use separate attempted, accepted, and applied fields."
                )

    def consume_many(self, events: list[EventPayload]) -> None:
        for event in events:
            self.consume(event)

    def snapshot_handlers(self) -> MutableMapping[str, EventHandler]:
        return dict(self._consumers)
