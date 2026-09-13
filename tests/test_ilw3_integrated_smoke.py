"""ILW-3: integrated smoke with replay, conservation, edge coverage; no claim."""

from __future__ import annotations

import pytest

from codontrace.genesis.ilw import (
    CLAIM_CEILING,
    SCIENTIFIC_NAME,
    IlwChainRuntime,
    IlwSmokeError,
    WorldSpec,
    check_conservation,
    load_integration_dag,
    run_integrated_smoke,
)


def test_replay_rebuilds_final_digest_bitwise():
    report = run_integrated_smoke(run_id="ilw3-replay", seed=1, population=4)
    assert report.replay_matched is True
    assert report.primary_final_digest == report.replay_final_digest
    assert report.primary_final_digest.startswith("ilw_final:")
    # Independent construction also matches.
    rt_a = IlwChainRuntime.s1(run_id="ilw3-replay-pair", seed=1)
    rt_a.bootstrap(4)
    rt_a.run()
    rt_b = IlwChainRuntime.s1(run_id="ilw3-replay-pair", seed=1)
    rt_b.bootstrap(4)
    rt_b.run()
    assert rt_a.final_digest() == rt_b.final_digest()
    assert rt_a.ledger.digest() == rt_b.ledger.digest()
    assert rt_a.world.digest() == rt_b.world.digest()


def test_conservation_invariants_hold():
    report = run_integrated_smoke(run_id="ilw3-cons", seed=1, population=4)
    assert report.conservation.passed is True
    assert report.conservation.resource_ok is True
    assert report.conservation.energy_nonnegative_ok is True
    assert report.conservation.harvest_conversion_ok is True
    # Direct assay on a fresh runtime.
    rt = IlwChainRuntime.s1(run_id="ilw3-cons-direct", seed=1)
    rt.bootstrap(4)
    rt.run()
    cons = check_conservation(rt, raise_on_fail=True)
    assert cons.passed
    for kind in rt.world_spec.resource_kinds:
        pred = (
            cons.initial_totals[kind]
            - cons.harvested.get(kind, 0.0)
            + cons.renewed.get(kind, 0.0)
        )
        assert abs(pred - cons.final_totals[kind]) <= cons.atol


def test_required_edge_coverage_is_100_percent():
    dag = load_integration_dag()
    report = run_integrated_smoke(run_id="ilw3-edges", seed=1, population=4)
    assert report.required_edge_coverage == 1.0
    assert report.missing_edge_ids == ()
    assert set(report.observed_edge_ids) >= dag.required_edge_ids


def test_attempt_accepted_applied_are_separate_fields():
    report = run_integrated_smoke(run_id="ilw3-counters", seed=1, population=4)
    assert report.attempt_fields_separate is True
    # Reconstruct from primary summary path via a runtime.
    rt = IlwChainRuntime.s1(run_id="ilw3-counters-rt", seed=1)
    rt.bootstrap(4)
    rt.run()
    seen_divergence = False
    for event in rt.ledger.events:
        payload = event.payload
        assert "attempted" in payload
        assert "accepted" in payload
        assert "applied" in payload
        assert "attempt_accepted_applied" not in payload
        a, b, c = int(payload["attempted"]), int(payload["accepted"]), int(payload["applied"])
        if not (a == b == c):
            seen_divergence = True
    # At least some events must show the counters are not a single collapsed value.
    assert seen_divergence is True


def test_smoke_reports_no_claim_promotion():
    report = run_integrated_smoke(run_id="ilw3-noclaim", seed=1, population=4)
    blob = report.to_dict()
    assert blob["claim_ceiling"] == CLAIM_CEILING == "runtime_observation"
    assert blob["scientific_name"] == SCIENTIFIC_NAME
    assert blob["claim_promotions"] == []
    assert blob["ladder_promotion"] is None
    assert blob["scientific_claim_emitted"] is False
    assert report.primary_summary["claim_promotions"] == []
    assert report.primary_summary["ladder_promotion"] is None
    assert report.primary_summary["scientific_claim_emitted"] is False
    # Must not look like a ClaimGate ladder promotion payload.
    for banned in (
        "ladder_promoted_to",
        "claim_ladder_promotion",
        "promoted_claim_level",
        "claimgate_promotion",
        "strong_claim_ladder_result",
        "tokyo_type1_passed",
        "collective_intelligence_candidate",
    ):
        assert banned not in blob
        assert banned not in report.primary_summary


def test_s1_scale_larger_than_s0_with_birth_death_cycle():
    s0 = WorldSpec.s0_unit(seed=1)
    s1 = WorldSpec.s1_smoke(seed=1)
    assert s1.width * s1.height > s0.width * s0.height
    assert s1.tick_horizon > s0.tick_horizon
    assert s1.scale_label == "S1"
    report = run_integrated_smoke(run_id="ilw3-scale", seed=1, population=4)
    assert report.width == 16 and report.height == 16
    assert report.tick_horizon >= 32
    assert report.birth_count >= 1
    assert report.death_count >= 1
    assert report.scale_label == "S1"


def test_s0_unit_rejected_as_integrated_smoke():
    with pytest.raises(IlwSmokeError, match="larger than S0"):
        run_integrated_smoke(
            run_id="ilw3-too-small",
            world_spec=WorldSpec.s0_unit(seed=1),
            require_birth_death=False,
        )
