from __future__ import annotations

from codontrace.actions import ActionRuntimeConfig, default_action_registry
from codontrace.genesis.causal_graph import CausalGraph, CausalGraphConfig
from codontrace.genesis.learning import LearningATPConfig
from codontrace.genesis.liveness import AliveGateResult
from codontrace.genesis.memory import EpisodicMemory, EpisodicMemoryConfig
from codontrace.genesis.organism import GenesisOrganism
from codontrace.genesis.population import MutationConfig, ReproductionConfig, reproduce
from codontrace.trace import Trace
from codontrace.world import World2D


def _alive(parent: GenesisOrganism) -> AliveGateResult:
    return AliveGateResult(
        passed=True,
        survived_ticks=1,
        executed_actions=1,
        blocked_actions=0,
        blocked_ratio=0.0,
        final_runtime_atp=parent.atp_state.runtime_available,
        lumen_interactions=0,
        reproduction_events=0,
        reasons=(),
    )


def test_reproduction_child_inherits_learning_runtime_config_without_memory_leak() -> None:
    memory_config = EpisodicMemoryConfig(capacity=7)
    learning_config = LearningATPConfig(memory_write_cost=0.0, prediction_update_cost=0.0)
    causal_config = CausalGraphConfig(update_cost=0.0)
    registry = default_action_registry()
    runtime_config = ActionRuntimeConfig(open_statuses=True)
    parent = GenesisOrganism.from_bits(
        "parent",
        "000000000",
        initial_runtime_atp=20.0,
        initial_learning_atp=5.0,
        learning_enabled=True,
        action_registry=registry,
        memory_config=memory_config,
        causal_graph=CausalGraph(config=causal_config),
    )
    parent.learning_config = learning_config
    parent.action_runtime_config = runtime_config
    parent.episodic_memory = EpisodicMemory(memory_config)
    parent.step(World2D(3, 3), Trace())
    assert parent.episodic_memory is not None
    assert len(parent.episodic_memory.events) > 0
    parent_graph_digest = parent.causal_graph.digest() if parent.causal_graph is not None else None

    result = reproduce(
        parent,
        ReproductionConfig(min_runtime_atp=1.0, parent_atp_cost=1.0, offspring_atp_fraction=0.25),
        MutationConfig(bit_flip_rate=0.0),
        alive_result=_alive(parent),
        generation=0,
        birth_tick=1,
        seed=99,
    )

    assert result.succeeded
    assert result.child is not None
    child = result.child
    assert child.action_registry is registry
    assert child.action_runtime_config is runtime_config
    assert child.memory_config == memory_config
    assert child.learning_config == learning_config
    assert child.atp_state.learning_enabled
    assert child.causal_graph is not None
    assert parent.causal_graph is not None
    assert child.causal_graph is not parent.causal_graph
    assert child.causal_graph.config == parent.causal_graph.config
    assert child.causal_graph.digest() != parent_graph_digest
    assert child.episodic_memory is not None
    assert len(child.episodic_memory.events) == 0
