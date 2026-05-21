from __future__ import annotations

from codontrace.genesis import AliveGateResult, BehaviorDescriptor, describe_behavior
from codontrace.trace import Trace, TraceEvent


def _trace() -> Trace:
    trace = Trace()
    trace.append(TraceEvent(0, "o", "000", "WAIT", 3.0, 2.9, (0, 0), (0, 0), {}, "executed", ""))
    trace.append(
        TraceEvent(
            1,
            "o",
            "101",
            "EAT_LUMEN",
            2.9,
            4.9,
            (0, 0),
            (1, 0),
            {"lumen_interaction": True},
            "executed",
            "lumen_consumed",
        )
    )
    trace.append(
        TraceEvent(
            2,
            "o",
            "111",
            "COPY_SELF",
            4.9,
            3.0,
            (1, 0),
            (1, 0),
            {"reproduction_succeeded": True},
            "executed",
            "reproduction_succeeded",
        )
    )
    return trace


def test_behavior_descriptor_counts_and_roundtrips() -> None:
    alive = AliveGateResult(True, 3, 3, 0, 0.0, 3.0, 1, 1, ())
    descriptor = describe_behavior(_trace(), alive)
    assert descriptor.survival_ticks == 3
    assert descriptor.lumen_eaten == 1
    assert descriptor.reproduction_count == 1
    assert descriptor.unique_positions == 2
    assert descriptor.path_entropy_lite > 0
    assert BehaviorDescriptor.from_dict(descriptor.to_dict()) == descriptor
