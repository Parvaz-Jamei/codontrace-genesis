"""Operational AliveGate metrics for controlled GENESIS Foundation runs.

AliveGate is an operational liveness metric for controlled runs. It is not proof
of artificial life. Full GENESIS alive(S) requires reproduction-capable
population dynamics and is deferred.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from codontrace._types import JsonValue
from codontrace.genesis.status import ActionStatusRegistry
from codontrace.trace import Trace, TraceEvent


@dataclass(frozen=True, slots=True)
class AliveGateConfig:
    """Thresholds for operational liveness candidate evaluation."""

    min_ticks: int = 10
    min_executed_actions: int = 1
    max_blocked_ratio: float = 0.8
    require_positive_runtime_atp: bool = True
    require_lumen_interaction: bool = False
    require_reproduction_capability: bool = False
    status_registry: ActionStatusRegistry = field(default_factory=ActionStatusRegistry.genesis_v0)

    def __post_init__(self) -> None:
        if self.min_ticks < 0 or self.min_executed_actions < 0:
            msg = "AliveGate minimum thresholds cannot be negative."
            raise ValueError(msg)
        if not 0 <= self.max_blocked_ratio <= 1:
            msg = "max_blocked_ratio must be in [0, 1]."
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class AliveGateResult:
    """Deterministic result of AliveGate evaluation."""

    passed: bool
    survived_ticks: int
    executed_actions: int
    blocked_actions: int
    blocked_ratio: float
    final_runtime_atp: float
    lumen_interactions: int
    reproduction_events: int
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a JSON-friendly AliveGate result."""

        return {
            "passed": self.passed,
            "survived_ticks": self.survived_ticks,
            "executed_actions": self.executed_actions,
            "blocked_actions": self.blocked_actions,
            "blocked_ratio": self.blocked_ratio,
            "final_runtime_atp": self.final_runtime_atp,
            "lumen_interactions": self.lumen_interactions,
            "reproduction_events": self.reproduction_events,
            "reasons": [reason for reason in self.reasons],
            "level": "operational_alive_candidate" if self.passed else "not_operational_alive",
            "genesis_alive_full": False,
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> AliveGateResult:
        """Restore an AliveGateResult from ``to_dict()`` output."""

        reasons = data.get("reasons", [])
        if not isinstance(reasons, list) or not all(isinstance(item, str) for item in reasons):
            msg = "AliveGateResult.reasons must be a list of strings."
            raise ValueError(msg)
        return cls(
            passed=_bool(data, "passed", False),
            survived_ticks=_int(data, "survived_ticks", 0),
            executed_actions=_int(data, "executed_actions", 0),
            blocked_actions=_int(data, "blocked_actions", 0),
            blocked_ratio=_float(data, "blocked_ratio", 0.0),
            final_runtime_atp=_float(data, "final_runtime_atp", 0.0),
            lumen_interactions=_int(data, "lumen_interactions", 0),
            reproduction_events=_int(data, "reproduction_events", 0),
            reasons=tuple(str(item) for item in reasons),
        )


def evaluate_alive(
    events: Trace | Sequence[TraceEvent],
    *,
    final_runtime_atp: float | None = None,
    config: AliveGateConfig | None = None,
) -> AliveGateResult:
    """Evaluate an operational liveness candidate gate without mutating inputs."""

    resolved_config = config or AliveGateConfig()
    event_tuple = tuple(events.events if isinstance(events, Trace) else events)
    if not event_tuple:
        return AliveGateResult(
            passed=False,
            survived_ticks=0,
            executed_actions=0,
            blocked_actions=0,
            blocked_ratio=0.0,
            final_runtime_atp=0.0 if final_runtime_atp is None else final_runtime_atp,
            lumen_interactions=0,
            reproduction_events=0,
            reasons=("empty_trace",),
        )
    # Generation-local traces may carry organism lifetime step indices.
    # Use the current trace length for default survival evaluation so per-generation
    # summaries cannot inflate merely because the organism internal cursor advanced.
    survived_ticks = len(event_tuple)
    executed = sum(
        1
        for event in event_tuple
        if resolved_config.status_registry.counts_as_executed(event.status)
    )
    blocked = sum(
        1
        for event in event_tuple
        if resolved_config.status_registry.counts_as_blocked(event.status)
    )
    blocked_ratio = round(blocked / len(event_tuple), 10)
    final_atp = event_tuple[-1].atp_after if final_runtime_atp is None else final_runtime_atp
    lumen_interactions = sum(
        1
        for event in event_tuple
        if event.world_delta.get("lumen_interaction") is True
        or (
            event.action == "EAT_LUMEN"
            and resolved_config.status_registry.counts_as_executed(event.status)
        )
    )
    reproduction_events = sum(
        1
        for event in event_tuple
        if event.action == "COPY_SELF"
        and resolved_config.status_registry.counts_as_executed(event.status)
    )
    reasons: list[str] = []
    if survived_ticks < resolved_config.min_ticks:
        reasons.append("min_ticks_not_met")
    if executed < resolved_config.min_executed_actions:
        reasons.append("min_executed_actions_not_met")
    if blocked_ratio > resolved_config.max_blocked_ratio:
        reasons.append("blocked_ratio_exceeded")
    if final_atp < 0:
        reasons.append("negative_runtime_atp")
    elif resolved_config.require_positive_runtime_atp and final_atp <= 0:
        reasons.append("positive_runtime_atp_required")
    if resolved_config.require_lumen_interaction and lumen_interactions <= 0:
        reasons.append("lumen_interaction_required")
    if resolved_config.require_reproduction_capability:
        reasons.append("full_genesis_alive_deferred")
    return AliveGateResult(
        passed=not reasons,
        survived_ticks=survived_ticks,
        executed_actions=executed,
        blocked_actions=blocked,
        blocked_ratio=blocked_ratio,
        final_runtime_atp=final_atp,
        lumen_interactions=lumen_interactions,
        reproduction_events=reproduction_events,
        reasons=tuple(str(item) for item in reasons),
    )


def _bool(data: dict[str, JsonValue], key: str, default: bool) -> bool:
    value = data.get(key, default)
    if not isinstance(value, bool):
        msg = f"{key} must be a boolean."
        raise ValueError(msg)
    return value


def _int(data: dict[str, JsonValue], key: str, default: int) -> int:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{key} must be an integer."
        raise ValueError(msg)
    return int(value)


def _float(data: dict[str, JsonValue], key: str, default: float) -> float:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int | float):
        msg = f"{key} must be numeric."
        raise ValueError(msg)
    return float(value)
