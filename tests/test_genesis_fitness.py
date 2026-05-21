from __future__ import annotations

from codontrace.genesis import AliveGateResult, FitnessConfig, evaluate_fitness
from codontrace.trace import Trace, TraceEvent


def _event(
    action: str, *, status: str = "executed", delta: dict[str, object] | None = None
) -> TraceEvent:
    return TraceEvent(
        step=0,
        agent_id="org",
        codon="000",
        action=action,
        atp_before=10.0,
        atp_after=9.0,
        position_before=(0, 0),
        position_after=(0, 0),
        status=status,
        reason="test",
        world_delta={} if delta is None else delta,
    )


def test_fitness_rewards_survival_and_penalizes_blocked_actions() -> None:
    trace = Trace()
    trace.append(_event("WAIT"))
    trace.append(_event("MOVE_TOWARD", status="blocked"))
    alive = AliveGateResult(True, 2, 1, 1, 0.5, 5.0, 0, 0, ())

    result = evaluate_fitness(trace, alive, FitnessConfig())

    assert result.score == 1.5
    assert result.blocked_actions == 1


def test_fitness_counts_only_actual_reproduction_success() -> None:
    trace = Trace()
    trace.append(_event("COPY_SELF", delta={"reproduction_succeeded": True}))
    trace.append(_event("COPY_SELF", status="blocked", delta={"reproduction_succeeded": False}))
    alive = AliveGateResult(True, 2, 1, 1, 0.5, 5.0, 0, 1, ())

    result = evaluate_fitness(trace, alive, FitnessConfig())

    assert result.reproduction_events == 1
    assert result.score > 0
    assert result == evaluate_fitness(trace, alive, FitnessConfig())
