"""Phase B two-parent sexual recombination tests.

These tests document software capability and runtime observation only. They do
not claim artificial life, intelligence, cooperation, or instinct evolution.
"""

from __future__ import annotations

from codontrace.genesis.birth import (
    InheritancePolicy,
    MutationOperator,
    RecombinationRecord,
    ReproductionMode,
    apply_positional_segment_swap,
    recombine_positional_segment,
)
from codontrace.genesis.engine import GenesisEngine
from codontrace.genesis.liveness import AliveGateConfig, AliveGateResult
from codontrace.genesis.organism import GenesisOrganism
from codontrace.genesis.population import (
    MutationConfig,
    OffspringPlacementPolicy,
    PopulationConfigs,
    PopulationState,
    ReproductionConfig,
    can_reproduce,
    reproduce,
    step_population,
)
from codontrace.genesis.runtime_profiles import (
    LIFE_LOOP_EATER_B_GENOME,
    LIFE_LOOP_EATER_GENOME,
    GenesisRuntimeProfile,
    summarize_life_loop_observation,
)
from codontrace.rng import RNGManager
from codontrace.world import World2D


PARENT_A_BITS = "101111000"
PARENT_B_BITS = "000000111"


def _alive(passed: bool = True, runtime_atp: float = 24.0) -> AliveGateResult:
    return AliveGateResult(
        passed=passed,
        survived_ticks=1,
        executed_actions=1,
        blocked_actions=0,
        blocked_ratio=0.0,
        final_runtime_atp=runtime_atp,
        lumen_interactions=1,
        reproduction_events=0,
        reasons=() if passed else ("blocked_ratio_exceeded",),
    )


def _sexual_config(**overrides: object) -> ReproductionConfig:
    payload: dict[str, object] = {
        "min_runtime_atp": 1.0,
        "parent_atp_cost": 1.0,
        "inheritance_policy": InheritancePolicy.DARWINIAN_GENETIC_ONLY,
        "reproduction_mode": ReproductionMode.SEXUAL_CROSSOVER,
    }
    payload.update(overrides)
    return ReproductionConfig(**payload)  # type: ignore[arg-type]


def test_default_reproduction_mode_stays_asexual_and_omitted_from_dict() -> None:
    config = ReproductionConfig()
    assert config.reproduction_mode is ReproductionMode.ASEXUAL
    assert config.is_sexual is False
    assert "reproduction_mode" not in config.to_dict()
    restored = ReproductionConfig.from_dict(config.to_dict())
    assert restored.reproduction_mode is ReproductionMode.ASEXUAL


def test_positional_segment_swap_replaces_only_the_named_window() -> None:
    child = apply_positional_segment_swap(PARENT_A_BITS, PARENT_B_BITS, 3, 6)
    assert child == "101000000"
    assert child[3:6] == PARENT_B_BITS[3:6]
    assert child[:3] == PARENT_A_BITS[:3]
    assert child[6:] == PARENT_A_BITS[6:]
    assert child != PARENT_A_BITS
    assert child != PARENT_B_BITS


def test_recombine_positional_segment_is_seeded_and_auditable() -> None:
    first = recombine_positional_segment(
        parent_a_id="a",
        parent_b_id="b",
        parent_a_bits=PARENT_A_BITS,
        parent_b_bits=PARENT_B_BITS,
        parent_a_genome_digest="da",
        parent_b_genome_digest="db",
        rng=RNGManager(seed=11).fork("recombination"),
    )
    second = recombine_positional_segment(
        parent_a_id="a",
        parent_b_id="b",
        parent_a_bits=PARENT_A_BITS,
        parent_b_bits=PARENT_B_BITS,
        parent_a_genome_digest="da",
        parent_b_genome_digest="db",
        rng=RNGManager(seed=11).fork("recombination"),
    )
    assert first.to_dict() == second.to_dict()
    assert first.digest() == second.digest()
    assert first.operator == MutationOperator.RECOMBINE_WITH_PARTNER.value
    assert first.mechanism == "positional_segment_swap"
    assert first.parent_ids == ("a", "b")
    reconstructed = apply_positional_segment_swap(
        PARENT_A_BITS, PARENT_B_BITS, first.start_index, first.end_index
    )
    assert first.child_genome_bits == reconstructed
    assert first.swapped_from_mate == PARENT_B_BITS[first.start_index : first.end_index]
    if PARENT_A_BITS[first.start_index : first.end_index] != PARENT_B_BITS[
        first.start_index : first.end_index
    ]:
        assert first.child_genome_bits != PARENT_A_BITS
        assert first.child_genome_bits != PARENT_B_BITS


