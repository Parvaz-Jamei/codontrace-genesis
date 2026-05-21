"""Legacy CausalGraph compatibility wrapper for event association evidence.

EventGraph is the canonical name for new code. CausalGraph remains for at least
one minor alpha cycle and serializes claim_level="temporal_association".

Small local causal evidence graph scaffold for GENESIS experiments.

This module stores deterministic event-based evidence from TraceEvent and
EpisodicMemory objects. It is intentionally not Pearl-grade causality, not a
statistical causal-discovery algorithm, and not a discovery detector.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import cast

from codontrace._types import JsonValue
from codontrace.genesis.atp import GenesisATPState
from codontrace.genesis.memory import EpisodicEvent, EpisodicMemory
from codontrace.genesis.status import ActionStatusRegistry
from codontrace.trace import Trace, TraceEvent

_ALLOWED_NODE_KINDS = {
    "action",
    "observation",
    "outcome",
    "resource",
    "atp_runtime",
    "atp_learning",
    "memory",
    "reproduction",
    "position",
    "blocked_reason",
    "outcome_detail",
}
_ALLOWED_RELATIONS = {
    "precedes",
    "co_occurs",
    "predicts_local",
    "consumes_runtime_atp",
    "consumes_learning_atp",
    "leads_to_block",
    "leads_to_resource_gain",
    "leads_to_memory_write",
    "leads_to_reproduction_attempt",
    "leads_to_reproduction_success",
    "has_outcome_detail",
}


@dataclass(frozen=True, slots=True)
class CausalNode:
    """One local evidence node in the causal scaffold."""

    node_id: str
    kind: str
    label: str
    metadata: dict[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.node_id:
            msg = "CausalNode.node_id must not be empty."
            raise ValueError(msg)
        if self.kind not in _ALLOWED_NODE_KINDS:
            msg = f"Unsupported CausalNode kind {self.kind!r}."
            raise ValueError(msg)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "node_id": self.node_id,
            "kind": self.kind,
            "label": self.label,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> CausalNode:
        metadata = data.get("metadata", {})
        if not isinstance(metadata, dict):
            msg = "CausalNode.metadata must be an object."
            raise ValueError(msg)
        return cls(
            node_id=_str(data, "node_id"),
            kind=_str(data, "kind"),
            label=_str(data, "label"),
            metadata={str(key): value for key, value in metadata.items()},
        )


@dataclass(frozen=True, slots=True)
class CausalEdge:
    """One deterministic evidence edge between local evidence nodes."""

    source: str
    target: str
    relation: str
    weight: float
    evidence_count: int
    first_tick: int
    last_tick: int
    evidence_refs: tuple[str, ...]
    metadata: dict[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.source or not self.target:
            msg = "CausalEdge source and target must not be empty."
            raise ValueError(msg)
        if self.relation not in _ALLOWED_RELATIONS:
            msg = f"Unsupported CausalEdge relation {self.relation!r}."
            raise ValueError(msg)
        if self.weight < 0 or self.evidence_count < 0:
            msg = "CausalEdge weight/evidence_count cannot be negative."
            raise ValueError(msg)
        if self.first_tick < 0 or self.last_tick < 0:
            msg = "CausalEdge ticks must be non-negative."
            raise ValueError(msg)

    @property
    def edge_id(self) -> str:
        return f"{self.source}|{self.relation}|{self.target}"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "source": self.source,
            "target": self.target,
            "relation": self.relation,
            "weight": self.weight,
            "evidence_count": self.evidence_count,
            "first_tick": self.first_tick,
            "last_tick": self.last_tick,
            "evidence_refs": [ref for ref in self.evidence_refs],
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> CausalEdge:
        metadata = data.get("metadata", {})
        refs = data.get("evidence_refs", [])
        if not isinstance(metadata, dict):
            msg = "CausalEdge.metadata must be an object."
            raise ValueError(msg)
        if not isinstance(refs, list) or not all(isinstance(item, str) for item in refs):
            msg = "CausalEdge.evidence_refs must be a list of strings."
            raise ValueError(msg)
        return cls(
            source=_str(data, "source"),
            target=_str(data, "target"),
            relation=_str(data, "relation"),
            weight=_float(data, "weight", 0.0),
            evidence_count=_int(data, "evidence_count", 0),
            first_tick=_int(data, "first_tick", 0),
            last_tick=_int(data, "last_tick", 0),
            evidence_refs=tuple(cast(list[str], refs)),
            metadata={str(key): value for key, value in metadata.items()},
        )


@dataclass(frozen=True, slots=True)
class CausalGraphConfig:
    """Limits and ATP_learning cost for local graph updates.

    ``decay`` and ``allow_negative_evidence`` are reserved, explicit no-op
    compatibility fields. They are kept for later evidence weighting
    experiments but do not change update behavior yet.
    """

    enabled: bool = True
    max_nodes: int = 256
    max_edges: int = 1024
    max_evidence_refs_per_edge: int = 16
    min_edge_weight: float = 0.0
    update_cost: float = 0.5
    decay: float = 0.0
    allow_negative_evidence: bool = False
    status_registry: ActionStatusRegistry = field(default_factory=ActionStatusRegistry.genesis_v0)

    def __post_init__(self) -> None:
        if self.max_nodes <= 0 or self.max_edges <= 0:
            msg = "CausalGraphConfig max_nodes/max_edges must be > 0."
            raise ValueError(msg)
        if self.max_evidence_refs_per_edge <= 0:
            msg = "max_evidence_refs_per_edge must be > 0."
            raise ValueError(msg)
        for value, name in (
            (self.min_edge_weight, "min_edge_weight"),
            (self.update_cost, "update_cost"),
            (self.decay, "decay"),
        ):
            if value < 0:
                msg = f"{name} must be >= 0."
                raise ValueError(msg)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "enabled": self.enabled,
            "max_nodes": self.max_nodes,
            "max_edges": self.max_edges,
            "max_evidence_refs_per_edge": self.max_evidence_refs_per_edge,
            "min_edge_weight": self.min_edge_weight,
            "update_cost": self.update_cost,
            "decay": self.decay,
            "allow_negative_evidence": self.allow_negative_evidence,
            "status_registry": self.status_registry.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> CausalGraphConfig:
        raw_status_registry = data.get("status_registry")
        return cls(
            enabled=_bool(data, "enabled", True),
            max_nodes=_int(data, "max_nodes", 256),
            max_edges=_int(data, "max_edges", 1024),
            max_evidence_refs_per_edge=_int(data, "max_evidence_refs_per_edge", 16),
            min_edge_weight=_float(data, "min_edge_weight", 0.0),
            update_cost=_float(data, "update_cost", 0.5),
            decay=_float(data, "decay", 0.0),
            allow_negative_evidence=_bool(data, "allow_negative_evidence", False),
            status_registry=(
                ActionStatusRegistry.from_dict(raw_status_registry)
                if isinstance(raw_status_registry, dict)
                else ActionStatusRegistry.genesis_v0()
            ),
        )


@dataclass(frozen=True, slots=True)
class CausalGraphUpdateResult:
    """Audit result for one ATP_learning-gated graph update."""

    attempted: bool
    succeeded: bool
    blocked_reason: str | None
    consumed_learning_atp: float
    learning_ledger_entry_id: int | None
    nodes_before: int
    nodes_after: int
    edges_before: int
    edges_after: int
    graph_digest_before: str
    graph_digest_after: str
    evidence_events: int
    truncated: bool = False
    dropped_nodes: int = 0
    dropped_edges: int = 0
    dropped_evidence_events: int = 0
    limit_reason: str | None = None

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "attempted": self.attempted,
            "succeeded": self.succeeded,
            "blocked_reason": self.blocked_reason,
            "consumed_learning_atp": self.consumed_learning_atp,
            "learning_ledger_entry_id": self.learning_ledger_entry_id,
            "nodes_before": self.nodes_before,
            "nodes_after": self.nodes_after,
            "edges_before": self.edges_before,
            "edges_after": self.edges_after,
            "graph_digest_before": self.graph_digest_before,
            "graph_digest_after": self.graph_digest_after,
            "evidence_events": self.evidence_events,
            "truncated": self.truncated,
            "dropped_nodes": self.dropped_nodes,
            "dropped_edges": self.dropped_edges,
            "dropped_evidence_events": self.dropped_evidence_events,
            "limit_reason": self.limit_reason,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> CausalGraphUpdateResult:
        ledger = data.get("learning_ledger_entry_id")
        blocked = data.get("blocked_reason")
        limit_reason = data.get("limit_reason")
        if ledger is not None and (isinstance(ledger, bool) or not isinstance(ledger, int)):
            msg = "learning_ledger_entry_id must be an integer or null."
            raise ValueError(msg)
        if blocked is not None and not isinstance(blocked, str):
            msg = "blocked_reason must be a string or null."
            raise ValueError(msg)
        if limit_reason is not None and not isinstance(limit_reason, str):
            msg = "limit_reason must be a string or null."
            raise ValueError(msg)
        return cls(
            attempted=_bool(data, "attempted", False),
            succeeded=_bool(data, "succeeded", False),
            blocked_reason=blocked,
            consumed_learning_atp=_float(data, "consumed_learning_atp", 0.0),
            learning_ledger_entry_id=ledger,
            nodes_before=_int(data, "nodes_before", 0),
            nodes_after=_int(data, "nodes_after", 0),
            edges_before=_int(data, "edges_before", 0),
            edges_after=_int(data, "edges_after", 0),
            graph_digest_before=_str(data, "graph_digest_before"),
            graph_digest_after=_str(data, "graph_digest_after"),
            evidence_events=_int(data, "evidence_events", 0),
            truncated=_bool(data, "truncated", False),
            dropped_nodes=_int(data, "dropped_nodes", 0),
            dropped_edges=_int(data, "dropped_edges", 0),
            dropped_evidence_events=_int(data, "dropped_evidence_events", 0),
            limit_reason=limit_reason,
        )


@dataclass(slots=True)
class CausalGraph:
    """Dependency-free local causal evidence graph.

    Edge weight is the deterministic evidence count. This is an auditable local
    scaffold; it does not prove causality or perform statistical discovery.
    """

    config: CausalGraphConfig = field(default_factory=CausalGraphConfig)
    _nodes: dict[str, CausalNode] = field(default_factory=dict, init=False, repr=False)
    _edges: dict[str, CausalEdge] = field(default_factory=dict, init=False, repr=False)
    _dropped_nodes: int = field(default=0, init=False, repr=False)
    _dropped_edges: int = field(default=0, init=False, repr=False)

    @property
    def nodes(self) -> tuple[CausalNode, ...]:
        return tuple(self._nodes[key] for key in sorted(self._nodes))

    @property
    def edges(self) -> tuple[CausalEdge, ...]:
        return tuple(self._edges[key] for key in sorted(self._edges))

    def add_node(self, node: CausalNode) -> bool:
        if node.node_id in self._nodes:
            existing = self._nodes[node.node_id]
            merged_metadata = {**existing.metadata, **node.metadata}
            self._nodes[node.node_id] = replace(existing, metadata=merged_metadata)
            return True
        if len(self._nodes) >= self.config.max_nodes:
            self._dropped_nodes += 1
            return False
        self._nodes[node.node_id] = node
        return True

    def add_or_update_edge(
        self,
        source: str,
        target: str,
        relation: str,
        *,
        tick: int,
        evidence_ref: str,
        metadata: Mapping[str, JsonValue] | None = None,
    ) -> bool:
        if relation not in _ALLOWED_RELATIONS:
            msg = f"Unsupported CausalEdge relation {relation!r}."
            raise ValueError(msg)
        if source not in self._nodes or target not in self._nodes:
            return False
        edge_id = f"{source}|{relation}|{target}"
        if edge_id not in self._edges and len(self._edges) >= self.config.max_edges:
            self._dropped_edges += 1
            return False
        if edge_id in self._edges:
            existing = self._edges[edge_id]
            refs = tuple(
                list(existing.evidence_refs)
                + ([] if evidence_ref in existing.evidence_refs else [evidence_ref])
            )[: self.config.max_evidence_refs_per_edge]
            updated = replace(
                existing,
                evidence_count=existing.evidence_count + 1,
                weight=float(round(existing.evidence_count + 1, 10)),
                last_tick=max(existing.last_tick, tick),
                evidence_refs=refs,
                metadata={**existing.metadata, **dict(metadata or {})},
            )
            if updated.weight >= self.config.min_edge_weight:
                self._edges[edge_id] = updated
            return True
        edge = CausalEdge(
            source=source,
            target=target,
            relation=relation,
            weight=1.0,
            evidence_count=1,
            first_tick=tick,
            last_tick=tick,
            evidence_refs=(evidence_ref,),
            metadata=dict(metadata or {}),
        )
        if edge.weight >= self.config.min_edge_weight:
            self._edges[edge_id] = edge
        return True

    def update_from_trace(
        self,
        trace: Trace | Sequence[TraceEvent],
        atp_state: GenesisATPState,
        config: CausalGraphConfig | None = None,
        *,
        tick: int,
        organism_id: str,
    ) -> CausalGraphUpdateResult:
        return update_causal_graph_from_trace(
            self, trace, atp_state, config or self.config, tick=tick, organism_id=organism_id
        )

    def update_from_memory(
        self,
        memory: EpisodicMemory,
        atp_state: GenesisATPState,
        config: CausalGraphConfig | None = None,
        *,
        tick: int,
        organism_id: str,
    ) -> CausalGraphUpdateResult:
        return update_causal_graph_from_memory(
            self, memory, atp_state, config or self.config, tick=tick, organism_id=organism_id
        )

    def neighbors(self, node_id: str) -> tuple[CausalNode, ...]:
        neighbor_ids = {edge.target for edge in self._edges.values() if edge.source == node_id} | {
            edge.source for edge in self._edges.values() if edge.target == node_id
        }
        return tuple(self._nodes[item] for item in sorted(neighbor_ids) if item in self._nodes)

    def edges_for_relation(self, relation: str) -> tuple[CausalEdge, ...]:
        return tuple(edge for edge in self.edges if edge.relation == relation)

    def digest(self) -> str:
        return _digest(self.to_dict())

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "graph_kind": "causal_graph_compatibility_alias",
            "claim_level": "temporal_association",
            "config": self.config.to_dict(),
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> CausalGraph:
        config_raw = data.get("config", {})
        graph = cls(
            config=CausalGraphConfig.from_dict(config_raw)
            if isinstance(config_raw, Mapping)
            else CausalGraphConfig()
        )
        nodes = data.get("nodes", [])
        edges = data.get("edges", [])
        if not isinstance(nodes, list) or not isinstance(edges, list):
            msg = "CausalGraph nodes/edges must be lists."
            raise ValueError(msg)
        for item in nodes:
            if isinstance(item, Mapping):
                node = CausalNode.from_dict(item)
                graph._nodes[node.node_id] = node
        for item in edges:
            if isinstance(item, Mapping):
                edge = CausalEdge.from_dict(item)
                graph._edges[edge.edge_id] = edge
        return graph


def update_causal_graph_from_trace(
    graph: CausalGraph,
    trace: Trace | Sequence[TraceEvent],
    atp_state: GenesisATPState,
    config: CausalGraphConfig,
    *,
    tick: int,
    organism_id: str,
) -> CausalGraphUpdateResult:
    """Update graph from TraceEvent evidence using ATP_learning only."""

    events = tuple(trace.events if isinstance(trace, Trace) else trace)
    return _gated_update(
        graph,
        atp_state,
        config,
        tick=tick,
        organism_id=organism_id,
        evidence_events=len(events),
        apply=lambda: _apply_trace_events(graph, events, config.status_registry),
    )


def update_causal_graph_from_memory(
    graph: CausalGraph,
    memory: EpisodicMemory,
    atp_state: GenesisATPState,
    config: CausalGraphConfig,
    *,
    tick: int,
    organism_id: str,
) -> CausalGraphUpdateResult:
    """Update graph from immutable memory event snapshots using ATP_learning only."""

    events = tuple(memory.events)
    return _gated_update(
        graph,
        atp_state,
        config,
        tick=tick,
        organism_id=organism_id,
        evidence_events=len(events),
        apply=lambda: _apply_memory_events(graph, events, config.status_registry),
    )


def _gated_update(
    graph: CausalGraph,
    atp_state: GenesisATPState,
    config: CausalGraphConfig,
    *,
    tick: int,
    organism_id: str,
    evidence_events: int,
    apply: Callable[[], bool],
) -> CausalGraphUpdateResult:
    nodes_before = len(graph._nodes)
    edges_before = len(graph._edges)
    before_digest = graph.digest()
    if not config.enabled:
        return _blocked_result(
            "causal_graph_disabled", nodes_before, edges_before, before_digest, evidence_events
        )
    if evidence_events == 0:
        return _blocked_result("no_evidence", nodes_before, edges_before, before_digest, 0)
    if not atp_state.can_learn(config.update_cost):
        return _blocked_result(
            "insufficient_learning_atp", nodes_before, edges_before, before_digest, evidence_events
        )
    old_config = graph.config
    graph.config = config
    graph._dropped_nodes = 0
    graph._dropped_edges = 0
    try:
        changed = apply()
    finally:
        graph.config = old_config
    dropped_nodes = graph._dropped_nodes
    dropped_edges = graph._dropped_edges
    truncated = dropped_nodes > 0 or dropped_edges > 0
    limit_reason = (
        "max_nodes_reached"
        if dropped_nodes > 0 and dropped_edges == 0
        else "max_edges_reached"
        if dropped_edges > 0 and dropped_nodes == 0
        else "graph_limits_reached"
        if truncated
        else None
    )
    if not changed:
        result = _blocked_result(
            "graph_limits_reached", nodes_before, edges_before, before_digest, evidence_events
        )
        return replace(
            result,
            truncated=truncated,
            dropped_nodes=dropped_nodes,
            dropped_edges=dropped_edges,
            dropped_evidence_events=evidence_events if truncated else 0,
            limit_reason=limit_reason,
        )
    ledger_id = atp_state.debit_learning(
        config.update_cost,
        tick=tick,
        organism_id=organism_id,
        reason="causal_graph_update",
        event_ref=before_digest,
    )
    if ledger_id is None and config.update_cost > 0:
        # The pre-check should prevent this; keep the result honest without
        # rolling back the graph because ATPAccount can only fail on races that
        # do not exist in this single-threaded library path.
        return _blocked_result(
            "insufficient_learning_atp", nodes_before, edges_before, before_digest, evidence_events
        )
    return CausalGraphUpdateResult(
        attempted=True,
        succeeded=True,
        blocked_reason=None,
        consumed_learning_atp=config.update_cost,
        learning_ledger_entry_id=ledger_id,
        nodes_before=nodes_before,
        nodes_after=len(graph._nodes),
        edges_before=edges_before,
        edges_after=len(graph._edges),
        graph_digest_before=before_digest,
        graph_digest_after=graph.digest(),
        evidence_events=evidence_events,
        truncated=truncated,
        dropped_nodes=dropped_nodes,
        dropped_edges=dropped_edges,
        dropped_evidence_events=evidence_events if truncated else 0,
        limit_reason=limit_reason,
    )


def _blocked_result(
    reason: str,
    nodes_before: int,
    edges_before: int,
    digest: str,
    evidence_events: int,
) -> CausalGraphUpdateResult:
    return CausalGraphUpdateResult(
        attempted=True,
        succeeded=False,
        blocked_reason=reason,
        consumed_learning_atp=0.0,
        learning_ledger_entry_id=None,
        nodes_before=nodes_before,
        nodes_after=nodes_before,
        edges_before=edges_before,
        edges_after=edges_before,
        graph_digest_before=digest,
        graph_digest_after=digest,
        evidence_events=evidence_events,
        truncated=False,
        dropped_nodes=0,
        dropped_edges=0,
        dropped_evidence_events=0,
        limit_reason=None,
    )


def _apply_trace_events(
    graph: CausalGraph, events: Sequence[TraceEvent], status_registry: ActionStatusRegistry
) -> bool:
    changed = False
    for event in events:
        ref = _trace_event_digest(event)
        action_id = _node_id("action", event.action)
        outcome_id = _node_id("outcome", event.status)
        changed |= graph.add_node(CausalNode(action_id, "action", event.action))
        changed |= graph.add_node(CausalNode(outcome_id, "outcome", event.status))
        changed |= graph.add_or_update_edge(
            action_id, outcome_id, "predicts_local", tick=event.step, evidence_ref=ref
        )
        if event.atp_before > event.atp_after:
            atp_id = "atp_runtime:debit"
            changed |= graph.add_node(CausalNode(atp_id, "atp_runtime", "runtime debit"))
            changed |= graph.add_or_update_edge(
                action_id,
                atp_id,
                "consumes_runtime_atp",
                tick=event.step,
                evidence_ref=ref,
            )
        is_blocked = (
            status_registry.counts_as_blocked(event.status)
            or event.world_delta.get("blocked") is True
        )
        if is_blocked:
            reason_id = _node_id("blocked_reason", event.reason or event.status)
            changed |= graph.add_node(
                CausalNode(reason_id, "blocked_reason", event.reason or event.status)
            )
            changed |= graph.add_or_update_edge(
                action_id, reason_id, "leads_to_block", tick=event.step, evidence_ref=ref
            )
        elif event.reason:
            detail_id = _node_id("outcome_detail", event.reason)
            changed |= graph.add_node(CausalNode(detail_id, "outcome_detail", event.reason))
            changed |= graph.add_or_update_edge(
                action_id, detail_id, "has_outcome_detail", tick=event.step, evidence_ref=ref
            )
        if event.world_delta.get("lumen_interaction") is True:
            resource_id = "resource:lumen"
            changed |= graph.add_node(CausalNode(resource_id, "resource", "Lumen"))
            changed |= graph.add_or_update_edge(
                action_id,
                resource_id,
                "leads_to_resource_gain",
                tick=event.step,
                evidence_ref=ref,
            )
        if event.world_delta.get("memory_write_succeeded") is True:
            memory_id = "memory:write"
            changed |= graph.add_node(CausalNode(memory_id, "memory", "memory write"))
            changed |= graph.add_or_update_edge(
                action_id,
                memory_id,
                "leads_to_memory_write",
                tick=event.step,
                evidence_ref=ref,
            )
        if event.world_delta.get("reproduction_attempted") is True:
            attempt_id = "reproduction:attempt"
            changed |= graph.add_node(
                CausalNode(attempt_id, "reproduction", "reproduction attempt")
            )
            changed |= graph.add_or_update_edge(
                action_id,
                attempt_id,
                "leads_to_reproduction_attempt",
                tick=event.step,
                evidence_ref=ref,
            )
            if event.world_delta.get("reproduction_succeeded") is True:
                success_id = "reproduction:success"
                changed |= graph.add_node(
                    CausalNode(success_id, "reproduction", "reproduction success")
                )
                changed |= graph.add_or_update_edge(
                    attempt_id,
                    success_id,
                    "leads_to_reproduction_success",
                    tick=event.step,
                    evidence_ref=ref,
                )
            else:
                block_id = _node_id(
                    "blocked_reason",
                    str(
                        event.world_delta.get("reproduction_blocked_reason")
                        or "reproduction_blocked"
                    ),
                )
                changed |= graph.add_node(
                    CausalNode(block_id, "blocked_reason", "reproduction blocked")
                )
                changed |= graph.add_or_update_edge(
                    attempt_id, block_id, "leads_to_block", tick=event.step, evidence_ref=ref
                )
    return changed


def _apply_memory_events(
    graph: CausalGraph, events: Sequence[EpisodicEvent], status_registry: ActionStatusRegistry
) -> bool:
    changed = False
    for event in events:
        ref = event.trace_event_digest or event.digest()
        action_id = _node_id("action", event.action)
        outcome_id = _node_id("outcome", event.status)
        changed |= graph.add_node(CausalNode(action_id, "action", event.action))
        changed |= graph.add_node(CausalNode(outcome_id, "outcome", event.status))
        changed |= graph.add_or_update_edge(
            action_id, outcome_id, "predicts_local", tick=event.tick, evidence_ref=ref
        )
        if event.atp_learning_before > event.atp_learning_after:
            learning_id = "atp_learning:debit"
            changed |= graph.add_node(CausalNode(learning_id, "atp_learning", "learning debit"))
            changed |= graph.add_or_update_edge(
                action_id,
                learning_id,
                "consumes_learning_atp",
                tick=event.tick,
                evidence_ref=ref,
            )
        reason = event.outcome.get("reason")
        if isinstance(reason, str) and reason:
            if status_registry.counts_as_blocked(event.status):
                reason_id = _node_id("blocked_reason", reason)
                changed |= graph.add_node(CausalNode(reason_id, "blocked_reason", reason))
                changed |= graph.add_or_update_edge(
                    action_id, reason_id, "leads_to_block", tick=event.tick, evidence_ref=ref
                )
            else:
                detail_id = _node_id("outcome_detail", reason)
                changed |= graph.add_node(CausalNode(detail_id, "outcome_detail", reason))
                changed |= graph.add_or_update_edge(
                    action_id, detail_id, "has_outcome_detail", tick=event.tick, evidence_ref=ref
                )
    return changed


def _node_id(kind: str, label: str) -> str:
    clean = label.replace(" ", "_").replace(";", "_") or "unknown"
    return f"{kind}:{clean}"


def _trace_event_digest(event: TraceEvent) -> str:
    return _digest(event.to_dict())


def _digest(payload: Mapping[str, JsonValue]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _str(data: Mapping[str, JsonValue], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        msg = f"{key} must be a string."
        raise ValueError(msg)
    return value


def _bool(data: Mapping[str, JsonValue], key: str, default: bool) -> bool:
    value = data.get(key, default)
    if not isinstance(value, bool):
        msg = f"{key} must be a boolean."
        raise ValueError(msg)
    return value


def _int(data: Mapping[str, JsonValue], key: str, default: int) -> int:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{key} must be an integer."
        raise ValueError(msg)
    return value


def _float(data: Mapping[str, JsonValue], key: str, default: float) -> float:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int | float):
        msg = f"{key} must be numeric."
        raise ValueError(msg)
    return float(value)
