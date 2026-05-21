from __future__ import annotations

from codontrace.genesis import ActionStatusRegistry, AliveGateConfig, evaluate_alive
from codontrace.trace import TraceEvent


def _event(status: str) -> TraceEvent:
    return TraceEvent(
        step=0,
        agent_id="a",
        codon="000",
        action="WAIT",
        status=status,
        reason="demo",
        atp_before=1.0,
        atp_after=1.0,
        position_before=(0, 0),
        position_after=(0, 0),
        world_delta={},
    )


def test_custom_action_status_semantics_in_alive_gate() -> None:
    registry = ActionStatusRegistry.genesis_v0().define(
        "partially_executed",
        "executed",
        counts_as_executed=True,
        counts_as_blocked=False,
        counts_as_failed=False,
    )
    result = evaluate_alive(
        [_event("partially_executed")],
        config=AliveGateConfig(min_ticks=0, status_registry=registry),
    )
    assert result.executed_actions == 1
    assert ActionStatusRegistry.from_dict(registry.to_dict()).digest() == registry.digest()
