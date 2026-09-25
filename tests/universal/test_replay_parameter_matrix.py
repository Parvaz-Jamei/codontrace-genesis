"""Replay and parameter identity of the general population motor."""

from __future__ import annotations

from pathlib import Path

import pytest

from codontrace.genesis import (
    AliveGateConfig,
    FitnessConfig,
    MutationConfig,
    PopulationConfigs,
    PopulationRunner,
    PopulationState,
    ReproductionConfig,
    mutate_genome,
    step_population,
)
from codontrace.genesis.host_parasite_life_plugin import ClosedLoopHPLifeConfig
from codontrace.genesis.organism import GenesisOrganism
from codontrace.genome import SemanticGenome
from codontrace.world import World2D

SEED = 11
MUTATION_SEED = 17
GENOME_BITS = "000111010011"
ENGINE_PATH = Path(__file__).resolve().parents[2] / "src" / "codontrace" / "engine.py"
FORBIDDEN_ENGINE_SUBSTRINGS = ("outcross", "kappa", "host_parasite", "BitSpan")


def _configs() -> PopulationConfigs:
    return PopulationConfigs(
        reproduction=ReproductionConfig(
            min_runtime_atp=1.0,
            parent_atp_cost=0.5,
            max_population=8,
            offspring_atp_fraction=0.1,
        ),
        mutation=MutationConfig(bit_flip_rate=0.5, insertion_rate=0.0, deletion_rate=0.0),
        fitness=FitnessConfig(),
        alive_gate=AliveGateConfig(
            min_ticks=1,
            min_executed_actions=0,
            max_blocked_ratio=1.0,
            require_positive_runtime_atp=False,
        ),
        ticks_per_generation=1,
    )


def _fresh_start() -> tuple[PopulationState, World2D]:
    organism = GenesisOrganism.from_bits(
        "org",
        "111001010011",
        initial_runtime_atp=20.0,
        position=(1, 1),
    )
    population = PopulationState(generation=0, tick=0, organisms=(organism,), lineage=(), fitness=())
    return population, World2D(5, 5)


def _organism_view(result: object) -> tuple[tuple[str, str, float, float], ...]:
    population = result.population  # type: ignore[attr-defined]
    return tuple(
        (
            organism.id,
            organism.genome.to_compact(),
            organism.atp_state.runtime_available,
            organism.atp_state.learning_available,
        )
        for organism in population.organisms
    )


def _step_digests(result: object) -> dict[str, str]:
    return {
        "population": result.population.digest(),  # type: ignore[attr-defined]
        "generation": result.digest(),  # type: ignore[attr-defined]
        "world": result.world_after.digest(),  # type: ignore[attr-defined]
    }


def _runner_from_same_start(runner: PopulationRunner) -> PopulationRunner:
    nexus = runner.nexus_layer
    return PopulationRunner(
        population=PopulationState.from_dict(runner.population.to_dict()),
        world=runner.world.clone(),
        configs=runner.configs,
        nexus_layer=None if nexus is None else type(nexus).from_dict(nexus.to_dict()),
    )


def test_step_population_replay_matches_ids_genomes_and_atp() -> None:
    configs = _configs()
    population_a, world_a = _fresh_start()
    population_b, world_b = _fresh_start()

    first = step_population(population_a, world_a, configs, seed=SEED)
    second = step_population(population_b, world_b, configs, seed=SEED)

    assert _organism_view(first) == _organism_view(second)
    assert _step_digests(first) == _step_digests(second)


def test_successive_step_population_seeds_match_runner() -> None:
    """Seeds s, s+1, s+2 on step_population match PopulationRunner.step_generation."""

    configs = _configs()
    seeds = (SEED, SEED + 1, SEED + 2)
    population, world = _fresh_start()
    direct_views = []
    direct_digests = []
    for seed in seeds:
        result = step_population(population, world, configs, seed=seed)
        direct_views.append(_organism_view(result))
        direct_digests.append(_step_digests(result))
        population, world = result.population, result.world_after

    population, world = _fresh_start()
    runner = PopulationRunner(population=population, world=world, configs=configs)
    runner_views = []
    runner_digests = []
    for seed in seeds:
        result = runner.step_generation(seed=seed)
        runner_views.append(_organism_view(result))
        runner_digests.append(_step_digests(result))

    assert runner_views == direct_views, (
        f"runner views={runner_views} step_population views={direct_views} "
        f"runner_digests={runner_digests} step_population_digests={direct_digests}"
    )
    assert runner_digests == direct_digests


def test_successive_seeds_match_runners_from_same_start() -> None:
    configs = _configs()
    seeds = (SEED, SEED + 1, SEED + 2)
    population, world = _fresh_start()
    sequential = PopulationRunner(population=population, world=world, configs=configs)
    sequential_views = []
    sequential_digests = []
    rebuilt_views = []
    rebuilt_digests = []
    for seed in seeds:
        rebuilt = _runner_from_same_start(sequential)
        rebuilt_result = rebuilt.step_generation(seed=seed)
        sequential_result = sequential.step_generation(seed=seed)
        rebuilt_views.append(_organism_view(rebuilt_result))
        rebuilt_digests.append(_step_digests(rebuilt_result))
        sequential_views.append(_organism_view(sequential_result))
        sequential_digests.append(_step_digests(sequential_result))

    assert sequential_views == rebuilt_views, (
        f"sequential_views={sequential_views} same_start_views={rebuilt_views} "
        f"sequential_digests={sequential_digests} same_start_digests={rebuilt_digests}"
    )
    assert sequential_digests == rebuilt_digests


