"""Round-trip library objects through dictionaries without file I/O."""

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
    AgentFactory,
    AgentSpec,
    InitializationConfig,
    Simulation,
    SimulationConfig,
    SimulationResult,
    World2D,
)

world = World2D(4, 4)
specs = AgentFactory.create_specs(
    world=world,
    config=InitializationConfig(count=2, seed=7, placement_strategy="grid"),
)
restored_specs = tuple(AgentSpec.from_dict(spec.to_dict()) for spec in specs)
agents = AgentFactory.from_specs(restored_specs, world=world)
result = Simulation.run(world=world, agents=agents, config=SimulationConfig(steps=2, seed=7))
restored_result = SimulationResult.from_dict(result.to_dict())
print(restored_result.summary())
