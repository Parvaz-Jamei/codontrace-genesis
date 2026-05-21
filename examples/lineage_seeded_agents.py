"""Create deterministic lineage-seeded initialization metadata."""

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

from codontrace import AgentFactory, InitializationConfig, World2D

world = World2D(width=10, height=6)

agents = AgentFactory.create_many(
    world=world,
    config=InitializationConfig(
        count=10,
        seed=7,
        genome_strategy="lineage_seeded",
        placement_strategy="poisson_disk",
        min_distance=1,
    ),
)

for agent in agents:
    print(
        agent.id,
        agent.lineage_id,
        "parent=",
        agent.parent_id,
        "gen=",
        agent.generation,
        agent.position,
        agent.genome.pretty(),
    )
