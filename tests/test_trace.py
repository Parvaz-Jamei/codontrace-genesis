from __future__ import annotations

import pytest

from codontrace import Trace, TraceEvent


def test_trace_append_json_and_digest() -> None:
    trace = Trace()
    trace.append(
        TraceEvent(
            step=0,
            agent_id="a",
            codon="000",
            action="WAIT",
            atp_before=1.0,
            atp_after=0.9,
            position_before=(0, 0),
            position_after=(0, 0),
            status="executed",
            reason="executed",
            ledger_entry_ids=(0,),
        )
    )
    assert trace.last().action == "WAIT"
    assert "WAIT" in trace.to_json()
    assert len(trace.digest()) == 64


def test_trace_event_is_explicitly_unhashable() -> None:
    event = TraceEvent(
        step=0,
        agent_id="a",
        codon="000",
        action="WAIT",
        atp_before=1.0,
        atp_after=0.9,
        position_before=(0, 0),
        position_after=(0, 0),
        world_delta={},
    )

    assert TraceEvent.__hash__ is None
    with pytest.raises(TypeError):
        hash(event)
