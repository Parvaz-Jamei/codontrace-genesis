"""
Regression tests reproducing and verifying the Five-Phase Fix Suite:
1. Mutable state digest invalidation (Phase 2)
2. Organism ID collision avoidance in create_population_with_unique_ids (Phase 3A)
3. Discovery candidate genome decoding and assay evidence structure (Phase 3B)
4. Lifecycle stop/completion semantics (Phase 4)
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
import pytest

from codontrace.genesis.canonical import canonical_digest
from codontrace.genesis.phase_e import (
    PhaseEOrganismState,
    DemeState,
    SensoryCue,
    DifferentiationRole,
    CapsuleMemoryState,
)
from codontrace.genesis.population import (
    GenesisOrganism,
    PopulationState,
    create_population_with_unique_ids,
    LineageRecord,
    FitnessResult,
    BirthChamberState,
)
from codontrace.genesis.discovery_witness import (
    evaluate_discovery_candidate,
    DiscoveryClaimLevel,
    D0BaselineSet,
    D0BaselineRun,
    D0BaselineConfig,
    calibrate_d0_baseline,
)


def _dummy_organism(org_id: str) -> GenesisOrganism:
    return GenesisOrganism.from_bits(org_id, "111", initial_runtime_atp=10.0, position=(0, 0))


def _dummy_lineage(org_id: str) -> LineageRecord:
    return LineageRecord(
        organism_id=org_id,
        parent_id=None,
        generation=0,
        genome_digest="dummy",
        mutation_count=0,
        birth_tick=0,
        death_tick=None,
        reproduction_event_id=None,
    )


def _dummy_fitness(org_id: str) -> FitnessResult:
    return FitnessResult(
        organism_id=org_id,
        score=1.0,
        survived_ticks=1,
        lumen_eaten=0,
        nexus_emitted=0,
        blocked_actions=0,
        reproduction_events=0,
        reasons=(),
    )


def _dummy_birth_chamber() -> BirthChamberState:
    return BirthChamberState()


# ==============================================================================
# Phase 2 Repro & Validation: Mutable state digest invalidation
# ==============================================================================

def test_phase2_mutable_organism_state_digest_integrity():
    """Verify that modifying a mutable PhaseEOrganismState immediately changes its digest."""
    state = PhaseEOrganismState(
        organism_id="org_test_1",
        atp_bonus=0.5,
    )
    d1 = state.digest()
    assert d1 == canonical_digest(state.to_dict())

    # Mutate atp_bonus
    state.atp_bonus = 2.5
    d2 = state.digest()
    
    # Expected: digest MUST reflect the mutated state
    assert d2 == canonical_digest(state.to_dict()), "Digest must match canonical_digest of mutated state"
    assert d1 != d2, "Digest must change when atp_bonus is mutated"
    
    # Reconstructed from to_dict must have exact same digest
    reconstructed = PhaseEOrganismState.from_dict(state.to_dict())
    assert reconstructed.digest() == state.digest()


def test_phase2_mutable_sensory_and_deme_digest_integrity():
    """Verify that updating sensory cues or deme states reflects in digests."""
    state = PhaseEOrganismState(
        organism_id="org_test_2",
        sensory=SensoryCue(hazard_intensity=0.1),
    )
    d1 = state.digest()
    
    # Update sensory field
    state.sensory = SensoryCue(hazard_intensity=0.9)
    d2 = state.digest()
    
    assert d2 == canonical_digest(state.to_dict())
    assert d1 != d2


# ==============================================================================
# Phase 3A Repro & Validation: ID collisions in create_population_with_unique_ids
# ==============================================================================

def test_phase3_create_population_unique_id_collision_handling():
    """Verify that inputs like [a, a#1, a] do not cause duplicate IDs like a#1."""
    orgs = (
        _dummy_organism("org-a"),
        _dummy_organism("org-a#1"),
        _dummy_organism("org-a"),
    )
    lins = (
        _dummy_lineage("org-a"),
        _dummy_lineage("org-a#1"),
        _dummy_lineage("org-a"),
    )
    fits = (
        _dummy_fitness("org-a"),
        _dummy_fitness("org-a#1"),
        _dummy_fitness("org-a"),
    )
    chamber = _dummy_birth_chamber()

    # Must not raise ValueError: duplicated id org-a#1
    pop = create_population_with_unique_ids(
        generation=1,
        tick=10,
        organisms=orgs,
        lineage=lins,
        fitness=fits,
        birth_chamber=chamber,
    )

    ids = [o.id for o in pop.organisms]
    assert len(set(ids)) == len(ids), f"All IDs must be unique, got: {ids}"
    assert ids[0] == "org-a"
    assert ids[1] == "org-a#1"
    assert ids[2] == "org-a#2"

    lineage_ids = [l.organism_id for l in pop.lineage]
    assert lineage_ids == ids, "Lineage records must match organism IDs"


def test_phase3_multiple_cascading_collisions():
    """Verify inputs with multiple identical IDs resolve without collisions."""
    orgs = tuple(_dummy_organism("node") for _ in range(5))
    lins = tuple(_dummy_lineage("node") for _ in range(5))
    fits = tuple(_dummy_fitness("node") for _ in range(5))
    chamber = _dummy_birth_chamber()

    pop = create_population_with_unique_ids(
        generation=1,
        tick=10,
        organisms=orgs,
        lineage=lins,
        fitness=fits,
        birth_chamber=chamber,
    )

    ids = [o.id for o in pop.organisms]
    assert ids == ["node", "node#1", "node#2", "node#3", "node#4"]
    assert len(set(ids)) == 5


# ==============================================================================
# Phase 3B Repro & Validation: Discovery candidate genome & assay validation
# ==============================================================================

def test_phase3_discovery_candidate_genome_and_assay():
    """Verify that candidate_id is decoupled from genome and structured assay is verified."""
    def _make_run(seed: int, nov: float) -> D0BaselineRun:
        return D0BaselineRun(
            run_id=f"r{seed}",
            seed=seed,
            config_digest="cfg",
            behavior_descriptor={"novelty": nov, "complexity": nov / 2},
            behavior_digest=f"b{seed}",
            trace_digest=f"t{seed}",
            population_digest=f"p{seed}",
            graph_digest=f"g{seed}",
            vocabulary_digest=f"v{seed}",
            capsule_store_digest=f"c{seed}",
        )

    calibration = calibrate_d0_baseline(
        [_make_run(1, 1.0), _make_run(2, 1.2)],
        D0BaselineConfig(enabled=True, min_reference_runs=2, min_seeds=2),
    )
    assert calibration.baseline_set is not None
    baseline_set = calibration.baseline_set

    # 1. Arbitrary non-genome candidate_id with valid genome parameter and valid assay evidence
    cand = evaluate_discovery_candidate(
        candidate_id="cand_alpha_01",
        genome="000111",
        source_run_id="run_src",
        behavior_descriptor={"novelty": 5.0, "complexity": 5.0},
        behavior_digest="digest_b",
        baseline_set=baseline_set,
        novelty_threshold=0.1,
        persistence_ticks=5,
        mechanism_tags=("assay",),
        evidence_refs=("trace:1",),
        assay_evidence={
            "genome": "000111",
            "raw_data_hash": "a" * 64,
            "measurements": [5.0],
        },
    )
    assert cand.claim_level == DiscoveryClaimLevel.CANDIDATE
    assert cand.candidate_id == "cand_alpha_01"

    # 2. Invalid genome must be rejected
    cand_bad_genome = evaluate_discovery_candidate(
        candidate_id="cand_alpha_02",
        genome="not-a-valid-codon-string",
        source_run_id="run_src",
        behavior_descriptor={"novelty": 5.0, "complexity": 5.0},
        behavior_digest="digest_b",
        baseline_set=baseline_set,
        novelty_threshold=0.1,
        persistence_ticks=5,
        mechanism_tags=("assay",),
        evidence_refs=("trace:1",),
        assay_evidence={"genome": "not-a-valid-codon-string", "raw_data_hash": "h1"},
    )
    assert cand_bad_genome.claim_level == DiscoveryClaimLevel.NONE
    assert "invalid_genome" in cand_bad_genome.reasons

    # 3. Merely adding 'assay' in mechanism_tags without structured assay_evidence must be rejected
    cand_no_evidence = evaluate_discovery_candidate(
        candidate_id="cand_alpha_03",
        genome="000111",
        source_run_id="run_src",
        behavior_descriptor={"novelty": 5.0, "complexity": 5.0},
        behavior_digest="digest_b",
        baseline_set=baseline_set,
        novelty_threshold=0.1,
        persistence_ticks=5,
        mechanism_tags=("assay",),
        evidence_refs=("trace:1",),
        assay_evidence=None,
    )
    assert cand_no_evidence.claim_level == DiscoveryClaimLevel.NONE
    assert "missing_assay_evidence" in cand_no_evidence.reasons


# ==============================================================================
# Phase 4 Repro & Validation: Lifecycle stop and completion semantics
# ==============================================================================

def test_phase4_lifecycle_early_stop_not_completed(tmp_path: Path):
    """Verify that early stop produces STOPPED status, complete=False, and no COMPLETE marker."""
    from scripts.grand_frontier_suite_extension import run_worker_5_functional_info

    out_dir = tmp_path / "test_run_stop"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Place STOP file before or during run
    (out_dir / "STOP").write_text("user requested stop\n", encoding="utf-8")

    # Run with 10.0 hours target
    run_worker_5_functional_info(output_dir=out_dir, duration_hours=10.0, core_id=0)

    # Check status.json
    status_file = out_dir / "status.json"
    assert status_file.is_file()
    status_data = json.loads(status_file.read_text(encoding="utf-8"))
    
    assert status_data["status"] == "STOPPED", f"Expected STOPPED, got {status_data['status']}"
    assert status_data["pct"] < 100.0, f"Progress must not be 100% on stop: {status_data['pct']}"
    
    # Check execution.json
    exec_file = out_dir / "execution.json"
    assert exec_file.is_file()
    exec_data = json.loads(exec_file.read_text(encoding="utf-8"))
    assert exec_data["complete"] is False, "complete must be False when stopped early"
    assert "stop_reason" in exec_data
    
    # Check COMPLETE marker
    complete_marker = out_dir / "COMPLETE"
    assert not complete_marker.exists(), "COMPLETE marker must not exist for stopped run"