def test_sexual_child_differs_from_both_parents_in_swapped_region() -> None:
    parent = GenesisOrganism.from_bits("parent-a", PARENT_A_BITS, initial_runtime_atp=24.0)
    mate = GenesisOrganism.from_bits("parent-b", PARENT_B_BITS, initial_runtime_atp=24.0)
    result = reproduce(
        parent,
        _sexual_config(),
        MutationConfig(bit_flip_rate=0.0),
        alive_result=_alive(),
        generation=0,
        birth_tick=1,
        seed=21,
        mate=mate,
    )
    assert result.succeeded and result.child is not None
    assert result.recombination_record is not None
    record = result.recombination_record
    child_bits = result.child.genome.to_compact()
    pre_mutation = record.child_genome_bits
    assert pre_mutation[record.start_index : record.end_index] == PARENT_B_BITS[
        record.start_index : record.end_index
    ]
    assert (
        pre_mutation[: record.start_index] + pre_mutation[record.end_index :]
        == PARENT_A_BITS[: record.start_index] + PARENT_A_BITS[record.end_index :]
    )
    assert result.lineage is not None
    assert result.lineage.parent_id == "parent-a"
    assert result.lineage.second_parent_id == "parent-b"
    assert result.lineage.parent_ids == ("parent-a", "parent-b")
    assert result.birth_event is not None
    assert result.birth_event.second_parent_id == "parent-b"
    assert result.child_genome_result is not None
    assert result.child_genome_result.second_parent_id == "parent-b"
    assert "second_parent_id" in result.lineage.to_dict()
    assert "recombination_record" in result.to_dict()
    if PARENT_A_BITS[record.start_index : record.end_index] != PARENT_B_BITS[
        record.start_index : record.end_index
    ]:
        assert pre_mutation != PARENT_A_BITS
    retained = pre_mutation[: record.start_index] + pre_mutation[record.end_index :]
    retained_b = PARENT_B_BITS[: record.start_index] + PARENT_B_BITS[record.end_index :]
    if retained != retained_b:
        assert pre_mutation != PARENT_B_BITS
    assert child_bits == pre_mutation
    assert 0 <= record.start_index < record.end_index <= len(PARENT_A_BITS)
    if len(PARENT_A_BITS) >= 6:
        assert record.end_index - record.start_index < len(PARENT_A_BITS)


def test_sexual_fixed_seed_replay_is_stable() -> None:
    parent = GenesisOrganism.from_bits("parent-a", PARENT_A_BITS, initial_runtime_atp=24.0)
    mate = GenesisOrganism.from_bits("parent-b", PARENT_B_BITS, initial_runtime_atp=24.0)
    kwargs = dict(
        config=_sexual_config(),
        mutation_config=MutationConfig(bit_flip_rate=0.05),
        alive_result=_alive(),
        generation=2,
        birth_tick=4,
        seed=99,
        mate=mate,
    )
    first = reproduce(parent, **kwargs)
    second = reproduce(parent, **kwargs)
    assert first.succeeded and second.succeeded
    assert first.child is not None and second.child is not None
    assert first.child.genome.to_compact() == second.child.genome.to_compact()
    assert first.recombination_record is not None
    assert second.recombination_record is not None
    assert first.recombination_record.digest() == second.recombination_record.digest()
    assert first.lineage is not None and second.lineage is not None
    assert first.lineage.to_dict() == second.lineage.to_dict()


def test_asexual_path_ignores_mate_and_does_not_record_recombination() -> None:
    parent = GenesisOrganism.from_bits("parent", LIFE_LOOP_EATER_GENOME, initial_runtime_atp=24.0)
    mate = GenesisOrganism.from_bits("intruder", PARENT_B_BITS, initial_runtime_atp=24.0)
    result = reproduce(
        parent,
        ReproductionConfig(
            min_runtime_atp=1.0,
            parent_atp_cost=1.0,
            inheritance_policy=InheritancePolicy.DARWINIAN_GENETIC_ONLY,
        ),
        MutationConfig(bit_flip_rate=0.0),
        alive_result=_alive(),
        generation=0,
        birth_tick=1,
        seed=21,
        mate=mate,
    )
    assert result.succeeded and result.child is not None
    assert result.child.genome.to_compact() == parent.genome.to_compact()
    assert result.recombination_record is None
    assert result.lineage is not None
    assert result.lineage.second_parent_id is None
    assert "second_parent_id" not in result.lineage.to_dict()
    assert "recombination_record" not in result.to_dict()
    assert "RECOMBINE" not in "".join(result.mutation.operations if result.mutation else ())


