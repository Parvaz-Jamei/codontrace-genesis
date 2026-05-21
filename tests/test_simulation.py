from __future__ import annotations

from codontrace import (
    AgentFactory,
    AgentSpec,
    ATPAccount,
    Codon,
    CodonTable,
    SemanticGenome,
    Simulation,
    SimulationConfig,
    WhiteBoxAgent,
    World2D,
)


def _agent(agent_id: str, position: tuple[int, int], codon: str = "000") -> WhiteBoxAgent:
    return WhiteBoxAgent(
        id=agent_id,
        genome=SemanticGenome.from_codons([codon]),
        codon_table=CodonTable.default_minimal(),
        atp_account=ATPAccount(10.0),
        position=position,
    )


def test_simulation_runs_multiple_agents() -> None:
    result = Simulation.run(
        world=World2D(4, 4),
        agents=(_agent("a", (0, 0)), _agent("b", (1, 1))),
        config=SimulationConfig(steps=2),
    )

    assert len(result.trace) == 4
    assert len(result.agent_states) == 2


def test_same_seed_gives_same_trace_digest() -> None:
    world = World2D(4, 4)
    left = Simulation.run(
        world=world,
        agents=(_agent("a", (0, 0), "101"), _agent("b", (3, 3), "110")),
        config=SimulationConfig(steps=3, scheduler="random_order", seed=9),
    )
    right = Simulation.run(
        world=world,
        agents=(_agent("a", (0, 0), "101"), _agent("b", (3, 3), "110")),
        config=SimulationConfig(steps=3, scheduler="random_order", seed=9),
    )

    assert left.trace_digest == right.trace_digest


def test_collision_policy_block_prevents_overlap() -> None:
    table = CodonTable.default_minimal().replace(Codon("001", "MOVE_EAST", 0.0))
    agents = AgentFactory.from_specs(
        (
            AgentSpec("a", SemanticGenome.from_codons(["001"]), 10.0, (0, 0)),
            AgentSpec("b", SemanticGenome.from_codons(["000"]), 10.0, (1, 0)),
        ),
        codon_table=table,
    )

    result = Simulation.run(world=World2D(3, 2), agents=agents, config=SimulationConfig(steps=1))
    positions = [tuple(state["position"]) for state in result.agent_states]

    assert len(set(positions)) == 2
    assert result.to_dict()["trace_digest"] == result.trace_digest
