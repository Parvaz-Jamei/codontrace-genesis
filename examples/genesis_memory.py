"""Demonstrate Dual ATP + EpisodicMemory without file output or UI."""

from __future__ import annotations

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

from codontrace import (
    AliveGateConfig,
    EpisodicMemory,
    GenesisATPState,
    GenesisOrganism,
    LearningATPConfig,
    World2D,
)

world = World2D(4, 4)
organism = GenesisOrganism.from_bits("mem-1", "000000000", initial_runtime_atp=5.0, position=(1, 1))
organism.atp_state = GenesisATPState.from_runtime(
    5.0,
    learning_atp=1.0,
    learning_enabled=True,
)
organism.episodic_memory = EpisodicMemory()
organism.learning_config = LearningATPConfig(memory_write_cost=0.1)

result = organism.run(
    world,
    ticks=3,
    alive_config=AliveGateConfig(
        min_ticks=1,
        min_executed_actions=0,
        require_positive_runtime_atp=False,
    ),
)

print("version: genesis_memory_demo")
print(f"events: {len(result.trace.events)}")
print(f"memory_size: {len(organism.episodic_memory.events) if organism.episodic_memory else 0}")
print(f"runtime_atp: {organism.atp_state.runtime_available:.2f}")
print(f"learning_atp: {organism.atp_state.learning_available:.2f}")
print(f"memory_digest: {organism.episodic_memory.digest() if organism.episodic_memory else 'none'}")