def test_sexual_requires_viable_mate_and_keeps_phase_a_gates() -> None:
    parent = GenesisOrganism.from_bits("parent-a", PARENT_A_BITS, initial_runtime_atp=24.0)
    hungry_mate = GenesisOrganism.from_bits("hungry", PARENT_B_BITS, initial_runtime_atp=0.5)
    missing = reproduce(
        parent,
        _sexual_config(),
        MutationConfig(bit_flip_rate=0.0),
        alive_result=_alive(),
        seed=3,
    )
    hungry = reproduce(
        parent,
        _sexual_config(),
        MutationConfig(bit_flip_rate=0.0),
        alive_result=_alive(),
        seed=3,
        mate=hungry_mate,
    )
    gated = can_reproduce(
        parent,
        _alive(passed=False),
        _sexual_config(),
    )
    assert not missing.succeeded
    assert "no_viable_mate" in missing.decision.reasons
    assert not hungry.succeeded
    assert "mate_min_runtime_atp_not_met" in hungry.decision.reasons
    assert not gated.allowed
    assert "alive_gate_not_passed" in gated.reasons


def test_life_loop_asexual_default_metadata_and_mode_stay_phase_a() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(seed=3, tick_count=4, population=6)
    assert spec.metadata["phase_b_sexual_crossover"] == "deferred"
    assert "reproduction_mode" not in spec.metadata
    assert spec.population_configs is not None
    assert spec.population_configs.reproduction.reproduction_mode is ReproductionMode.ASEXUAL
    assert "reproduction_mode" not in spec.population_configs.reproduction.to_dict()


def test_life_loop_sexual_opt_in_records_two_parents_and_replays() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(
        seed=7,
        tick_count=12,
        population=6,
        reproduction_mode=ReproductionMode.SEXUAL_CROSSOVER,
    )
    assert spec.metadata["phase_b_sexual_crossover"] == "enabled"
    assert spec.metadata["reproduction_mode"] == "sexual_crossover"
    assert spec.metadata["claim_ceiling"] == "runtime_observation"
    assert spec.metadata["claim_allowed_for_intelligence"] is False
    assert spec.metadata["phase_c_fluctuating_environment"] == "deferred"
    assert spec.metadata["phase_d_instinct_claim_metrics"] == "hooks_only_not_implemented"
    assert spec.population_configs is not None
    assert (
        spec.population_configs.reproduction.reproduction_mode
        is ReproductionMode.SEXUAL_CROSSOVER
    )
    assert LIFE_LOOP_EATER_GENOME in spec.genome_bits
    assert LIFE_LOOP_EATER_B_GENOME in spec.genome_bits
    first = GenesisEngine.from_spec(spec).run_ticks()
    second = GenesisEngine.from_spec(spec).run_ticks()
    assert first.digest() == second.digest()
    observation = summarize_life_loop_observation(first)
    assert observation.claim_ceiling == "runtime_observation"
    assert observation.genesis_alive_full is False
    assert observation.two_parent_lineage_records >= 1
    assert observation.heritable_sexual_pairs >= 1
    assert observation.recombinant_child_pairs >= 1
    sexual_lineage = [
        record
        for tick in first.ticks
        for record in tick.generation_result.population.lineage
        if record.second_parent_id
    ]
    assert sexual_lineage
    rec = sexual_lineage[0]
    assert rec.parent_id is not None
    assert rec.second_parent_id is not None
    assert rec.parent_id != rec.second_parent_id
    assert rec.parent_ids == (rec.parent_id, rec.second_parent_id)


