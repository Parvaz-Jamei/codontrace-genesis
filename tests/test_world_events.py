from __future__ import annotations

import json

import pytest

from codontrace import RunRecorder, Trace, WhiteBoxAgent, World2D, WorldEvent, WorldObject
from codontrace.errors import ReplayError
from codontrace.replay import CausalReplay
from codontrace.trace import (
    WORLD_EVENT_EXTERNAL_REPLENISHMENT,
    WORLD_EVENT_RESOURCE_PLACED,
)


def test_world_event_to_dict_from_dict_roundtrip() -> None:
    event = WorldEvent(
        schema_version=1,
        step=12,
        sequence=34,
        event_type=WORLD_EVENT_RESOURCE_PLACED,
        position=(10, 5),
        source="environment",
        reason="replenishment",
        amount=8.0,
        before={"resource": 0.0},
        after={"resource": 8.0},
        delta={"resource_delta": 8.0},
        metadata={"zone": "north_hub"},
    )

    restored = WorldEvent.from_dict(event.to_dict())

    assert restored == event
    assert restored.event_kind == "world_event"
    assert restored.idempotency_key == "v1:12:34:resource_placed:10,5"


def test_trace_stores_world_events() -> None:
    trace = Trace()
    event = WorldEvent(1, 0, trace.next_sequence(), WORLD_EVENT_RESOURCE_PLACED, (1, 1))

    trace.append_world_event(event)

    assert trace.world_events == (event,)
    assert trace.all_events() == (event,)


def test_trace_bundle_from_bundle_roundtrip() -> None:
    trace = Trace()
    world = World2D(3, 3)
    world.place_resource_event((1, 1), 2.0, trace=trace, step=0)

    restored = Trace.from_bundle(trace.to_bundle())

    assert restored.world_events == trace.world_events
    assert restored.to_bundle() == trace.to_bundle()


def test_trace_jsonl_remains_agent_event_only() -> None:
    trace = Trace()
    world = World2D.from_ascii("""
    ...
    .A*
    ...
    """)
    world.place_resource_event((2, 1), 4.0, trace=trace, step=0)
    agent = WhiteBoxAgent.from_world(world, genome="000", initial_atp=5.0)
    agent.step(world, trace)

    lines = [line for line in trace.to_jsonl().splitlines() if line]

    assert len(lines) == 1
    assert json.loads(lines[0])["event_kind"] == "agent_action"
    assert len(trace.world_events) == 1


def test_trace_bundle_digest_changes_when_world_event_changes() -> None:
    trace_a = Trace()
    trace_b = Trace()
    World2D(3, 3).place_resource_event((1, 1), 2.0, trace=trace_a, step=0)
    World2D(3, 3).place_resource_event((1, 1), 3.0, trace=trace_b, step=0)

    assert trace_a.bundle_digest() != trace_b.bundle_digest()


def test_trace_to_engine_events_returns_sorted_mixed_events() -> None:
    trace = Trace()
    world = World2D.from_ascii("""
    ...
    .A*
    ...
    """)
    world.place_resource_event((2, 1), 4.0, trace=trace, step=0)
    agent = WhiteBoxAgent.from_world(world, genome="000", initial_atp=5.0)
    agent.step(world, trace)

    engine_events = trace.to_engine_events()

    assert [item["kind"] for item in engine_events] == ["world", "agent"]
    assert json.loads(trace.to_engine_json())[0]["kind"] == "world"


def test_world_place_resource_event_logs_before_after_delta() -> None:
    trace = Trace()
    world = World2D(4, 4)

    event = world.place_resource_event((2, 2), 8.0, trace=trace, step=3, reason="initial food")

    assert event.before == {"resource": 0.0}
    assert event.after == {"resource": 8.0}
    assert event.delta == {"resource_delta": 8.0}
    assert trace.world_events == (event,)


def test_world_apply_world_event_reproduces_world_state() -> None:
    trace = Trace()
    world = World2D(4, 4)
    event = world.place_resource_event((2, 2), 8.0, trace=trace, step=3)
    replay_world = World2D(4, 4)

    replay_world.apply_world_event(event)

    assert replay_world.digest() == world.digest()


def test_apply_world_events_sorted_by_step_sequence_is_deterministic() -> None:
    trace = Trace()
    world = World2D(5, 5)
    later = world.place_resource_event((3, 3), 4.0, trace=trace, step=2)
    earlier = world.place_resource_event((1, 1), 2.0, trace=trace, step=1)

    replayed = CausalReplay.apply_world_events(World2D(5, 5), [later, earlier])

    assert replayed.resource_amount((1, 1)) == 2.0
    assert replayed.resource_amount((3, 3)) == 4.0


def test_run_recorder_place_resource_records_event_and_mutates_world() -> None:
    world = World2D(4, 4)
    recorder = RunRecorder()

    event = recorder.place_resource(world, (2, 2), 5.0, step=0)

    assert world.resource_amount((2, 2)) == 5.0
    assert recorder.trace.world_events == (event,)
    assert event.source == "recorder"


def test_viewer_state_export_contains_layers_agents_and_events() -> None:
    trace = Trace()
    world = World2D.from_ascii("""
    .#.
    .A.
    ...
    """)
    event = world.place_resource_event((2, 2), 7.0, trace=trace, step=1)
    agent = WhiteBoxAgent.from_world(world, genome="000", initial_atp=3.0)

    state = world.to_view_state(agents=(agent,), step=1, events=(event,))

    assert state["world"] == {"width": 3, "height": 3}
    assert state["agents"]
    assert state["events"]
    assert state["layers"]


