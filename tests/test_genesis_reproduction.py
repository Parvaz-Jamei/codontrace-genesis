from __future__ import annotations

from codontrace.genesis import (
    AliveGateResult,
    MutationConfig,
    ReproductionConfig,
    can_reproduce,
    reproduce,
)
from codontrace.genesis.organism import GenesisOrganism


def _alive(passed: bool = True) -> AliveGateResult:
    return AliveGateResult(
        passed=passed,
        survived_ticks=1,
        executed_actions=1,
        blocked_actions=0,
        blocked_ratio=0.0,
        final_runtime_atp=10.0,
        lumen_interactions=0,
        reproduction_events=0,
        reasons=() if passed else ("blocked_ratio_exceeded",),
    )


def test_insufficient_atp_blocks_reproduction() -> None:
    organism = GenesisOrganism.from_bits("parent", "111", initial_runtime_atp=1.0)
    config = ReproductionConfig(min_runtime_atp=8.0, parent_atp_cost=2.0)

    decision = can_reproduce(organism, _alive(), config)

    assert not decision.allowed
    assert "min_runtime_atp_not_met" in decision.reasons


def test_sufficient_atp_allows_reproduction_and_records_lineage() -> None:
    parent = GenesisOrganism.from_bits("parent", "111", initial_runtime_atp=20.0)
    config = ReproductionConfig(
        min_runtime_atp=5.0, parent_atp_cost=1.0, offspring_atp_fraction=0.25
    )

    result = reproduce(
        parent,
        config,
        MutationConfig(bit_flip_rate=0.0),
        alive_result=_alive(),
        generation=0,
        birth_tick=3,
        seed=42,
    )

    assert result.succeeded
    assert result.child is not None
    assert result.lineage is not None
    assert result.lineage.parent_id == "parent"
    assert result.lineage.genome_digest == result.child.genome.digest()
    assert result.parent_after.atp_state.runtime_available >= 0
    assert parent.atp_state.runtime_available == 20.0


def test_disabled_reproduction_blocks_copy_self() -> None:
    parent = GenesisOrganism.from_bits("parent", "111", initial_runtime_atp=20.0)
    config = ReproductionConfig(enabled=False, min_runtime_atp=5.0)

    result = reproduce(
        parent, config, MutationConfig(bit_flip_rate=0.0), alive_result=_alive(), seed=1
    )

    assert not result.succeeded
    assert "reproduction_disabled" in result.decision.reasons


def test_parent_atp_never_goes_negative_after_reproduction() -> None:
    parent = GenesisOrganism.from_bits("parent", "111", initial_runtime_atp=8.0)
    config = ReproductionConfig(
        min_runtime_atp=1.0, parent_atp_cost=8.0, offspring_atp_fraction=1.0
    )

    result = reproduce(
        parent, config, MutationConfig(bit_flip_rate=0.0), alive_result=_alive(), seed=4
    )

    assert result.succeeded
    assert result.parent_after.atp_state.runtime_available == 0.0


def test_reproduce_requires_alive_result_by_default() -> None:
    parent = GenesisOrganism.from_bits("parent", "111", initial_runtime_atp=20.0)
    config = ReproductionConfig(min_runtime_atp=5.0, parent_atp_cost=1.0)

    result = reproduce(parent, config, MutationConfig(bit_flip_rate=0.0), seed=7)

    assert not result.succeeded
    assert "alive_result_required" in result.decision.reasons


def test_failed_alive_result_blocks_reproduction() -> None:
    parent = GenesisOrganism.from_bits("parent", "111", initial_runtime_atp=20.0)
    config = ReproductionConfig(min_runtime_atp=5.0, parent_atp_cost=1.0)

    result = reproduce(
        parent,
        config,
        MutationConfig(bit_flip_rate=0.0),
        alive_result=_alive(passed=False),
        seed=8,
    )

    assert not result.succeeded
    assert "alive_gate_not_passed" in result.decision.reasons
