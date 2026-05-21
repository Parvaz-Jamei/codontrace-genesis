"""Run a tiny simulation with object-based scheduler and topology presets."""

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
    ATPAccount,
    CodonTable,
    EnergyPriorityScheduler,
    SemanticGenome,
    Simulation,
    SimulationConfig,
    TorusTopology,
    WhiteBoxAgent,
    World2D,
)


def agent(agent_id: str, x: int, atp: float) -> WhiteBoxAgent:
    return WhiteBoxAgent(
        id=agent_id,
        genome=SemanticGenome.from_codons(("000",)),
        codon_table=CodonTable.default_minimal(),
        atp_account=ATPAccount(atp),
        position=(x, 0),
    )


world = World2D(2, 1, topology=TorusTopology())
result = Simulation.run(
    world=world,
    agents=(agent("low", 0, 1.0), agent("high", 1, 5.0)),
    config=SimulationConfig(steps=1, scheduler=EnergyPriorityScheduler()),
)
print(result.summary())