def test_bundle_with_missing_world_events_loads_as_empty() -> None:
    restored = Trace.from_bundle({"schema_version": 1, "agent_events": []})

    assert restored.world_events == ()


def test_object_event_roundtrip_and_apply_is_idempotent_friendly() -> None:
    trace = Trace()
    world = World2D(4, 4)
    obj = WorldObject(kind="FOOD", amount=3.0, metadata={"color": "green"})
    event = world.add_object_event((1, 1), obj, trace=trace, step=0)
    replay_world = World2D(4, 4)

    replay_world.apply_world_event(event)
    replay_world.apply_world_event(event)

    assert replay_world.objects_at((1, 1)) == (obj,)


def test_external_replenishment_event_applies_like_resource_change() -> None:
    event = WorldEvent(
        schema_version=1,
        step=0,
        sequence=0,
        event_type=WORLD_EVENT_EXTERNAL_REPLENISHMENT,
        position=(1, 1),
        amount=9.0,
        after={"resource": 9.0},
    )
    world = World2D(3, 3)

    world.apply_world_event(event)

    assert world.resource_amount((1, 1)) == 9.0


def test_timeline_agent_before_world_same_step_preserves_append_order() -> None:
    trace = Trace()
    world = World2D.from_ascii("""
    ...
    .A.
    ...
    """)
    agent = WhiteBoxAgent.from_world(world, genome="000", initial_atp=5.0)

    agent.step(world, trace)
    world.place_resource_event((2, 2), 4.0, trace=trace, step=0)

    assert [item["kind"] for item in trace.to_engine_events()] == ["agent", "world"]


def test_timeline_world_before_agent_same_step_preserves_append_order() -> None:
    trace = Trace()
    world = World2D.from_ascii("""
    ...
    .A.
    ...
    """)
    world.place_resource_event((2, 2), 4.0, trace=trace, step=0)
    agent = WhiteBoxAgent.from_world(world, genome="000", initial_atp=5.0)

    agent.step(world, trace)

    assert [item["kind"] for item in trace.to_engine_events()] == ["world", "agent"]


def test_timeline_multiple_agent_events_same_step_preserve_append_order() -> None:
    trace = Trace()
    world = World2D(5, 5)
    first = WhiteBoxAgent.quick(agent_id="first", genome="000", position=(1, 1), initial_atp=5.0)
    second = WhiteBoxAgent.quick(agent_id="second", genome="000", position=(2, 2), initial_atp=5.0)

    first.step(world, trace)
    second.step(world, trace)

    events = trace.to_engine_events()
    assert [item["agent"] for item in events] == ["first", "second"]


def test_bundle_restore_keeps_mixed_timeline_order() -> None:
    trace = Trace()
    world = World2D.from_ascii("""
    ...
    .A.
    ...
    """)
    agent = WhiteBoxAgent.from_world(world, genome="000", initial_atp=5.0)
    agent.step(world, trace)
    world.place_resource_event((2, 2), 4.0, trace=trace, step=0)

    restored = Trace.from_bundle(trace.to_bundle())

    assert restored.to_bundle() == trace.to_bundle()
    assert restored.to_engine_events() == trace.to_engine_events()


def test_engine_events_match_bundle_timeline_order() -> None:
    trace = Trace()
    world = World2D.from_ascii("""
    ...
    .A.
    ...
    """)
    agent = WhiteBoxAgent.from_world(world, genome="000", initial_atp=5.0)
    agent.step(world, trace)
    world.place_resource_event((2, 2), 4.0, trace=trace, step=0)

    bundle_timeline = trace.to_bundle()["timeline"]
    engine_events = trace.to_engine_events()

    assert isinstance(bundle_timeline, list)
    assert [(item["event_kind"], item["sequence"]) for item in bundle_timeline] == [
        ("agent_action" if item["kind"] == "agent" else "world_event", item["seq"])
        for item in engine_events
    ]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"schema_version": True, "step": 0, "sequence": 0, "event_type": "x"},
        {"schema_version": 1, "step": False, "sequence": 0, "event_type": "x"},
        {"schema_version": 1, "step": 0, "sequence": True, "event_type": "x"},
        {"schema_version": 1, "step": 0, "sequence": 0, "event_type": "x", "amount": True},
        {"schema_version": 1, "step": 0, "sequence": 0, "event_type": "x", "position": (True, 1)},
    ],
)
def test_world_event_rejects_bool_numeric_fields(kwargs: dict[str, object]) -> None:
    with pytest.raises(ReplayError):
        WorldEvent(**kwargs)  # type: ignore[arg-type]


def test_world_event_from_dict_rejects_bool_numeric_fields() -> None:
    base = {"schema_version": 1, "step": 0, "sequence": 0, "event_type": "x"}
    for key, value in (
        ("schema_version", True),
        ("step", False),
        ("sequence", True),
        ("amount", True),
    ):
        data = dict(base)
        data[key] = value
        with pytest.raises(ReplayError):
            WorldEvent.from_dict(data)  # type: ignore[arg-type]


def test_agent_engine_event_includes_delta() -> None:
    trace = Trace()
    world = World2D(3, 3)
    agent = WhiteBoxAgent.quick(agent_id="a1", genome="000", position=(1, 1), initial_atp=5.0)
    agent.step(world, trace)

    event = trace.to_engine_events()[0]

    assert event["kind"] == "agent"
    assert "delta" in event
    assert isinstance(event["delta"], dict)
