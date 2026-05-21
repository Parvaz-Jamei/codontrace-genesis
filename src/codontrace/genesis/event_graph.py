"""EventGraph: canonical event-association graph for GENESIS.

CausalGraph remains as a compatibility name in ``causal_graph``. EventGraph is
explicitly about temporal/predictive/interventional evidence levels, not proof
of causality.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError


def _digest(payload: Mapping[str, JsonValue]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class EventGraphEdge:
    source: str
    target: str
    lag: int
    evidence_count: int
    claim_level: str = "temporal_association"
    validation_digest: str | None = None
    digest: str = ""

    def __post_init__(self) -> None:
        if not self.source or not self.target:
            raise ConfigurationError("EventGraphEdge source/target must not be empty.")
        if self.lag < 0 or self.evidence_count < 0:
            raise ConfigurationError("EventGraphEdge lag/evidence_count must be non-negative.")
        computed = _digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("EventGraphEdge digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "source": self.source,
            "target": self.target,
            "lag": self.lag,
            "evidence_count": self.evidence_count,
            "claim_level": self.claim_level,
            "validation_digest": self.validation_digest,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


@dataclass(frozen=True, slots=True)
class EventGraph:
    edges: tuple[EventGraphEdge, ...] = ()
    graph_kind: str = "event_graph"
    claim_level: str = "temporal_association"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "graph_kind": self.graph_kind,
            "claim_level": self.claim_level,
            "edges": [
                edge.to_dict()
                for edge in sorted(self.edges, key=lambda e: (e.source, e.target, e.lag))
            ],
        }

    def digest(self) -> str:
        return _digest(self.to_dict())

    def add_edge(
        self,
        source: str,
        target: str,
        *,
        lag: int = 1,
        evidence_count: int = 1,
        claim_level: str = "temporal_association",
        validation_digest: str | None = None,
    ) -> EventGraph:
        edge = EventGraphEdge(source, target, lag, evidence_count, claim_level, validation_digest)
        return EventGraph((*self.edges, edge), self.graph_kind, self.claim_level)

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> EventGraph:
        raw = data.get("edges", [])
        if not isinstance(raw, list):
            raise ConfigurationError("EventGraph.edges must be a list.")
        edges = tuple(event_graph_edge_from_dict(item) for item in raw if isinstance(item, Mapping))
        return cls(
            edges=edges,
            graph_kind=str(data.get("graph_kind", "event_graph")),
            claim_level=str(data.get("claim_level", "temporal_association")),
        )


def event_graph_edge_from_dict(data: Mapping[str, JsonValue]) -> EventGraphEdge:
    edge = EventGraphEdge(
        source=_str(data, "source"),
        target=_str(data, "target"),
        lag=_int(data, "lag", 0),
        evidence_count=_int(data, "evidence_count", 0),
        claim_level=_str(data, "claim_level", "temporal_association"),
        validation_digest=None
        if data.get("validation_digest") is None
        else _str(data, "validation_digest"),
    )
    if edge.digest != data.get("digest"):
        raise ConfigurationError("EventGraphEdge digest mismatch.")
    return edge


def event_graph_from_causal_graph(graph: object) -> EventGraph:
    edges = []
    for edge in getattr(graph, "edges", ()):
        edges.append(
            EventGraphEdge(
                str(getattr(edge, "source", "")),
                str(getattr(edge, "target", "")),
                1,
                int(getattr(edge, "evidence_count", 1)),
                "temporal_association",
                None,
            )
        )
    return EventGraph(tuple(edges))


def _str(data: Mapping[str, JsonValue], key: str, default: str | None = None) -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        raise ConfigurationError(f"{key} must be a string.")
    return value


def _int(data: Mapping[str, JsonValue], key: str, default: int) -> int:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{key} must be an integer.")
    return value
