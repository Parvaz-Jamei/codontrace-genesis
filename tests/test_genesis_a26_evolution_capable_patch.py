from __future__ import annotations

from codontrace.genesis import (
    EvolutionConfig,
    GenesisEngine,
    GenesisEngineConfig,
    GenesisExperimentSpec,
)
from codontrace.genesis.capsule import (
    CapsuleShuffleMode,
    CapsuleTransferConfig,
    CausalCapsule,
    apply_capsule_shuffle_control,
)


def test_capsule_shuffle_control_changes_payload_and_is_deterministic() -> None:
    first = CausalCapsule("c1", "s1", 1.0, "g1", ("A",), "B", 0.9, 0, 10)
    second = CausalCapsule("c2", "s2", 2.0, "g2", ("C",), "D", 0.9, 0, 10)
    shuffled_a, records_a = apply_capsule_shuffle_control(
        (first, second),
        CapsuleShuffleMode.CONTENT_SOURCE_TIMING,
        tick=5,
        target_organism_id="target",
    )
    shuffled_b, records_b = apply_capsule_shuffle_control(
        (first, second),
        CapsuleShuffleMode.CONTENT_SOURCE_TIMING,
        tick=5,
        target_organism_id="target",
    )

    assert [capsule.digest() for capsule in shuffled_a] == [
        capsule.digest() for capsule in shuffled_b
    ]
    assert [record.digest() for record in records_a] == [record.digest() for record in records_b]
    assert records_a
    assert all(record.claim_eligible for record in records_a)
    assert any(record.source_changed for record in records_a)
    assert any(record.content_changed for record in records_a)
    assert any(record.timing_changed for record in records_a)


def test_genesis_result_public_patch_records_are_deterministic() -> None:
    spec = GenesisExperimentSpec(
        genome_bits=("101110000", "110101000", "111000111"),
        seed=123,
        tick_count=3,
        population_max=3,
        engine_config=GenesisEngineConfig(
            ticks_per_generation=2, enable_capsules=True, enable_qd=True
        ),
        evolution_config=EvolutionConfig(selection_policy="novelty_weighted", max_population=3),
        capsule_transfer_config=CapsuleTransferConfig(
            enabled=True,
            min_confidence=0.0,
            adoption_min_confidence=0.0,
            min_source_fitness=0.0,
            max_adoptions_per_organism=2,
            max_capsules_read_per_tick=4,
            read_radius=99,
            adoption_cost_learning_atp=0.0,
            emission_cost_learning_atp=0.0,
            emission_cost_runtime_atp=0.0,
            read_cost_runtime_atp=0.0,
            min_atp_runtime_to_emit=0.0,
            shuffle_mode=CapsuleShuffleMode.CONTENT_SOURCE_TIMING,
        ),
    )

    first = GenesisEngine.from_spec(spec).run_ticks()
    second = GenesisEngine.from_spec(spec).run_ticks()

    assert first.digest() == second.digest()
    assert first.behavior_descriptors
    assert first.fitness_breakdown_records
    assert first.engine_frames
    assert first.capsule_shuffle_records
    assert first.evidence_manifest.digest() == second.evidence_manifest.digest()


def test_qd_novelty_weighted_selection_can_change_survivor_order() -> None:
    spec = GenesisExperimentSpec(
        genome_bits=("101110000", "110101000", "111000111", "000111000"),
        seed=7,
        tick_count=2,
        population_max=2,
        engine_config=GenesisEngineConfig(ticks_per_generation=2, enable_qd=True),
        evolution_config=EvolutionConfig(
            selection_policy="novelty_weighted",
            max_population=2,
            novelty_weight=10.0,
            fitness_weight=0.0,
        ),
    )

    result = GenesisEngine.from_spec(spec).run_ticks()

    assert result.qd_selection_audit
    assert any(record.selection_changed_by_qd for record in result.qd_selection_audit)
    assert all(record.novelty_scores_digest for record in result.qd_selection_audit)
