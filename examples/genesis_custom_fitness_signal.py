"""Add a runtime-only custom fitness signal as a Python callable."""

try:
    from ._path_bootstrap import ensure_src_path
except ImportError:  # direct script or runpy execution outside the examples package
    import sys as _sys
    from pathlib import Path as _Path

    _EXAMPLES_DIR = _Path(__file__).resolve().parent
    if str(_EXAMPLES_DIR) not in _sys.path:
        _sys.path.insert(0, str(_EXAMPLES_DIR))
    from _path_bootstrap import ensure_src_path

ensure_src_path()

from collections.abc import Mapping, Sequence

from codontrace.genesis import (
    AliveGateResult,
    FitnessConfig,
    FitnessSignalRegistry,
    evaluate_fitness,
)
from codontrace.trace import Trace, TraceEvent


def constant_signal(
    trace: Trace | Sequence[TraceEvent],
    organism: object | None,
    context: Mapping[str, object] | None,
) -> float:
    return 2.0


registry = FitnessSignalRegistry.genesis_v0().add_signal(
    "constant_demo", constant_signal, weight=3.0
)
alive = AliveGateResult(True, 1, 1, 0, 0.0, 1.0, 0, 0, ())
print(evaluate_fitness(Trace(), alive, FitnessConfig(signal_registry=registry)).to_dict())
