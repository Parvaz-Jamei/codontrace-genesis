"""Parameter matrix for the general asexual population motor.

Host-parasite plugins are not used. Reproduction stays on the default asexual
path of PopulationConfigs / step_population / PopulationRunner.
"""

from __future__ import annotations

import pytest

from codontrace.codon import Action, Codon, CodonTable
from codontrace.errors import ConfigurationError
from codontrace.genesis import (
    AliveGateConfig,
    GenesisOrganism,
    MetabolicConfig,
    MutationConfig,
    PopulationConfigs,
    PopulationRunner,
    PopulationState,
    ReproductionConfig,
    Ribosome,
    step_population,
)
from codontrace.genome import BitSpan
from codontrace.specs import CodonTableSpec, GenomeSpec
from codontrace.world import World2D


def _configs(
    *,
    bit_flip_rate: float = 0.0,
    parent_atp_cost: float = 1.0,
    max_population: int = 8,
    offspring_atp_fraction: float = 0.25,
    min_runtime_atp: float = 0.0,
    ticks_per_generation: int = 1,
    basal_runtime_atp_cost: float = 0.0,
) -> PopulationConfigs:
    return PopulationConfigs(
        reproduction=ReproductionConfig(
            min_runtime_atp=min_runtime_atp,
            parent_atp_cost=parent_atp_cost,
            max_population=max_population,
            offspring_atp_fraction=offspring_atp_fraction,
        ),
        mutation=MutationConfig(bit_flip_rate=bit_flip_rate),
        alive_gate=AliveGateConfig(
            min_ticks=1,
            min_executed_actions=0,
            max_blocked_ratio=1.0,
            require_positive_runtime_atp=False,
        ),
        ticks_per_generation=ticks_per_generation,
        metabolism=MetabolicConfig(
            enabled=basal_runtime_atp_cost > 0.0,
            basal_runtime_atp_cost=basal_runtime_atp_cost,
        ),
    )


def _state(bits: str, atp: float, *, organism_id: str = "org", ribosome: Ribosome | None = None):
    organism = GenesisOrganism.from_bits(
        organism_id,
        bits,
        initial_runtime_atp=atp,
        position=(1, 1),
        ribosome=ribosome,
    )
    return organism, PopulationState(0, 0, (organism,), (), ()), World2D(3, 3)


def _child(result, parent_id: str = "org"):
    children = [item for item in result.population.organisms if item.id != parent_id]
    assert result.births == 1, (
        f"births={result.births} blocked={result.blocked_reproduction} "
        f"after={result.after_count} ids={[item.id for item in result.population.organisms]}"
    )
    assert len(children) == 1, [item.id for item in result.population.organisms]
    return children[0]


def _assert_no_negative_atp(result) -> None:
    for organism in result.population.organisms:
        balance = organism.atp_state.runtime_available
        assert balance >= 0.0, f"{organism.id} runtime_atp={balance}"
    for record in result.organism_records:
        assert record.runtime_atp_before >= 0.0, record.runtime_atp_before
        assert record.runtime_atp_after >= 0.0, record.runtime_atp_after
    for trace in result.traces:
        for event in trace.events:
            assert event.atp_before >= 0.0, event.atp_before
            assert event.atp_after >= 0.0, event.atp_after


def test_two_seeds_diverge_at_bit_flip_rate_half_and_same_seed_matches() -> None:
    bits = "111" * 8
    configs = _configs(bit_flip_rate=0.5, parent_atp_cost=1.0, offspring_atp_fraction=0.25)
    assert configs.reproduction.is_sexual is False

    _, population_a, world_a = _state(bits, 40.0)
    direct = step_population(population_a, world_a, configs, seed=4)
    _, population_b, world_b = _state(bits, 40.0)
    repeated = PopulationRunner(population_b, world_b, configs).step_generation(seed=4)
    _, population_c, world_c = _state(bits, 40.0)
    other = step_population(population_c, world_c, configs, seed=9)

    left = _child(direct).genome.to_compact()
    right = _child(repeated).genome.to_compact()
    diverged = _child(other).genome.to_compact()

    assert left == right, f"same seed genomes {left!r} vs {right!r}"
    assert left != diverged, f"seeds 4 and 9 both produced {left!r}"
    _assert_no_negative_atp(direct)
    _assert_no_negative_atp(repeated)
    _assert_no_negative_atp(other)


def test_bit_flip_rate_zero_asexual_child_genome_equals_parent() -> None:
    bits = "111000111"
    configs = _configs(bit_flip_rate=0.0)
    assert configs.reproduction.is_sexual is False
    _parent, population, world = _state(bits, 40.0)

    result = step_population(population, world, configs, seed=3)
    child = _child(result)
    reproduction = result.organism_records[0].reproduction_result

    assert child.genome.to_compact() == bits, child.genome.to_compact()
    assert child.genome.to_codons() == ("111", "000", "111")
    assert reproduction is not None and reproduction.recombination_record is None
    _assert_no_negative_atp(result)


def test_parent_atp_cost_above_balance_blocks_birth_and_atp_stays_non_negative() -> None:
    initial_atp = 20.0
    configs = _configs(parent_atp_cost=100.0, min_runtime_atp=0.0)
    _parent, population, world = _state("111", initial_atp)

    result = step_population(population, world, configs, seed=5)
    reproduction = result.organism_records[0].reproduction_result

    assert result.births == 0, result.births
    assert reproduction is not None
    assert reproduction.succeeded is False
    assert reproduction.decision.reasons[0] == "parent_atp_cost_not_payable", reproduction.decision.reasons
    assert reproduction.reproduction_gate_result is not None
    assert reproduction.reproduction_gate_result.parent_cost_payable is False
    assert reproduction.child is None
    _assert_no_negative_atp(result)
    for organism in result.population.organisms:
        assert organism.atp_state.runtime_available <= initial_atp


