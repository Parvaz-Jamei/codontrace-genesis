"""Persistence ledger + passage refill prereg: assay gate, typed outcomes, ClaimGate."""

from __future__ import annotations

from pathlib import Path

import pytest

from codontrace.claimgate.adapters.host_parasite import assert_claim_allowed
from codontrace.errors import ConfigurationError
from codontrace.genesis.closed_loop_hp_arm01 import (
    CLAIM_CEILING_OBSERVATION,
    HP_ARM01_ESTIMAND,
    PASSAGE_REFILL_GENERATION_BOUNDARY,
    SUBSTRATE_LIFE_LOOP,
)
from codontrace.genesis.closed_loop_hp_arm01_persistence import (
    OUTCOME_INVASION_FAIL,
    OUTCOME_INVASION_PASS,
    OUTCOME_PERSISTENCE_FAIL,
    PERSIST_GENERATIONS,
    PERSIST_INVASION_PASS_BAR,
    PERSIST_RESOURCE_BOLUS_AMOUNT,
    PERSIST_SEEDS,
    PERSIST_SOFT_K,
    PERSIST_VIRULENCE,
    PREREG_RELATIVE_PATH,
    SEALED_P7_SEEDS,
    SEALED_SLOWINSKI_SEEDS,
    assay_validity_gate,
    assert_persist_locked_horizon,
    assert_persist_seed_policy,
    classify_typed_outcome,
    locked_design_dict,
    persistence_ledger_design_digest,
    persistence_ledger_document_digest,
    prereg_document_path,
    run_persistence_confirm_campaign,
)


def test_prereg_file_exists_and_digests_stable() -> None:
    path = prereg_document_path()
    assert path.is_file()
    assert PREREG_RELATIVE_PATH in str(path).replace("\\", "/")
    text = path.read_text(encoding="utf-8")
    assert "LOCKED before outcomes" in text
    assert "HP-ARM01-PERSISTENCE-LEDGER" in text
    assert "HP-ARM01-PASSAGE-REFILL" in text
    assert "ASSAY-VALIDITY-GATE" in text
    assert "persistence_fail" in text
    assert "doi:10.1038/nrg1088" in text
    assert "214df20" in text
    d1 = persistence_ledger_design_digest()
    d2 = persistence_ledger_document_digest()
    assert d1.startswith("hp_arm01_persistence_design:")
    assert len(d2) == 64
    assert d1 == persistence_ledger_design_digest()
    design = locked_design_dict()
    assert design["estimand"] == HP_ARM01_ESTIMAND
    assert design["substrate"] == SUBSTRATE_LIFE_LOOP
    assert design["generations"] == PERSIST_GENERATIONS
    assert design["virulence"] == PERSIST_VIRULENCE
    assert design["resource_bolus_amount"] == PERSIST_RESOURCE_BOLUS_AMOUNT
    assert design["soft_carrying_capacity"] == PERSIST_SOFT_K
    assert design["passage_refill_mode"] == PASSAGE_REFILL_GENERATION_BOUNDARY
    assert design["passage_refill_sync"] == "generation_boundary"
    assert design["seeds"] == list(PERSIST_SEEDS)
    assert design["spc_owns_accept_path"] is False
    assert design["last_live_is_slowinski_pass"] is False


def test_seed_policy_refuses_sealed_ranges_and_short_horizon() -> None:
    assert_persist_seed_policy()
    with pytest.raises(ConfigurationError, match="101"):
        assert_persist_seed_policy([101, 301])
    with pytest.raises(ConfigurationError, match="201"):
        assert_persist_seed_policy([201, 301])
    with pytest.raises(ConfigurationError, match="unique"):
        assert_persist_seed_policy([301, 301])
    assert_persist_locked_horizon(generations=PERSIST_GENERATIONS)
    with pytest.raises(ConfigurationError, match="locked at 48"):
        assert_persist_locked_horizon(generations=4)
    assert set(PERSIST_SEEDS).isdisjoint(set(SEALED_P7_SEEDS))
    assert set(PERSIST_SEEDS).isdisjoint(set(SEALED_SLOWINSKI_SEEDS))


def test_assay_validity_gate_and_typed_outcomes() -> None:
    assert assay_validity_gate(
        terminal_census_by_arm={"avirulent": 1, "fixed": 2, "copassaged": 3}
    )
    assert not assay_validity_gate(
        terminal_census_by_arm={"avirulent": 0, "fixed": 2, "copassaged": 3}
    )
    assert not assay_validity_gate(
        terminal_census_by_arm={"avirulent": 1, "fixed": 1}
    )
    assert (
        classify_typed_outcome(assay_valid=False, slowinski_invasion_holds=True)
        == OUTCOME_PERSISTENCE_FAIL
    )
    assert (
        classify_typed_outcome(assay_valid=True, slowinski_invasion_holds=False)
        == OUTCOME_INVASION_FAIL
    )
    assert (
        classify_typed_outcome(assay_valid=True, slowinski_invasion_holds=True)
        == OUTCOME_INVASION_PASS
    )


def test_claimgate_still_refuses_and_engine_clean() -> None:
    with pytest.raises(ConfigurationError, match="blocked"):
        assert_claim_allowed("red_queen_proved")
    repo = Path(__file__).resolve().parents[2]
    engine = (repo / "src" / "codontrace" / "engine.py").read_text(encoding="utf-8").lower()
    for token in ("outcross", "infection", "parasite", "red_queen", "matching_allele"):
        assert token not in engine


def test_persist_runner_refuses_retuned_params() -> None:
    with pytest.raises(ConfigurationError, match="virulence is locked"):
        run_persistence_confirm_campaign(virulence=8.0)
    with pytest.raises(ConfigurationError, match="parasite_mutation is locked"):
        run_persistence_confirm_campaign(parasite_mutation=0.7)
    with pytest.raises(ConfigurationError, match="locked at 48"):
        run_persistence_confirm_campaign(generations=4)


@pytest.mark.slow
def test_persist_campaign_smoke_one_seed_locked_horizon() -> None:
    report = run_persistence_confirm_campaign(seeds=(301,))
    assert report.generations == PERSIST_GENERATIONS
    assert report.virulence == PERSIST_VIRULENCE
    assert report.resource_bolus_amount == PERSIST_RESOURCE_BOLUS_AMOUNT
    assert report.soft_carrying_capacity == PERSIST_SOFT_K
    assert report.passage_refill_sync == "generation_boundary"
    assert report.two_fold_cost_sex_applied is False
    assert report.red_queen_proved is False
    assert report.biological_red_queen_proved is False
    assert report.claim_ceiling == CLAIM_CEILING_OBSERVATION or report.invasion_campaign_pass
    assert len(report.seed_results) == 1
    row = report.seed_results[0]
    assert row.typed_outcome in {
        OUTCOME_PERSISTENCE_FAIL,
        OUTCOME_INVASION_FAIL,
        OUTCOME_INVASION_PASS,
    }
    assert row.life_loop_bound is True
    assert row.passage_refill_mode == PASSAGE_REFILL_GENERATION_BOUNDARY
    # If assay invalid, invasion must be unscored (None), not a soft PASS.
    if not row.assay_valid:
        assert row.typed_outcome == OUTCOME_PERSISTENCE_FAIL
        assert row.slowinski_invasion_holds is None
        assert report.claim_ceiling == CLAIM_CEILING_OBSERVATION
    else:
        assert row.typed_outcome in {OUTCOME_INVASION_FAIL, OUTCOME_INVASION_PASS}
        assert row.slowinski_invasion_holds is not None
        assert all(v >= 1 for v in row.terminal_census_by_arm.values())