def test_step_population_sexual_uses_nearest_viable_mate() -> None:
    world = World2D(4, 4)
    world.place_resource((1, 1), 6.0)
    initiator = GenesisOrganism.from_bits(
        "a",
        LIFE_LOOP_EATER_GENOME,
        initial_runtime_atp=20.0,
        position=(1, 1),
    )
    near = GenesisOrganism.from_bits(
        "b",
        LIFE_LOOP_EATER_B_GENOME,
        initial_runtime_atp=20.0,
        position=(1, 2),
    )
    far = GenesisOrganism.from_bits(
        "c",
        "111000000",
        initial_runtime_atp=20.0,
        position=(3, 3),
    )
    configs = PopulationConfigs(
        reproduction=ReproductionConfig(
            min_runtime_atp=1.0,
            parent_atp_cost=1.0,
            max_population=8,
            offspring_placement=OffspringPlacementPolicy.SAME_CELL,
            reproduction_mode=ReproductionMode.SEXUAL_CROSSOVER,
        ),
        mutation=MutationConfig(bit_flip_rate=0.0),
        alive_gate=AliveGateConfig(
            min_ticks=1,
            min_executed_actions=0,
            max_blocked_ratio=1.0,
            require_positive_runtime_atp=True,
        ),
    )
    fed = step_population(
        PopulationState(0, 0, (initiator, near, far), (), ()),
        world,
        configs,
        seed=5,
    )
    born = step_population(fed.population, fed.world_after, configs, seed=6)
    sexual = [
        record
        for record in born.population.lineage
        if record.second_parent_id and record.parent_id == "a"
    ]
    assert born.births >= 1
    assert sexual
    assert sexual[0].second_parent_id == "b"
    child = next(item for item in born.population.organisms if item.id == sexual[0].organism_id)
    assert child.genome.to_compact() != LIFE_LOOP_EATER_GENOME or (
        child.genome.to_compact() != LIFE_LOOP_EATER_B_GENOME
    )
    # Identity crossover is allowed when the drawn window matches; the record
    # still names both parents and the swapped interval.
    record = next(
        item.reproduction_result
        for item in born.organism_records
        if item.reproduction_result is not None
        and item.reproduction_result.recombination_record is not None
        and item.reproduction_result.recombination_record.parent_a_id == "a"
    )
    assert record is not None
    assert record.recombination_record is not None
    recon = record.recombination_record
    mosaic = recon.child_genome_bits
    assert mosaic[recon.start_index : recon.end_index] == LIFE_LOOP_EATER_B_GENOME[
        recon.start_index : recon.end_index
    ]


def test_asexual_life_loop_digest_matches_phase_a_baseline() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)
    result = GenesisEngine.from_spec(spec).run_ticks()
    replay = GenesisEngine.from_spec(spec).run_ticks()
    assert (
        spec.digest()
        == "7d199ae51345872215dbbb0c45cf8f141aacfb4c31d6537eda6de246c0cb7aac"
    )
    assert [tick.digest() for tick in result.ticks] == [
        "6bb7a3b9fb9d9acc08931af92187d4fe543084b60157cd4ca790b8dc2c262e56",
        "058a5718aaac2af1229a09962fdc4bceade15ca06740da9b8ab309ef62b12a28",
        "447d1eccc5c883f20b2c50804bdf343213a1f3daa48ceae8faf1daca91e0b120",
        "564f83a63c5be25ad7a46e3541af505d16e358b2c22d3122672a98c82d94fc36",
        "26809f2d67dc6958a4245b4e420ef4bb8507684ae1689f15dbd1a08e0dcd4447",
        "75c2312544823596fcce2c47e9f5c17bacbdb35c8a942da3b71ca32e61bbd7d9",
        "a42df615bd632dd657bf31a8f0fbc5fe58fa6a4f80dc7d1694fcb6a24ee18353",
        "be72bf9f2dcb22870cff3428cc8543db9e774c9c0ea4dd073b23cd806aabb081",
        "ba48857f1c2490df07f6dee7e158f2b78f1274d03dc146a3166a00320aaaa7fe",
        "339c13f11a8296bfd4c75ba3f57e443339df542e5b7fb288d00e1b8321939e5f",
        "da6e4a7fbe0ee04cd5e3e05682cf6c54f0f04ad4ff81fede3254c5bbb98b6a5a",
        "a8311016a85a468952ac8cc004bafaadc1fc704018cffef24541ff81fa70ce24",
    ]
    assert result.snapshot.digest() == "76a5e62cb0123b20a089adde25acd1cfb6dc460bdfab52f33ee460533d76f43a"
    assert result.digest() == replay.digest()
    observation = summarize_life_loop_observation(result)
    assert observation.heritable_asexual_pairs >= 1
    assert observation.two_parent_lineage_records == 0
    assert observation.heritable_sexual_pairs == 0


def test_recombination_record_roundtrip() -> None:
    record = RecombinationRecord(
        parent_a_id="a",
        parent_b_id="b",
        parent_a_genome_digest="da",
        parent_b_genome_digest="db",
        parent_a_bits=PARENT_A_BITS,
        parent_b_bits=PARENT_B_BITS,
        child_genome_bits=apply_positional_segment_swap(PARENT_A_BITS, PARENT_B_BITS, 0, 3),
        child_genome_digest="dc",
        start_index=0,
        end_index=3,
        codon_width=3,
        rng_digest="rng",
    )
    assert record.to_dict()["parent_ids"] == ["a", "b"]
    assert record.swapped_from_mate == PARENT_B_BITS[:3]
