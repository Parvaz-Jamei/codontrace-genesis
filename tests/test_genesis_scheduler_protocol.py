from __future__ import annotations

from codontrace import (
    ATPAccount,
    CodonTable,
    EnergyPriorityScheduler,
    SemanticGenome,
    Simulation,
    SimulationConfig,
    WhiteBoxAgent,
    World2D,
)


def _agent(agent_id: str, atp: float) -> WhiteBoxAgent:
    return WhiteBoxAgent(
        id=agent_id,
        genome=SemanticGenome.from_codons(("000",)),
        codon_table=CodonTable.default_minimal(),
        atp_account=ATPAccount(atp),
        position=(0 if agent_id == "a" else 1, 0),
    )


def test_energy_priority_scheduler_object_runs() -> None:
    result = Simulation.run(
        world=World2D(2, 1),
        agents=(_agent("a", 1.0), _agent("b", 5.0)),
        config=SimulationConfig(steps=1, scheduler=EnergyPriorityScheduler()),
    )
    assert len(result.trace.events) == 2
    assert result.trace.events[0].agent_id == "b"
