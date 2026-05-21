"""Bounded GENESIS learning ATP decisions and consolidation scaffolds.

This module intentionally does not implement CausalGraph, causal discovery,
ADF, or discovery detection. It only accounts for whether ATP_learning is
available for memory/consolidation-style updates in controlled library runs.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import cast

from codontrace._types import JsonValue
from codontrace.genesis.atp import GenesisATPState
from codontrace.genesis.memory import EpisodicEvent, MemoryWriteResult
from codontrace._numeric import finite_float, finite_json_dumps


@dataclass(frozen=True, slots=True)
class LearningATPConfig:
    """Costs and policy for ATP_learning-backed memory work."""

    learning_enabled: bool = True
    memory_write_cost: float = 0.1
    memory_consolidation_cost: float = 0.5
    prediction_update_cost: float = 1.0
    vitae_to_learning_rate: float = 1.0
    min_vitae_reserve: float = 0.0
    allow_runtime_to_learning_ablation: bool = False

    def __post_init__(self) -> None:
        for field_name in (
            "memory_write_cost",
            "memory_consolidation_cost",
            "prediction_update_cost",
            "min_vitae_reserve",
        ):
            object.__setattr__(
                self, field_name, finite_float(field_name, getattr(self, field_name), non_negative=True)
            )
        object.__setattr__(
            self, "vitae_to_learning_rate", finite_float("vitae_to_learning_rate", self.vitae_to_learning_rate)
        )
        if self.vitae_to_learning_rate <= 0:
            msg = "vitae_to_learning_rate must be > 0."
            raise ValueError(msg)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "learning_enabled": self.learning_enabled,
            "memory_write_cost": self.memory_write_cost,
            "memory_consolidation_cost": self.memory_consolidation_cost,
            "prediction_update_cost": self.prediction_update_cost,
            "vitae_to_learning_rate": self.vitae_to_learning_rate,
            "min_vitae_reserve": self.min_vitae_reserve,
            "allow_runtime_to_learning_ablation": self.allow_runtime_to_learning_ablation,
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> LearningATPConfig:
        return cls(
            learning_enabled=_bool(data, "learning_enabled", True),
            memory_write_cost=_float(data, "memory_write_cost", 0.1),
            memory_consolidation_cost=_float(data, "memory_consolidation_cost", 0.5),
            prediction_update_cost=_float(data, "prediction_update_cost", 1.0),
            vitae_to_learning_rate=_float(data, "vitae_to_learning_rate", 1.0),
            min_vitae_reserve=_float(data, "min_vitae_reserve", 0.0),
            allow_runtime_to_learning_ablation=_bool(
                data, "allow_runtime_to_learning_ablation", False
            ),
        )


@dataclass(frozen=True, slots=True)
class LearningUpdateDecision:
    """Decision-only object for future learning updates.

    This does not build a CausalGraph and does not infer causality.
    """

    should_update: bool
    reasons: tuple[str, ...]
    prediction_error: float
    threshold: float
    learning_cost: float
    learning_atp_available: float

    def __post_init__(self) -> None:
        for field_name in ("prediction_error", "threshold", "learning_cost", "learning_atp_available"):
            object.__setattr__(self, field_name, finite_float(f"LearningUpdateDecision.{field_name}", getattr(self, field_name)))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "should_update": self.should_update,
            "reasons": [reason for reason in self.reasons],
            "prediction_error": self.prediction_error,
            "threshold": self.threshold,
            "learning_cost": self.learning_cost,
            "learning_atp_available": self.learning_atp_available,
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> LearningUpdateDecision:
        reasons = data.get("reasons", [])
        if not isinstance(reasons, list) or not all(isinstance(item, str) for item in reasons):
            msg = "LearningUpdateDecision.reasons must be a list of strings."
            raise ValueError(msg)
        return cls(
            should_update=_bool(data, "should_update", False),
            reasons=tuple(str(item) for item in reasons),
            prediction_error=_float(data, "prediction_error", 0.0),
            threshold=_float(data, "threshold", 0.0),
            learning_cost=_float(data, "learning_cost", 0.0),
            learning_atp_available=_float(data, "learning_atp_available", 0.0),
        )


@dataclass(frozen=True, slots=True)
class MemoryConsolidationResult:
    """Result of a bounded memory summary/consolidation attempt."""

    attempted: bool
    succeeded: bool
    decision: LearningUpdateDecision
    consumed_learning_atp: float
    ledger_entry_id: int | None
    memory_digest_before: str
    memory_digest_after: str
    summary: dict[str, JsonValue]
    state_changed: bool = False
    mode: str = "audit_summary_only"
    claim_allowed_for_learning_compression: bool = False
    evicted_count: int = 0
    evicted_event_digests: tuple[str, ...] = ()
    consolidation_event_digest: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "consumed_learning_atp", finite_float("MemoryConsolidationResult.consumed_learning_atp", self.consumed_learning_atp, non_negative=True))
        if self.evicted_count < 0:
            msg = "MemoryConsolidationResult.evicted_count must be non-negative."
            raise ValueError(msg)
        object.__setattr__(self, "evicted_event_digests", tuple(str(x) for x in self.evicted_event_digests))
        if self.evicted_count != len(self.evicted_event_digests):
            object.__setattr__(self, "evicted_count", len(self.evicted_event_digests))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "attempted": self.attempted,
            "succeeded": self.succeeded,
            "decision": self.decision.to_dict(),
            "consumed_learning_atp": self.consumed_learning_atp,
            "ledger_entry_id": self.ledger_entry_id,
            "memory_digest_before": self.memory_digest_before,
            "memory_digest_after": self.memory_digest_after,
            "summary": dict(self.summary),
            "state_changed": self.state_changed,
            "mode": self.mode,
            "claim_allowed_for_learning_compression": self.claim_allowed_for_learning_compression,
            "evicted_count": self.evicted_count,
            "evicted_event_digests": list(self.evicted_event_digests),
            "consolidation_event_digest": self.consolidation_event_digest,
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> MemoryConsolidationResult:
        decision_raw = data.get("decision")
        summary_raw = data.get("summary", {})
        if not isinstance(decision_raw, dict):
            msg = "MemoryConsolidationResult.decision must be an object."
            raise ValueError(msg)
        if not isinstance(summary_raw, dict):
            msg = "MemoryConsolidationResult.summary must be an object."
            raise ValueError(msg)
        ledger = data.get("ledger_entry_id")
        if ledger is not None and (isinstance(ledger, bool) or not isinstance(ledger, int)):
            msg = "ledger_entry_id must be an integer or null."
            raise ValueError(msg)
        evicted_raw = data.get("evicted_event_digests", [])
        if not isinstance(evicted_raw, list) or not all(isinstance(x, str) for x in evicted_raw):
            msg = "evicted_event_digests must be a list of strings."
            raise ValueError(msg)
        event_digest = data.get("consolidation_event_digest")
        if event_digest is not None and not isinstance(event_digest, str):
            msg = "consolidation_event_digest must be a string or null."
            raise ValueError(msg)
        return cls(
            attempted=_bool(data, "attempted", False),
            succeeded=_bool(data, "succeeded", False),
            decision=LearningUpdateDecision.from_dict(decision_raw),
            consumed_learning_atp=_float(data, "consumed_learning_atp", 0.0),
            ledger_entry_id=ledger,
            memory_digest_before=_str(data, "memory_digest_before"),
            memory_digest_after=_str(data, "memory_digest_after"),
            summary={str(key): value for key, value in summary_raw.items()},
            state_changed=_bool(data, "state_changed", False),
            mode=_str(data, "mode", "audit_summary_only"),
            claim_allowed_for_learning_compression=_bool(data, "claim_allowed_for_learning_compression", False),
            evicted_count=_int(data, "evicted_count", len(evicted_raw)),
            evicted_event_digests=tuple(str(x) for x in evicted_raw),
            consolidation_event_digest=event_digest,
        )


def decide_learning_update(
    memory: object,
    prediction_error: float,
    config: LearningATPConfig,
    atp_state: GenesisATPState,
) -> LearningUpdateDecision:
    """Decide whether a future learning update should happen.

    The function is deterministic and decision-only. It does not consume ATP,
    build a graph, or infer causality.
    """

    prediction_error = finite_float("prediction_error", prediction_error, non_negative=True)  # type: ignore[assignment]
    reasons: list[str] = []
    if not config.learning_enabled:
        reasons.append("learning_disabled")
    threshold = _memory_threshold(memory)
    if prediction_error < 0:
        reasons.append("invalid_prediction_error")
    if prediction_error < threshold:
        reasons.append("prediction_error_below_threshold")
    if not atp_state.can_learn(config.prediction_update_cost):
        reasons.append("insufficient_learning_atp")
    return LearningUpdateDecision(
        should_update=not reasons,
        reasons=tuple(str(item) for item in reasons),
        prediction_error=prediction_error,
        threshold=threshold,
        learning_cost=config.prediction_update_cost,
        learning_atp_available=atp_state.learning_available,
    )


def consolidate_memory(
    memory: object,
    prediction_error: float,
    config: LearningATPConfig,
    atp_state: GenesisATPState,
    *,
    tick: int,
    organism_id: str,
) -> MemoryConsolidationResult:
    """Compute a small deterministic memory summary and debit ATP_learning.

    No CausalGraph, external ML, or causal-learning claim is implemented.
    """

    before = memory.digest() if hasattr(memory, "digest") else "unknown"
    decision = decide_learning_update(memory, prediction_error, config, atp_state)
    if decision.learning_cost != config.memory_consolidation_cost:
        decision = LearningUpdateDecision(
            should_update=decision.should_update and atp_state.can_learn(config.memory_consolidation_cost),
            reasons=decision.reasons
            if atp_state.can_learn(config.memory_consolidation_cost)
            else decision.reasons + ("insufficient_learning_atp",),
            prediction_error=decision.prediction_error,
            threshold=decision.threshold,
            learning_cost=config.memory_consolidation_cost,
            learning_atp_available=decision.learning_atp_available,
        )
    if not decision.should_update:
        return MemoryConsolidationResult(
            attempted=True,
            succeeded=False,
            decision=decision,
            consumed_learning_atp=0.0,
            ledger_entry_id=None,
            memory_digest_before=before,
            memory_digest_after=before,
            summary={},
        )
    summary = _memory_summary(memory)
    if int(summary.get("event_count", 0)) <= 0:
        return MemoryConsolidationResult(
            attempted=True,
            succeeded=False,
            decision=LearningUpdateDecision(
                should_update=False,
                reasons=decision.reasons + ("audit_summary_only_no_memory_events",),
                prediction_error=decision.prediction_error,
                threshold=decision.threshold,
                learning_cost=config.memory_consolidation_cost,
                learning_atp_available=atp_state.learning_available,
            ),
            consumed_learning_atp=0.0,
            ledger_entry_id=None,
            memory_digest_before=before,
            memory_digest_after=before,
            summary=summary,
            state_changed=False,
            mode="audit_summary_only",
            claim_allowed_for_learning_compression=False,
        )
    if not hasattr(memory, "write_event"):
        after = memory.digest() if hasattr(memory, "digest") else before
        return MemoryConsolidationResult(
            attempted=True,
            succeeded=False,
            decision=LearningUpdateDecision(
                should_update=False,
                reasons=decision.reasons + ("audit_summary_only_no_memory_write_api",),
                prediction_error=decision.prediction_error,
                threshold=decision.threshold,
                learning_cost=config.memory_consolidation_cost,
                learning_atp_available=atp_state.learning_available,
            ),
            consumed_learning_atp=0.0,
            ledger_entry_id=None,
            memory_digest_before=before,
            memory_digest_after=after,
            summary=summary,
            state_changed=False,
            mode="audit_summary_only",
            claim_allowed_for_learning_compression=False,
        )

    consolidation_digest = _digest(
        {
            "mode": "state_changing_consolidation",
            "memory_digest_before": before,
            "organism_id": organism_id,
            "summary": summary,
            "tick": tick,
        }
    )
    learning_before = atp_state.learning_available
    event = EpisodicEvent(
        tick=tick,
        organism_id=organism_id,
        action="MEMORY_CONSOLIDATION",
        status="executed",
        position_before=(0, 0),
        position_after=(0, 0),
        atp_runtime_before=atp_state.runtime_available,
        atp_runtime_after=atp_state.runtime_available,
        atp_learning_before=learning_before,
        atp_learning_after=max(0.0, learning_before - config.memory_consolidation_cost),
        world_digest_before=before,
        trace_event_digest=consolidation_digest,
        observation={"summary": summary, "memory_digest_before": before},
        outcome={"mode": "state_changing_consolidation"},
    )
    write_result = memory.write_event(
        event,
        atp_state,
        cost=config.memory_consolidation_cost,
        reason="memory_consolidation",
    )
    if not isinstance(write_result, MemoryWriteResult) or not write_result.written:
        blocked = LearningUpdateDecision(
            should_update=False,
            reasons=decision.reasons + ((getattr(write_result, "blocked_reason", None) or "memory_consolidation_write_blocked"),),
            prediction_error=decision.prediction_error,
            threshold=decision.threshold,
            learning_cost=config.memory_consolidation_cost,
            learning_atp_available=atp_state.learning_available,
        )
        after = memory.digest() if hasattr(memory, "digest") else before
        return MemoryConsolidationResult(
            attempted=True,
            succeeded=False,
            decision=blocked,
            consumed_learning_atp=0.0,
            ledger_entry_id=None,
            memory_digest_before=before,
            memory_digest_after=after,
            summary=summary,
            state_changed=False,
            mode="blocked",
            claim_allowed_for_learning_compression=False,
        )

    after = memory.digest() if hasattr(memory, "digest") else write_result.memory_digest_after
    state_changed = after != before
    return MemoryConsolidationResult(
        attempted=True,
        succeeded=state_changed,
        decision=decision if state_changed else LearningUpdateDecision(
            should_update=False,
            reasons=decision.reasons + ("audit_summary_only_no_memory_state_change",),
            prediction_error=decision.prediction_error,
            threshold=decision.threshold,
            learning_cost=config.memory_consolidation_cost,
            learning_atp_available=atp_state.learning_available,
        ),
        consumed_learning_atp=config.memory_consolidation_cost if state_changed else 0.0,
        ledger_entry_id=write_result.learning_ledger_entry_id if state_changed else None,
        memory_digest_before=before,
        memory_digest_after=after,
        summary=summary,
        state_changed=state_changed,
        mode="state_changing_consolidation" if state_changed else "audit_summary_only",
        claim_allowed_for_learning_compression=state_changed,
        evicted_count=write_result.evicted_count if state_changed else 0,
        evicted_event_digests=write_result.evicted_event_digests if state_changed else (),
        consolidation_event_digest=consolidation_digest if state_changed else None,
    )


def _memory_threshold(memory: object) -> float:
    config = getattr(memory, "config", None)
    threshold = getattr(config, "prediction_error_threshold", 0.25)
    if isinstance(threshold, int | float) and not isinstance(threshold, bool):
        return finite_float("prediction_error_threshold", threshold, non_negative=True)  # type: ignore[return-value]
    return 0.25


def _memory_summary(memory: object) -> dict[str, JsonValue]:
    events = tuple(getattr(memory, "events", ()))
    action_counts: dict[str, int] = {}
    blocked = 0
    runtime_delta = 0.0
    outcomes: dict[str, int] = {}
    for event in events:
        action = str(getattr(event, "action", "unknown"))
        status = str(getattr(event, "status", "unknown"))
        action_counts[action] = action_counts.get(action, 0) + 1
        outcomes[status] = outcomes.get(status, 0) + 1
        if status == "blocked":
            blocked += 1
        runtime_after = finite_float("event.atp_runtime_after", getattr(event, "atp_runtime_after", 0.0))
        runtime_before = finite_float("event.atp_runtime_before", getattr(event, "atp_runtime_before", 0.0))
        runtime_delta += runtime_after - runtime_before
    count = len(events)
    return {
        "event_count": count,
        "action_counts": cast(dict[str, JsonValue], action_counts),
        "blocked_ratio": 0.0 if count == 0 else round(blocked / count, 10),
        "runtime_atp_delta": round(runtime_delta, 10),
        "recent_outcome_frequency": cast(dict[str, JsonValue], outcomes),
    }


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
    return value


def _str(data: dict[str, JsonValue], key: str, default: str | None = None) -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        msg = f"{key} must be a string."
        raise ValueError(msg)
    return value


def _digest(data: dict[str, JsonValue]) -> str:
    encoded = finite_json_dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