def test_later_seeds_keep_carried_state() -> None:
    """Seed N+1 on one runner must not match a fresh runner given only that seed.

    A fresh runner starts from generation 0. The successive runner has already
    applied seed N. Those are different states. The first step still matches.
    """

    configs = _configs()
    seeds = (SEED, SEED + 1, SEED + 2)
    population, world = _fresh_start()
    sequential = PopulationRunner(population=population, world=world, configs=configs)
    sequential_views = []
    for seed in seeds:
        sequential_views.append(_organism_view(sequential.step_generation(seed=seed)))

    fresh_views = []
    for seed in seeds:
        fresh_population, fresh_world = _fresh_start()
        fresh_result = PopulationRunner(
            population=fresh_population, world=fresh_world, configs=configs
        ).step_generation(seed=seed)
        stepped = step_population(*_fresh_start(), configs, seed=seed)
        assert _organism_view(fresh_result) == _organism_view(stepped)
        fresh_views.append(_organism_view(fresh_result))

    assert sequential_views[0] == fresh_views[0]
    assert sequential_views[1] != fresh_views[1]
    assert sequential_views[2] != fresh_views[2]


def test_indel_rates_zero_do_not_change_genome_length() -> None:
    genome = SemanticGenome.from_compact(GENOME_BITS)
    before = len(genome.to_compact())
    result = mutate_genome(
        genome,
        MutationConfig(bit_flip_rate=1.0, insertion_rate=0.0, deletion_rate=0.0),
        seed=MUTATION_SEED,
    )
    after = len(result.mutated_genome.to_compact())
    assert after == before, (
        f"before={before} after={after} operations={result.operations} seed={MUTATION_SEED}"
    )


def _length_after_indels(insertion_rate: float, deletion_rate: float) -> tuple[object, ...]:
    genome = SemanticGenome.from_compact(GENOME_BITS)
    before = len(genome.to_compact())
    codon_width = genome.spec.codon_width
    try:
        result = mutate_genome(
            genome,
            MutationConfig(
                bit_flip_rate=0.0,
                insertion_rate=insertion_rate,
                deletion_rate=deletion_rate,
            ),
            seed=MUTATION_SEED,
        )
    except Exception as exc:
        return ("raised", type(exc).__name__, str(exc), before, codon_width)
    after = len(result.mutated_genome.to_compact())
    return ("returned", before, after, after - before, codon_width, result.operations)


@pytest.mark.parametrize(
    ("insertion_rate", "deletion_rate"),
    [(1.0, 0.0), (0.0, 1.0), (1.0, 1.0)],
)
def test_indel_rate_one_applies_each_codon_edit(
    insertion_rate: float, deletion_rate: float
) -> None:
    outcome = _length_after_indels(insertion_rate, deletion_rate)
    assert outcome[0] == "returned", outcome
    _status, _before, _after, delta, codon_width, operations = outcome
    inserts = sum(1 for op in operations if str(op).startswith("insert:"))
    deletes = sum(1 for op in operations if str(op).startswith("delete:"))
    assert inserts == (1 if insertion_rate == 1.0 else 0)
    assert deletes == (1 if deletion_rate == 1.0 else 0)
    assert delta == codon_width * (inserts - deletes), (
        f"insertion_rate={insertion_rate} deletion_rate={deletion_rate} seed={MUTATION_SEED} "
        f"delta={delta} codon_width={codon_width} operations={operations}"
    )


def test_default_closed_loop_hp_life_omitted_unless_enabled() -> None:
    default_payload = PopulationConfigs().to_dict()
    assert "closed_loop_hp_life" not in default_payload, (
        f"default PopulationConfigs.to_dict keys include closed_loop_hp_life: "
        f"{default_payload.get('closed_loop_hp_life')!r}"
    )

    explicit_default = PopulationConfigs(closed_loop_hp_life=ClosedLoopHPLifeConfig()).to_dict()
    assert "closed_loop_hp_life" not in explicit_default

    enabled_payload = PopulationConfigs(
        closed_loop_hp_life=ClosedLoopHPLifeConfig(enabled=True)
    ).to_dict()
    assert "closed_loop_hp_life" in enabled_payload
    assert enabled_payload["closed_loop_hp_life"]["enabled"] is True  # type: ignore[index]


def test_engine_source_excludes_specialized_substrings() -> None:
    assert ENGINE_PATH.is_file(), f"missing {ENGINE_PATH}"
    source = ENGINE_PATH.read_text(encoding="utf-8")
    found = {
        needle: source.find(needle)
        for needle in FORBIDDEN_ENGINE_SUBSTRINGS
        if needle in source
    }
    assert not found, f"engine.py contains forbidden substrings at offsets {found}"
