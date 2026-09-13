"""ILW-4: locked prereg digests, seed policy, pilot harness fail-first."""

from __future__ import annotations

import pytest

from codontrace.genesis.ilw import (
    CLAIM_CEILING,
    SCIENTIFIC_NAME,
)
from codontrace.genesis.ilw.prereg import (
    CONFIRMATORY_HELD_OUT_SEEDS,
    DOE_PLAN,
    EDGE_KNOCKOUTS,
    FORBIDDEN_CLAIM_LABELS,
    HORIZON_DEFINITIONS,
    INTERACTIONS_TO_ESTIMATE,
    MESOUDI_CCE_CRITERIA,
    PILOT_SEEDS,
    POM_ACCEPTANCE_PATTERNS,
    PREREG_VERSION,
    SCALE_LADDER,
    SMOKE_SEEDS,
    STOP_RULES,
    IlwPreregError,
    PilotGateError,
    PilotGateStatus,
    PilotHarness,
    assert_no_forbidden_claims,
    assert_prereg_claim_ceiling,
    assert_seed_policy_disjoint,
    ilw_prereg_design_digest,
    ilw_prereg_document_digest,
    locked_design_dict,
    summarize_prereg,
)

# Pinned after locking docs/ILW_PREREG_V1.md + prereg.py design dict (ILW-4).
PINNED_DESIGN_DIGEST = (
    "ilw_prereg_design:998654e9d27f5f314b7fa587785dac76fef4d7c1cdeb08cfcc74a83ba369c673"
)
PINNED_DOCUMENT_DIGEST = (
    "81dbfc057a7ff89e539940575bb51cbfb8db5f185fa282d9dd39963a3e9b125d"
)


def test_claim_ceiling_and_scientific_name_unchanged():
    assert_prereg_claim_ceiling()
    assert CLAIM_CEILING == "runtime_observation"
    assert SCIENTIFIC_NAME == "integrated eco-evolutionary runtime"
    design = locked_design_dict()
    assert design["claim_ceiling"] == CLAIM_CEILING
    assert design["scientific_name"] == SCIENTIFIC_NAME


def test_design_and_document_digests_pin():
    assert ilw_prereg_design_digest() == PINNED_DESIGN_DIGEST
    assert ilw_prereg_document_digest() == PINNED_DOCUMENT_DIGEST
    # Stability across calls.
    assert ilw_prereg_design_digest() == ilw_prereg_design_digest()
    assert ilw_prereg_document_digest() == ilw_prereg_document_digest()


def test_pilot_seeds_disjoint_from_confirmatory_analysis_seeds():
    assert_seed_policy_disjoint()
    pilot = set(PILOT_SEEDS)
    conf = set(CONFIRMATORY_HELD_OUT_SEEDS)
    assert pilot.isdisjoint(conf)
    assert set(SMOKE_SEEDS).issubset(pilot)
    assert pilot == set(range(3100, 3108))
    assert conf == set(range(4100, 4108))


def test_pom_interactions_scale_horizon_doe_locked():
    assert PREREG_VERSION == "ilw_prereg_v1"
    assert len(POM_ACCEPTANCE_PATTERNS) == 8
    assert {p["id"] for p in POM_ACCEPTANCE_PATTERNS} >= {
        "pom_1_toolchain_phenotype",
        "pom_6_capsule_causal",
        "pom_8_scale_direction",
    }
    assert INTERACTIONS_TO_ESTIMATE == (
        "toolchain × capsule",
        "capsule × ecology",
        "mutation × capsule",
        "heterogeneity × population_size",
    )
    assert set(SCALE_LADDER) == {"S0", "S1", "S2", "S3", "S4"}
    assert SCALE_LADDER["S2"]["width"] == 32
    assert SCALE_LADDER["S4"]["widths"] == (32, 64, 96)
    assert set(HORIZON_DEFINITIONS) == {
        "ticks",
        "generation_turnover",
        "lineage_depth",
        "regime_changes",
    }
    assert len(STOP_RULES) >= 8
    assert "stop_confirmatory_if_pilot_gates_fail" in STOP_RULES
    assert len(EDGE_KNOCKOUTS) == 7
    assert DOE_PLAN["phase_1_screening"]["cite_doi"] == "10.1016/j.envsoft.2010.04.012"
    assert DOE_PLAN["phase_2b_continuous"]["cite_doi"] == "10.1080/00224065.2011.11917841"
    assert DOE_PLAN["pom_cite_doi"] == "10.1098/rstb.2011.0180"
    assert DOE_PLAN["cce_cite_doi"] == "10.1098/rspb.2018.0712"
    assert len(MESOUDI_CCE_CRITERIA) == 4


def test_pilot_harness_refuses_confirmatory_until_gates_pass():
    harness = PilotHarness()
    # Pilot / smoke OK.
    out = harness.run_stub(3100, role="pilot", scale_label="S2")
    assert out["campaign_started"] is False
    assert out["ilw5_started"] is False
    assert out["claim_ceiling"] == "runtime_observation"
    harness.run_stub(3100, role="smoke")

    # Confirmatory refused fail-first.
    with pytest.raises(PilotGateError, match="pilot gates"):
        harness.run_stub(4100, role="confirmatory")

    # Held-out seed under pilot role refused.
    with pytest.raises(PilotGateError, match="held-out"):
        harness.run_stub(4100, role="pilot")

    # After gates pass, confirmatory held-out accepted; pilot seed still refused.
    passed = PilotGateStatus(
        replay_ok=True,
        conservation_ok=True,
        edge_coverage_ok=True,
        pom_patterns_recorded=True,
        no_claim_promotion=True,
        claim_ceiling_ok=True,
    )
    assert passed.all_passed is True
    ok = PilotHarness(gates=passed)
    conf = ok.run_stub(4100, role="confirmatory", scale_label="S3")
    assert conf["status"] == "stub_accepted"
    assert conf["campaign_started"] is False
    with pytest.raises(PilotGateError, match="pilot seed"):
        ok.run_stub(3100, role="confirmatory")


def test_forbidden_claims_rejected():
    assert_no_forbidden_claims([])
    with pytest.raises(IlwPreregError, match="Forbidden"):
        assert_no_forbidden_claims(["runtime_observation", "intelligence"])
    assert "collective_intelligence" in FORBIDDEN_CLAIM_LABELS
    assert "agi" in FORBIDDEN_CLAIM_LABELS


def test_summarize_prereg_no_outcomes():
    summary = summarize_prereg()
    assert summary["design_digest"] == PINNED_DESIGN_DIGEST
    assert summary["pom_pattern_count"] == 8
    assert "outcome" not in summary
    assert "campaign_result" not in summary
