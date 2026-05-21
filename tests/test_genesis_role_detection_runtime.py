from __future__ import annotations

from codontrace.genesis.phase1_runtime_maturity import infer_runtime_roles_from_events
from codontrace.trace import TraceEvent


def _event(step: int, action: str, *, event_id: str | None = None, **delta: object) -> TraceEvent:
    world_delta = dict(delta)
    if event_id is not None:
        world_delta["event_id"] = event_id
    return TraceEvent(
        step=step,
        agent_id="org",
        codon="000",
        action=action,
        status="executed",
        reason="ok",
        atp_before=10.0,
        atp_after=9.0,
        position_before=(0, 0),
        position_after=(0, 0),
        world_delta=world_delta,
    )


def test_role_is_inferred_from_action_history_not_profile_label() -> None:
    events = (
        _event(0, "COLLECT_WOOD", event_id="e0", primitive_action="collect"),
        _event(1, "DEPOSIT_HOME", event_id="e1", primitive_action="deposit"),
    )
    roles = infer_runtime_roles_from_events("org", events, first_tick=4)
    labels = {item.role_label for item in roles}
    assert "collector" in labels
    assert "depositor" in labels
    for role in roles:
        assert role.source_event_ids
        assert role.contribution_digest
        assert role.record_digest


def test_role_timeline_marks_role_change_from_previous_runtime_role() -> None:
    events = (_event(0, "SEND_CAPSULE", event_id="e0", primitive_action="emit"),)
    roles = infer_runtime_roles_from_events(
        "org", events, first_tick=2, previous_role_label="collector"
    )
    assert roles[0].role_label == "capsule_sender"
    assert roles[0].role_changed is True


def test_unknown_role_is_explicit_when_action_evidence_is_insufficient() -> None:
    roles = infer_runtime_roles_from_events("org", (), first_tick=0)
    assert len(roles) == 1
    assert roles[0].role_label == "unknown"
    assert roles[0].support_count == 0
    assert roles[0].confidence == 0.0
