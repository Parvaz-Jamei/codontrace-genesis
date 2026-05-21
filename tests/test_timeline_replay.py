from __future__ import annotations

import json

from codontrace import RunRecorder, Trace, WhiteBoxAgent, World2D
from codontrace.replay import CausalReplay, TimelineReplayResult


def test_same_initial_world_and_world_events_produce_same_final_digest() -> None:
    recorder = RunRecorder()
    source_world = World2D(5, 5)
    recorder.place_resource(source_world, (1, 1), 2.0, step=0)
    recorder.place_resource(source_world, (2, 2), 4.0, step=1)

    replayed = CausalReplay.apply_world_events(World2D(5, 5), recorder.trace.world_events)

    assert replayed.digest() == source_world.digest()


def test_changed_world_event_amount_changes_final_digest() -> None:
    trace_a = Trace()
    trace_b = Trace()
    World2D(5, 5).place_resource_event((1, 1), 2.0, trace=trace_a, step=0)
    World2D(5, 5).place_resource_event((1, 1), 3.0, trace=trace_b, step=0)

    world_a = CausalReplay.apply_world_events(World2D(5, 5), trace_a.world_events)
    world_b = CausalReplay.apply_world_events(World2D(5, 5), trace_b.world_events)

    assert world_a.digest() != world_b.digest()


def test_external_replenishment_appears_before_collection_in_timeline_ordering() -> None:
    world = World2D.from_ascii("""
    ...
    .A.
    ...
    """)
    trace = Trace()
    world.place_resource_event((1, 1), 2.0, trace=trace, step=0, reason="external")
    agent = WhiteBoxAgent.from_world(world, genome="111", initial_atp=5.0)
    agent.step(world, trace)

    events = trace.to_engine_events()

    assert events[0]["kind"] == "world"
    assert events[1]["kind"] == "agent"
    assert events[1]["type"] == "COLLECT_RESOURCE"


def test_engine_events_are_json_serializable() -> None:
    trace = Trace()
    World2D(3, 3).place_resource_event((1, 1), 1.0, trace=trace, step=0)

    payload = json.loads(trace.to_engine_json())

    assert payload[0]["type"] == "resource_placed"


def test_replay_timeline_emits_frames_and_digests() -> None:
    recorder = RunRecorder()
    world = World2D(5, 5)
    recorder.place_resource(world, (1, 1), 2.0, step=0)
    recorder.place_resource(world, (2, 2), 4.0, step=1)

    result = CausalReplay.replay_timeline(
        initial_world=World2D(5, 5),
        trace=recorder.trace,
        emit_frames=True,
        frame_every=1,
    )

    assert isinstance(result, TimelineReplayResult)
    assert result.world_digest == world.digest()
    assert result.frames
    assert result.bundle_digest == recorder.trace.bundle_digest()
