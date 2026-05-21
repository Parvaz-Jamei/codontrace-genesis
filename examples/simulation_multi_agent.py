"""Run multiple agents through the library-first Simulation API."""

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

from codontrace import AgentFactory, InitializationConfig, Simulation, SimulationConfig, World2D

world = World2D.from_ascii(
    """
....
....
....
....
"""
)
agents = AgentFactory.create_many(
    world=world,
    config=InitializationConfig(count=3, seed=42, placement_strategy="grid"),
)
result = Simulation.run(
    world=world,
    agents=agents,
    config=SimulationConfig(steps=5, scheduler="random_order", seed=42),
)
print(result.summary())
