"""Create deterministic profiled agents without population evolution."""

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

from codontrace import AgentFactory, AgentProfile, InitializationConfig, World2D

world = World2D(width=12, height=8)

agents = AgentFactory.create_many(
    world=world,
    config=InitializationConfig(
        count=12,
        seed=42,
        genome_strategy="profiled_random",
        placement_strategy="poisson_disk",
        min_distance=2,
        profiles=(
            AgentProfile(
                name="explorer",
                count=4,
                genome_length=8,
                initial_atp=4.0,
                preferred_codons=("101", "011"),
            ),
            AgentProfile(
                name="collector",
                count=4,
                genome_length=6,
                initial_atp=6.0,
                preferred_codons=("111", "001"),
            ),
            AgentProfile(
                name="conserver",
                count=4,
                genome_length=4,
                initial_atp=8.0,
                preferred_codons=("000",),
            ),
        ),
    ),
)

for agent in agents:
    print(agent.id, agent.profile, agent.position, agent.genome.pretty())
