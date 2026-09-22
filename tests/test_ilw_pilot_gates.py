"""ILW pilot gate evaluation + unlock (fast unit tests; no full S2 suite)."""

from __future__ import annotations

import pytest

from codontrace.genesis.ilw.pilot import (
    PilotCampaignReport,
    PomPatternRecord,
    SeedPilotResult,
    evaluate_pilot_gates,
    evaluate_pom_patterns,
    unlocked_harness_or_raise,
)
from codontrace.genesis.ilw.prereg import (
    CONFIRMATORY_HELD_OUT_SEEDS,
    PILOT_SEEDS,
    POM_ACCEPTANCE_PATTERNS,
    PilotGateError,
    PilotGateStatus,
)
from codontrace.genesis.ilw.world_spec import WorldSpec


def _seed_result(**overrides):
    base = dict(
        seed=3100,
        run_id="t",
        replay_matched=True,
        conservation_passed=True,
        required_edge_coverage=1.0,
        missing_edge_ids=(),
        birth_count=10,
        death_count=10,
        generation_turnover=10,
        lineage_depth=2,
        regime_changes=0,
        unique_genome_count=5,
        niches_occupied=3,
        capsule_to_policy_applied=3,
        event_count=100,
        organism_count=12,
        alive_count=4,
        attempt_fields_separate=True,
        no_claim_promotion=True,
        claim_ceiling="runtime_observation",
        primary_final_digest="ilw_final:a",
        replay_final_digest="ilw_final:a",
        world_spec_digest="ilw_world_spec:a",
    )
    base.update(overrides)
    return SeedPilotResult(**base)


def test_world_spec_s2_pilot_matches_ladder():
    spec = WorldSpec.s2_pilot(seed=3100)
    assert spec.width == 32 and spec.height == 32
    assert spec.tick_horizon == 128
    assert spec.population_cap == 64
    assert spec.scale_label == "S2"
    assert WorldSpec.from_scale_ladder("S2", seed=3101).width == 32


def test_evaluate_gates_and_pom_recording():
    seeds = [_seed_result(seed=s) for s in PILOT_SEEDS]
    ko = {
        "path_broke_as_predicted": True,
        "intact_applied": 5,
        "knockout_applied": 0,
        "knockout_blocked": 5,
    }
    scale = {"effect_direction_retained": True, "s1_coverage": 1.0, "s2_coverage": 1.0}
    pom = evaluate_pom_patterns(seeds, knockout_probe=ko, scale_probe=scale)
    assert len(pom) == len(POM_ACCEPTANCE_PATTERNS) == 8
    assert {p.pattern_id for p in pom} == {p["id"] for p in POM_ACCEPTANCE_PATTERNS}
    gates = evaluate_pilot_gates(seeds, pom)
    assert gates.all_passed is True


def test_gate_fails_when_replay_breaks():
    seeds = [_seed_result(replay_matched=False)]
    pom = [PomPatternRecord(p["id"], "pass", "x") for p in POM_ACCEPTANCE_PATTERNS]
    gates = evaluate_pilot_gates(seeds, pom)
    assert gates.replay_ok is False
    assert gates.all_passed is False


def test_unlock_requires_all_gates():
    report = PilotCampaignReport(
        seed_results=[_seed_result()],
        pom_records=[PomPatternRecord(p["id"], "pass", "x") for p in POM_ACCEPTANCE_PATTERNS],
        gates=PilotGateStatus(),
        status="FAIL",
    )
    with pytest.raises(PilotGateError):
        unlocked_harness_or_raise(report)
    report.gates = PilotGateStatus(
        replay_ok=True,
        conservation_ok=True,
        edge_coverage_ok=True,
        pom_patterns_recorded=True,
        no_claim_promotion=True,
        claim_ceiling_ok=True,
    )
    harness = unlocked_harness_or_raise(report)
    harness.assert_seed_allowed(4100, role="confirmatory")
    assert 4100 in CONFIRMATORY_HELD_OUT_SEEDS
