from __future__ import annotations

from codontrace.genesis import AliveGateConfig, GenesisOrganism
from codontrace.world import World2D


def test_fixed_9_bit_genome_runs_deterministically() -> None:
    left_world = World2D(3, 3, resources={(1, 0): 2.0})
    right_world = left_world.clone()
    left = GenesisOrganism.from_bits("g", "000001011", initial_runtime_atp=5.0)
    right = GenesisOrganism.from_bits("g", "000001011", initial_runtime_atp=5.0)
    left_result = left.run(left_world, ticks=3, alive_config=AliveGateConfig(min_ticks=3))
    right_result = right.run(right_world, ticks=3, alive_config=AliveGateConfig(min_ticks=3))
    assert left_result.trace.digest() == right_result.trace.digest()
    assert left_result.compiled_brain.digest() == right_result.compiled_brain.digest()


def test_compiled_brain_is_reused_and_atp_charged_before_execution() -> None:
    organism = GenesisOrganism.from_bits("g", "101000000", initial_runtime_atp=1.0)
    world = World2D(2, 2, resources={(0, 0): 2.0})
    result = organism.run(world, ticks=1, alive_config=AliveGateConfig(min_ticks=1))
    event = result.trace.events[0]
    assert event.action == "EAT_LUMEN"
    assert event.ledger_entry_ids == (0, 1)
    assert event.atp_before == 1.0
    assert event.atp_after == 2.2
    assert event.world_delta["compiled_brain_digest"] == result.compiled_brain.digest()


def test_alive_gate_result_is_included_and_serializable() -> None:
    organism = GenesisOrganism.from_bits("g", "000000000", initial_runtime_atp=2.0)
    result = organism.run(World2D(2, 2), ticks=3, alive_config=AliveGateConfig(min_ticks=3))
    payload = result.to_dict()
    assert payload["organism_id"] == "g"
    assert "alive_result" in payload
