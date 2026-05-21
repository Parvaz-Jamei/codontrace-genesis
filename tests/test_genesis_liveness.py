from __future__ import annotations

from codontrace.genesis import AliveGateConfig, evaluate_alive
from codontrace.trace import Trace, TraceEvent


def _event(
    step: int, *, status: str = "executed", atp: float = 1.0, action: str = "WAIT"
) -> TraceEvent:
    return TraceEvent(
        step=step,
        agent_id="g",
        codon="000",
        action=action,
        atp_before=atp,
        atp_after=atp,
        position_before=(0, 0),
        position_after=(0, 0),
        status=status,
        reason=status,
        world_delta={},
    )


def test_empty_trace_fails() -> None:
    assert evaluate_alive(Trace()).passed is False


def test_all_blocked_behavior_fails() -> None:
    result = evaluate_alive([_event(0, status="blocked"), _event(1, status="blocked")])
    assert result.passed is False
    assert "min_executed_actions_not_met" in result.reasons


def test_positive_executed_actions_can_pass_operational_candidate_gate() -> None:
    events = [_event(step, atp=2.0) for step in range(10)]
    result = evaluate_alive(events, config=AliveGateConfig(min_ticks=10))
    assert result.passed is True
    assert result.to_dict()["level"] == "operational_alive_candidate"


def test_negative_atp_cannot_pass() -> None:
    events = [_event(step, atp=-1.0) for step in range(10)]
    result = evaluate_alive(events, final_runtime_atp=-1.0)
    assert result.passed is False
    assert "negative_runtime_atp" in result.reasons


def test_input_trace_not_mutated() -> None:
    trace = Trace()
    trace.append(_event(0))
    before = trace.digest()
    evaluate_alive(trace, config=AliveGateConfig(min_ticks=1))
    assert trace.digest() == before
