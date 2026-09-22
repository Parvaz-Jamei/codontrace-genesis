"""Phase B two-parent sexual recombination tests.

These tests document software capability and runtime observation only. They do
not claim artificial life, intelligence, cooperation, or instinct evolution.
"""

from __future__ import annotations

from codontrace.genesis.birth import (
    BirthChamberState,
    InheritancePolicy,
    MutationOperator,
    RecombinationRecord,
    ReproductionMode,
    SexualRecombinationConfig,
    apply_positional_segment_exchange,
    apply_positional_segment_swap,
    recombine_positional_segment,
    select_chamber_pair,
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


def test_positional_segment_exchange_returns_reciprocal_products() -> None:
    child_a, child_b = apply_positional_segment_exchange(PARENT_A_BITS, PARENT_B_BITS, 3, 6)
    assert child_a == "101000000"
    assert child_b == "000111111"
    assert child_a[3:6] == PARENT_B_BITS[3:6]
    assert child_b[3:6] == PARENT_A_BITS[3:6]
    assert child_a[:3] == PARENT_A_BITS[:3]
    assert child_b[:3] == PARENT_B_BITS[:3]


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
    assert "sexual_recombination" not in spec.population_configs.to_dict()
    assert spec.population_configs.sexual_recombination.enabled is False


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
    assert spec.population_configs.sexual_recombination.enabled is True
    assert spec.population_configs.sexual_recombination.uses_birth_chamber is True
    assert spec.population_configs.sexual_recombination.recombination_prob == 1.0
    assert spec.metadata["sexual_pairing"] == "birth_chamber"
    assert spec.metadata["phase_b1_diploid_meiosis"] == "deferred"
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
    assert observation.births >= 1
    assert (
        observation.adjacent_or_displaced_births + observation.same_cell_births
        >= observation.births
    )
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
    assert rec.recombination_digest
    assert rec.recombination_start_index is not None
    assert rec.recombination_end_index is not None
    assert rec.recombination_end_index > rec.recombination_start_index
    if any(item.recombination_window_differed for item in sexual_lineage):
        assert observation.recombinant_child_pairs >= 1


def _chamber_configs(**sexual_overrides: object) -> PopulationConfigs:
    sexual_payload: dict[str, object] = {
        "enabled": True,
        "recombination_prob": 1.0,
        "chamber_capacity": 8,
        "same_length_only": False,
        "two_fold_cost_sex": False,
        "timeout_policy": "asexual_fallback",
        "pairing_policy": "birth_chamber",
    }
    sexual_payload.update(sexual_overrides)
    return PopulationConfigs(
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
        sexual_recombination=SexualRecombinationConfig(**sexual_payload),  # type: ignore[arg-type]
    )


def test_step_population_sexual_uses_birth_chamber_and_reciprocal_swap() -> None:
    world = World2D(4, 4)
    parent_a = GenesisOrganism.from_bits(
        "a", "111000000", initial_runtime_atp=20.0, position=(1, 1)
    )
    parent_b = GenesisOrganism.from_bits(
        "b", "111111000", initial_runtime_atp=20.0, position=(1, 2)
    )
    born = step_population(
        PopulationState(0, 0, (parent_a, parent_b), (), ()),
        world,
        _chamber_configs(),
        seed=5,
    )
    sexual = [record for record in born.population.lineage if record.second_parent_id]
    assert born.births == 2
    assert len(sexual) == 2
    assert {record.parent_id for record in sexual} == {"a", "b"}
    assert {record.second_parent_id for record in sexual} == {"a", "b"}
    recs = [
        item.reproduction_result.recombination_record
        for item in born.organism_records
        if item.reproduction_result is not None
        and item.reproduction_result.recombination_record is not None
    ]
    assert recs
    recon = recs[0]
    mosaic = recon.child_genome_bits
    assert mosaic[recon.start_index : recon.end_index] == recon.parent_b_bits[
        recon.start_index : recon.end_index
    ]
    reciprocal_a, reciprocal_b = apply_positional_segment_exchange(
        recon.parent_a_bits, recon.parent_b_bits, recon.start_index, recon.end_index
    )
    child_bits = {item.genome.to_compact() for item in born.population.organisms}
    assert reciprocal_a in child_bits
    assert reciprocal_b in child_bits
    assert born.population.birth_chamber.is_empty


def test_birth_chamber_two_fold_cost_places_only_one_recombinant() -> None:
    world = World2D(4, 4)
    parent_a = GenesisOrganism.from_bits(
        "a", "111000000", initial_runtime_atp=20.0, position=(0, 0)
    )
    parent_b = GenesisOrganism.from_bits(
        "b", "111111000", initial_runtime_atp=20.0, position=(0, 1)
    )
    born = step_population(
        PopulationState(0, 0, (parent_a, parent_b), (), ()),
        world,
        _chamber_configs(two_fold_cost_sex=True),
        seed=8,
    )
    assert born.births == 1
    sexual = [record for record in born.population.lineage if record.second_parent_id]
    assert len(sexual) == 1
    assert sexual[0].parent_ids == ("a", "b") or sexual[0].parent_id in {"a", "b"}


def test_birth_chamber_recombination_prob_zero_places_asexual_copies() -> None:
    world = World2D(4, 4)
    parent_a = GenesisOrganism.from_bits(
        "a", "111000000", initial_runtime_atp=20.0, position=(0, 0)
    )
    parent_b = GenesisOrganism.from_bits(
        "b", "111111000", initial_runtime_atp=20.0, position=(0, 1)
    )
    born = step_population(
        PopulationState(0, 0, (parent_a, parent_b), (), ()),
        world,
        _chamber_configs(recombination_prob=0.0),
        seed=8,
    )
    assert born.births == 2
    assert all(record.second_parent_id is None for record in born.population.lineage)
    child_bits = {
        item.genome.to_compact()
        for item in born.population.organisms
        if item.id not in {"a", "b"}
    }
    assert "111000000" in child_bits
    assert "111111000" in child_bits


def test_birth_chamber_same_length_only_leaves_unequal_genomes_waiting() -> None:
    world = World2D(4, 4)
    parent_a = GenesisOrganism.from_bits(
        "a", "111000000", initial_runtime_atp=20.0, position=(0, 0)
    )
    parent_b = GenesisOrganism.from_bits(
        "b", "111000000111", initial_runtime_atp=20.0, position=(0, 1)
    )
    born = step_population(
        PopulationState(0, 0, (parent_a, parent_b), (), ()),
        world,
        _chamber_configs(same_length_only=True),
        seed=4,
    )
    assert born.births == 0
    assert len(born.population.birth_chamber.waiting) == 2
    pair = select_chamber_pair(
        born.population.birth_chamber.waiting, same_length_only=True
    )
    assert pair is None


def test_birth_chamber_capacity_blocks_overflow() -> None:
    world = World2D(4, 4)
    parent_a = GenesisOrganism.from_bits(
        "a", "111000000", initial_runtime_atp=20.0, position=(0, 0)
    )
    parent_b = GenesisOrganism.from_bits(
        "b", "111111000", initial_runtime_atp=20.0, position=(0, 1)
    )
    born = step_population(
        PopulationState(0, 0, (parent_a, parent_b), (), ()),
        world,
        _chamber_configs(chamber_capacity=1),
        seed=4,
    )
    assert born.births == 0
    assert len(born.population.birth_chamber.waiting) == 1
    reasons = [
        event.world_delta.get("reproduction_blocked_reason")
        for trace in born.traces
        for event in trace.events
        if event.action == "COPY_SELF"
    ]
    assert "birth_chamber_full" in reasons


def test_birth_chamber_timeout_fail_discards_unpaired_genome() -> None:
    world = World2D(4, 4)
    parent_a = GenesisOrganism.from_bits(
        "a", "111000000", initial_runtime_atp=20.0, position=(0, 0)
    )
    waiter = GenesisOrganism.from_bits(
        "z", "000000000", initial_runtime_atp=20.0, position=(2, 2)
    )
    born = step_population(
        PopulationState(0, 0, (parent_a, waiter), (), ()),
        world,
        _chamber_configs(max_birth_wait_ticks=0, timeout_policy="fail"),
        seed=4,
    )
    assert born.births == 0
    assert born.population.birth_chamber.is_empty
    assert born.blocked_reproduction >= 1


def test_birth_chamber_timeout_asexual_fallback_places_copy() -> None:
    world = World2D(4, 4)
    parent_a = GenesisOrganism.from_bits(
        "a", "111000000", initial_runtime_atp=20.0, position=(0, 0)
    )
    waiter = GenesisOrganism.from_bits(
        "z", "000000000", initial_runtime_atp=20.0, position=(2, 2)
    )
    born = step_population(
        PopulationState(0, 0, (parent_a, waiter), (), ()),
        world,
        _chamber_configs(max_birth_wait_ticks=0, timeout_policy="asexual_fallback"),
        seed=4,
    )
    assert born.births == 1
    child = next(item for item in born.population.organisms if item.id not in {"a", "z"})
    assert child.genome.to_compact() == "111000000"
    assert all(record.second_parent_id is None for record in born.population.lineage)


def test_asexual_population_configs_omit_sexual_recombination() -> None:
    configs = PopulationConfigs()
    assert "sexual_recombination" not in configs.to_dict()
    restored = PopulationConfigs.from_dict(configs.to_dict())
    assert restored.sexual_recombination.enabled is False
    empty = BirthChamberState()
    assert "birth_chamber" not in PopulationState(0, 0, (), (), (), empty).to_dict()


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
