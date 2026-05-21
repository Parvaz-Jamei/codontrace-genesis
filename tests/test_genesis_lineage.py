from __future__ import annotations

from codontrace.genesis import LineageRecord, PopulationState
from codontrace.genesis.organism import GenesisOrganism


def test_lineage_record_serializes_to_json_safe_dict() -> None:
    record = LineageRecord(
        organism_id="child",
        parent_id="parent",
        generation=1,
        genome_digest="abc",
        mutation_count=2,
        birth_tick=3,
        death_tick=None,
        reproduction_event_id="evt",
    )

    assert record.to_dict()["parent_id"] == "parent"
    assert record.to_dict()["death_tick"] is None


def test_population_state_digest_is_stable() -> None:
    organism = GenesisOrganism.from_bits("org", "000", initial_runtime_atp=1.0)
    population = PopulationState(0, 0, (organism,), (), ())

    assert population.digest() == population.digest()
