"""Runtime glue for GENESIS causal evidence and lightweight prediction.

These helpers connect organism trace/memory events to ``CausalGraph`` in an
ATP_learning-gated, deterministic way. They are intentionally lightweight:
this is not full causal discovery, not proof of causal intelligence, and not an
LLM-controlled simulation loop.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from codontrace._types import JsonValue, Position
from codontrace.genesis.atp import GenesisATPState
from codontrace.genesis.causal_graph import CausalGraph, CausalGraphConfig, CausalNode


@dataclass(frozen=True, slots=True)
class CausalUpdateInput:
    """Auditable input derived from one organism step/action result."""

    organism_id: str | None
    tick: int
    action: str
    action_status: str
    blocked_reason: str | None
    energy_delta: int | float | None
    resource_delta: int | float | None
    position_before: Position | None
    position_after: Position | None
    memory_event_id: str | None = None

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "organism_id": self.organism_id,
            "tick": self.tick,
            "action": self.action,
            "action_status": self.action_status,
            "blocked_reason": self.blocked_reason,
            "energy_delta": self.energy_delta,
            "resource_delta": self.resource_delta,
            "position_before": _position_to_json(self.position_before),
            "position_after": _position_to_json(self.position_after),
            "memory_event_id": self.memory_event_id,
        }


@dataclass(frozen=True, slots=True)
class CausalUpdateResult:
    """Result for one ATP_learning-gated runtime graph update."""

    attempted: bool
    success: bool
    cost_atp_learning: float
    digest_before: str | None
    digest_after: str | None
    reason: str | None = None
    learning_ledger_entry_id: int | None = None
    nodes_before: int = 0
    nodes_after: int = 0
    edges_before: int = 0
    edges_after: int = 0

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "attempted": self.attempted,
            "success": self.success,
            "cost_atp_learning": self.cost_atp_learning,
            "digest_before": self.digest_before,
            "digest_after": self.digest_after,
            "reason": self.reason,
            "learning_ledger_entry_id": self.learning_ledger_entry_id,
            "nodes_before": self.nodes_before,
            "nodes_after": self.nodes_after,
            "edges_before": self.edges_before,
            "edges_after": self.edges_after,
        }


@dataclass(frozen=True, slots=True)
class CausalPrediction:
    """Lightweight evidence/prediction record.

    This is a lightweight evidence/prediction helper, not full causal discovery
    and not proof of causal intelligence.
    """

    predicted_outcome: str | None
    confidence: float
    graph_digest: str | None
    used_edges: tuple[str, ...] = ()
    reason: str | None = None

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "predicted_outcome": self.predicted_outcome,
            "confidence": self.confidence,
            "graph_digest": self.graph_digest,
            "used_edges": [edge for edge in self.used_edges],
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class CausalPredictionEvaluation:
    """Audit result comparing a lightweight prediction with an observed outcome."""

    predicted: bool
    correct: bool | None
    expected: str | None
    observed: str | None
    confidence: float

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "predicted": self.predicted,
            "correct": self.correct,
            "expected": self.expected,
            "observed": self.observed,
            "confidence": self.confidence,
        }


def update_causal_graph_from_step(
    graph: CausalGraph | None,
    update_input: CausalUpdateInput,
    *,
    atp_learning_state: GenesisATPState | None = None,
    config: CausalGraphConfig | None = None,
) -> CausalUpdateResult:
    """Update ``graph`` from one step using explicit ATP_learning accounting.

    The function mutates only the provided graph, never global state. When
    ``graph`` is ``None`` it returns ``attempted=False`` so callers can keep
    causal learning opt-in and backward-compatible.
    """

    if graph is None:
        return CausalUpdateResult(False, False, 0.0, None, None, reason="causal_graph_absent")
    resolved_config = config or graph.config
    before = graph.digest()
    nodes_before = len(graph.nodes)
    edges_before = len(graph.edges)
    if not resolved_config.enabled:
        return CausalUpdateResult(
            True,
            False,
            0.0,
            before,
            before,
            reason="causal_graph_disabled",
            nodes_before=nodes_before,
            nodes_after=nodes_before,
            edges_before=edges_before,
            edges_after=edges_before,
        )
    cost = float(resolved_config.update_cost)
    if atp_learning_state is None:
        if cost > 0:
            return CausalUpdateResult(
                True,
                False,
                0.0,
                before,
                before,
                reason="insufficient_atp_learning",
                nodes_before=nodes_before,
                nodes_after=nodes_before,
                edges_before=edges_before,
                edges_after=edges_before,
            )
    elif not atp_learning_state.can_learn(cost):
        return CausalUpdateResult(
            True,
            False,
            0.0,
            before,
            before,
            reason="insufficient_atp_learning",
            nodes_before=nodes_before,
            nodes_after=nodes_before,
            edges_before=edges_before,
            edges_after=edges_before,
        )

    old_config = graph.config
    graph.config = resolved_config
    try:
        changed = _apply_step_evidence(graph, update_input)
    finally:
        graph.config = old_config
    if not changed:
        return CausalUpdateResult(
            True,
            False,
            0.0,
            before,
            before,
            reason="graph_limits_reached_or_no_evidence",
            nodes_before=nodes_before,
            nodes_after=len(graph.nodes),
            edges_before=edges_before,
            edges_after=len(graph.edges),
        )

    ledger_id = None
    if atp_learning_state is not None:
        ledger_id = atp_learning_state.debit_learning(
            cost,
            tick=update_input.tick,
            organism_id=update_input.organism_id or "organism",
            reason="causal_graph_step_update",
            event_ref=_digest(update_input.to_dict()),
        )
        if ledger_id is None and cost > 0:
            # Guarded by can_learn above; this branch keeps the audit honest if
            # a custom ATP state changes under the caller.
            return CausalUpdateResult(
                True,
                False,
                0.0,
                before,
                before,
                reason="insufficient_atp_learning",
                nodes_before=nodes_before,
                nodes_after=nodes_before,
                edges_before=edges_before,
                edges_after=edges_before,
            )

    return CausalUpdateResult(
        True,
        True,
        cost,
        before,
        graph.digest(),
        reason=None,
        learning_ledger_entry_id=ledger_id,
        nodes_before=nodes_before,
        nodes_after=len(graph.nodes),
        edges_before=edges_before,
        edges_after=len(graph.edges),
    )


def predict_next_outcome(
    graph: CausalGraph | None, action: str, context: object | None = None
) -> CausalPrediction:
    """Return a deterministic lightweight prediction for ``action``.

    This helper reads existing ``predicts_local`` edges. It is not causal
    discovery and should be interpreted as evidence reuse only.
    """

    if graph is None:
        return CausalPrediction(None, 0.0, None, reason="causal_graph_absent")
    digest = graph.digest()
    action_id = _node_id("action", action)
    candidates = [
        edge
        for edge in graph.edges
        if edge.source == action_id and edge.relation == "predicts_local"
    ]
    if not candidates:
        return CausalPrediction(None, 0.0, digest, reason="no_matching_edges")
    total = sum(max(0.0, float(edge.weight)) for edge in candidates) or float(len(candidates))
    best = sorted(candidates, key=lambda edge: (-edge.weight, edge.target, edge.edge_id))[0]
    confidence = round(max(0.0, min(1.0, float(best.weight) / total)), 10)
    return CausalPrediction(
        predicted_outcome=_label_from_node_id(best.target),
        confidence=confidence,
        graph_digest=digest,
        used_edges=(best.edge_id,),
        reason=None,
    )


def evaluate_prediction(
    prediction: CausalPrediction, observed_outcome: str
) -> CausalPredictionEvaluation:
    """Compare a lightweight prediction with the observed outcome."""

    predicted = prediction.predicted_outcome is not None
    return CausalPredictionEvaluation(
        predicted=predicted,
        correct=(prediction.predicted_outcome == observed_outcome) if predicted else None,
        expected=prediction.predicted_outcome,
        observed=observed_outcome,
        confidence=prediction.confidence,
    )


def _apply_step_evidence(graph: CausalGraph, update_input: CausalUpdateInput) -> bool:
    changed = False
    evidence_ref = _digest(update_input.to_dict())
    action_id = _node_id("action", update_input.action)
    outcome_id = _node_id("outcome", update_input.action_status)
    changed |= graph.add_node(CausalNode(action_id, "action", update_input.action))
    changed |= graph.add_node(CausalNode(outcome_id, "outcome", update_input.action_status))
    changed |= graph.add_or_update_edge(
        action_id,
        outcome_id,
        "predicts_local",
        tick=update_input.tick,
        evidence_ref=evidence_ref,
        metadata={"organism_id": update_input.organism_id or ""},
    )
    if update_input.blocked_reason:
        reason_id = _node_id("blocked_reason", update_input.blocked_reason)
        changed |= graph.add_node(
            CausalNode(reason_id, "blocked_reason", update_input.blocked_reason)
        )
        changed |= graph.add_or_update_edge(
            action_id,
            reason_id,
            "leads_to_block",
            tick=update_input.tick,
            evidence_ref=evidence_ref,
        )
    if update_input.resource_delta is not None and float(update_input.resource_delta) > 0:
        resource_id = "resource:lumen"
        changed |= graph.add_node(CausalNode(resource_id, "resource", "Lumen"))
        changed |= graph.add_or_update_edge(
            action_id,
            resource_id,
            "leads_to_resource_gain",
            tick=update_input.tick,
            evidence_ref=evidence_ref,
        )
    if update_input.energy_delta is not None and float(update_input.energy_delta) < 0:
        atp_id = "atp_runtime:debit"
        changed |= graph.add_node(CausalNode(atp_id, "atp_runtime", "runtime debit"))
        changed |= graph.add_or_update_edge(
            action_id,
            atp_id,
            "consumes_runtime_atp",
            tick=update_input.tick,
            evidence_ref=evidence_ref,
        )
    if update_input.memory_event_id:
        memory_id = "memory:write"
        changed |= graph.add_node(CausalNode(memory_id, "memory", "memory write"))
        changed |= graph.add_or_update_edge(
            action_id,
            memory_id,
            "leads_to_memory_write",
            tick=update_input.tick,
            evidence_ref=update_input.memory_event_id,
        )
    if (
        update_input.position_before is not None
        and update_input.position_after is not None
        and update_input.position_before != update_input.position_after
    ):
        position_id = _node_id(
            "position", f"{update_input.position_after[0]},{update_input.position_after[1]}"
        )
        changed |= graph.add_node(
            CausalNode(
                position_id,
                "position",
                f"{update_input.position_after[0]},{update_input.position_after[1]}",
            )
        )
        changed |= graph.add_or_update_edge(
            action_id,
            position_id,
            "precedes",
            tick=update_input.tick,
            evidence_ref=evidence_ref,
        )
    return changed


def _node_id(kind: str, label: str) -> str:
    clean = str(label).replace(" ", "_").replace(";", "_") or "unknown"
    return f"{kind}:{clean}"


def _label_from_node_id(node_id: str) -> str:
    if ":" not in node_id:
        return node_id
    return node_id.split(":", 1)[1]


def _position_to_json(position: Position | None) -> JsonValue:
    return None if position is None else [position[0], position[1]]


def _digest(payload: dict[str, JsonValue] | tuple[Any, ...]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
