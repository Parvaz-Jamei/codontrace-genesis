"""Define custom action status semantics for AliveGate metrics."""

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

from codontrace.genesis import ActionStatusRegistry, AliveGateConfig, evaluate_alive
from codontrace.trace import TraceEvent

registry = ActionStatusRegistry.genesis_v0().define(
    "deferred",
    "deferred",
    counts_as_executed=False,
    counts_as_blocked=False,
    counts_as_failed=False,
    counts_as_deferred=True,
)
event = TraceEvent(
    step=0,
    agent_id="demo",
    codon="000",
    action="WAIT",
    status="deferred",
    reason="example",
    atp_before=1.0,
    atp_after=1.0,
    position_before=(0, 0),
    position_after=(0, 0),
    world_delta={},
)
print(
    evaluate_alive([event], config=AliveGateConfig(min_ticks=0, status_registry=registry)).to_dict()
)
