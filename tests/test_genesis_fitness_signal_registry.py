from __future__ import annotations

from collections.abc import Mapping, Sequence

from codontrace.genesis import (
    AliveGateResult,
    FitnessConfig,
    FitnessSignalRegistry,
    evaluate_fitness,
)
from codontrace.trace import Trace, TraceEvent


def _custom_signal(
    trace: Trace | Sequence[TraceEvent],
    organism: object | None,
    context: Mapping[str, object] | None,
) -> float:
    return 3.0


def test_custom_fitness_signal_runtime_callable() -> None:
    registry = FitnessSignalRegistry.genesis_v0().add_signal(
        "custom_lumen_efficiency", _custom_signal, weight=2.0
    )
    alive = AliveGateResult(True, 1, 1, 0, 0.0, 1.0, 0, 0, ())
    result = evaluate_fitness(Trace(), alive, FitnessConfig(signal_registry=registry))
    assert result.score >= 6.0