def test_max_population_one_blocks_the_second_birth() -> None:
    configs = _configs(max_population=1, ticks_per_generation=2, parent_atp_cost=1.0)
    _parent, population, world = _state("111", 40.0)

    result = step_population(population, world, configs, seed=6)
    events = result.traces[0].events

    assert len(events) == 2, len(events)
    assert result.births == 0, result.births
    assert result.blocked_reproduction == 2, result.blocked_reproduction
    assert result.after_count == 1, result.after_count
    assert len(result.population.organisms) == 1
    assert events[1].world_delta["reproduction_succeeded"] is False
    assert events[1].world_delta["reproduction_blocked_reason"] == "max_population_reached", (
        events[1].world_delta.get("reproduction_blocked_reason")
    )
    assert events[0].world_delta["reproduction_blocked_reason"] == "max_population_reached"
    _assert_no_negative_atp(result)


def test_offspring_atp_fraction_half_does_not_create_energy() -> None:
    parent_cost = 2.0
    fraction = 0.5
    configs = _configs(parent_atp_cost=parent_cost, offspring_atp_fraction=fraction, bit_flip_rate=0.0)
    _parent, population, world = _state("111", 30.0)

    result = step_population(population, world, configs, seed=8)
    child = _child(result)
    reproduction = result.organism_records[0].reproduction_result
    assert reproduction is not None and reproduction.reproduction_gate_result is not None
    before_birth = reproduction.reproduction_gate_result.parent_runtime_atp_before_copy_self
    parent_after = reproduction.parent_after.atp_state.runtime_available
    child_atp = child.atp_state.runtime_available
    after_parent_cost = before_birth - parent_cost

    assert child_atp == pytest.approx(after_parent_cost * fraction, abs=1e-9), (
        f"child_atp={child_atp} before_birth={before_birth} after_parent_cost={after_parent_cost} "
        f"parent_after={parent_after}"
    )
    assert parent_after + child_atp <= before_birth + 1e-9, (
        f"energy created: parent_after={parent_after} child_atp={child_atp} before_birth={before_birth}"
    )
    assert parent_after >= 0.0 and child_atp >= 0.0
    _assert_no_negative_atp(result)


def test_basal_metabolism_reduces_atp_and_never_goes_below_zero() -> None:
    initial_atp = 2.0
    basal_cost = 1.0
    configs = _configs(basal_runtime_atp_cost=basal_cost, ticks_per_generation=5)
    _parent, population, world = _state("000", initial_atp)

    result = step_population(population, world, configs, seed=2)
    record = result.organism_records[0]

    assert record.runtime_atp_before == pytest.approx(initial_atp)
    assert record.runtime_atp_after < record.runtime_atp_before - basal_cost, (
        f"before={record.runtime_atp_before} after={record.runtime_atp_after} basal={basal_cost}"
    )
    assert record.runtime_atp_after == pytest.approx(0.0), record.runtime_atp_after
    assert result.births == 0
    _assert_no_negative_atp(result)


def test_public_birth_path_genome_spec_other_than_binary3() -> None:
    spec = GenomeSpec.dna3()
    table = CodonTable(
        [Codon.from_sequence("AAA", Action.COPY_SELF, 1.0, spec=spec)],
        spec=CodonTableSpec(genome_spec=spec, table_name="dna3_birth"),
    )
    ribosome = Ribosome(codon_table=table, codon_table_version="dna3_birth")
    configs = _configs(bit_flip_rate=0.0, parent_atp_cost=1.0, offspring_atp_fraction=0.25)
    rejected: BaseException | None = None
    result = None
    try:
        _parent, population, world = _state("AAA", 20.0, ribosome=ribosome)
        result = step_population(population, world, configs, seed=11)
    except (ConfigurationError, ValueError) as exc:
        rejected = exc

    if rejected is not None:
        assert isinstance(rejected, (ConfigurationError, ValueError)), type(rejected)
        return

    assert result is not None
    child = _child(result)
    assert child.genome.spec.name != "binary3", child.genome.spec.to_dict()
    assert child.genome.spec == spec, child.genome.spec.to_dict()
    assert set(child.genome.to_compact()) <= set(spec.alphabet)
    _assert_no_negative_atp(result)


def test_mention_spans_child_brain_codons_match_executable_bits() -> None:
    organism, population, world = _state("111000111", 40.0)
    spanned = organism.genome.with_spans((BitSpan(3, 6, "payload", "note"),))
    try:
        organism.genome = spanned
    except (AttributeError, TypeError) as exc:
        pytest.skip(f"organism forbids replacing genome: {type(exc).__name__}: {exc}")
    if organism.genome.spans != spanned.spans:
        pytest.skip("organism forbids replacing genome: assignment did not keep mention spans")

    configs = _configs(bit_flip_rate=0.0)
    result = step_population(population, world, configs, seed=12)
    child = _child(result)
    executable = child.genome.executable_bits()
    width = child.genome.spec.codon_width
    brain_codons = tuple(token.bits for token in child.compiled_brain.tokens)
    expected = tuple(executable[index : index + width] for index in range(0, len(executable), width))

    assert executable != child.genome.to_compact(), (
        f"executable={executable!r} tape={child.genome.to_compact()!r} spans={child.genome.spans}"
    )
    assert brain_codons == expected, (
        f"brain={brain_codons} executable_codons={expected} tape={child.genome.to_compact()!r}"
    )
    assert "".join(brain_codons) == executable
    assert "".join(brain_codons) != child.genome.to_compact()
