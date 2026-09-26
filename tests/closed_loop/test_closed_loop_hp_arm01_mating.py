"""Mating ledger prereg: raised census floor, selfing_nonviable taxonomy, ClaimGate."""

from __future__ import annotations

import pytest

from codontrace.claimgate.adapters.host_parasite import assert_claim_allowed
from codontrace.errors import ConfigurationError
from codontrace.genesis.closed_loop_hp_arm01 import (
    CLAIM_CEILING_OBSERVATION,
    HP_ARM01_ESTIMAND,
    PASSAGE_REFILL_GENERATION_BOUNDARY,
    SUBSTRATE_LIFE_LOOP,
)
from codontrace.genesis.closed_loop_hp_arm01_mating import (
    MATING_GENERATIONS,
    MATING_INVASION_PASS_BAR,
    MATING_MIN_VIABLE_CENSUS,
    MATING_RESOURCE_BOLUS_AMOUNT,
    MATING_SEEDS,
    MATING_SOFT_K,
    MATING_STEAL_FRACTION,
    MATING_VIRULENCE,
    OUTCOME_INVASION_FAIL,
    OUTCOME_INVASION_PASS,
    OUTCOME_PERSISTENCE_FAIL,
    OUTCOME_SELFING_NONVIABLE,
    PREREG_RELATIVE_PATH,
    SEALED_P7_SEEDS,
    SEALED_PERSISTENCE_SEEDS,
    SEALED_SLOWINSKI_SEEDS,
    assay_validity_gate,
    assert_mating_locked_horizon,
    assert_mating_seed_policy,
    avirulent_selfing_baseline_holds,
    classify_typed_outcome,
    locked_design_dict,
    mating_ledger_design_digest,
    mating_ledger_document_digest,
    prereg_document_path,
)


def test_prereg_file_exists_and_digests_stable() -> None:
    path = prereg_document_path()
    assert path.is_file()
    assert PREREG_RELATIVE_PATH in str(path).replace("\\", "/")
    text = path.read_text(encoding="utf-8")
    assert "LOCKED before outcomes" in text
    assert "HP-ARM01-MATING-LEDGER" in text
    assert "HP-ARM01-SELFING-BASELINE" in text
    assert "HP-ARM01-CLAIMGATE-SELFING-TAXONOMY" in text
    assert "HP-ARM01-DEBIT-GAIN-ASSURANCE" in text
    assert "selfing_nonviable" in text
    assert "doi:10.1186/s12915-014-0093-1" in text
    assert "doi:10.1098/rspb.2021.2269" in text
    assert "91ab0c6" in text
    assert "214df20" in text
    d1 = mating_ledger_design_digest()
    d2 = mating_ledger_document_digest()
    assert d1.startswith("hp_arm01_mating_design:")
    assert len(d2) == 64
    assert d1 == mating_ledger_design_digest()
    design = locked_design_dict()
    assert design["estimand"] == HP_ARM01_ESTIMAND
    assert design["substrate"] == SUBSTRATE_LIFE_LOOP
    assert design["generations"] == MATING_GENERATIONS
    assert design["virulence"] == MATING_VIRULENCE
    assert design["resource_bolus_amount"] == MATING_RESOURCE_BOLUS_AMOUNT
    assert design["soft_carrying_capacity"] == MATING_SOFT_K
    assert design["steal_fraction"] == MATING_STEAL_FRACTION
    assert design["min_viable_census"] == MATING_MIN_VIABLE_CENSUS
    assert design["min_viable_census"] >= 5
    assert design["passage_refill_mode"] == PASSAGE_REFILL_GENERATION_BOUNDARY
    assert design["founder_spatial_policy"] == "food_patch_interleaved"
    assert design["seeds"] == list(MATING_SEEDS)
    assert design["spc_owns_accept_path"] is False
    assert design["last_live_is_slowinski_pass"] is False
    assert "selfing_nonviable" in design["typed_outcomes"]


def test_seed_policy_refuses_sealed_ranges_and_short_horizon() -> None:
    assert_mating_seed_policy()
    with pytest.raises(ConfigurationError, match="101"):
        assert_mating_seed_policy([101, 401])
    with pytest.raises(ConfigurationError, match="201"):
        assert_mating_seed_policy([201, 401])
    with pytest.raises(ConfigurationError, match="301"):
        assert_mating_seed_policy([301, 401])
    with pytest.raises(ConfigurationError, match="unique"):
        assert_mating_seed_policy([401, 401])
    with pytest.raises(ConfigurationError, match="locked"):
        assert_mating_locked_horizon(generations=24)
    assert_mating_locked_horizon(generations=MATING_GENERATIONS)


def test_assay_gate_refuses_n1_and_typed_taxonomy() -> None:
    with pytest.raises(ConfigurationError, match="N=1"):
        assay_validity_gate(
            terminal_census_by_arm={"avirulent": 8, "fixed": 8, "copassaged": 8},
            min_viable_census=1,
        )
    assert assay_validity_gate(
        terminal_census_by_arm={"avirulent": 8, "fixed": 8, "copassaged": 8},
        min_viable_census=8,
    )
    assert not assay_validity_gate(
        terminal_census_by_arm={"avirulent": 32, "fixed": 1, "copassaged": 22},
        min_viable_census=8,
    )
    assert avirulent_selfing_baseline_holds(selfing_freq_avirulent=0.1)
    assert not avirulent_selfing_baseline_holds(selfing_freq_avirulent=0.0)
    assert not avirulent_selfing_baseline_holds(selfing_freq_avirulent=None)
    assert (
        classify_typed_outcome(
            assay_valid=False,
            avirulent_selfing_baseline=True,
            slowinski_invasion_holds=True,
        )
        == OUTCOME_PERSISTENCE_FAIL
    )
    assert (
        classify_typed_outcome(
            assay_valid=True,
            avirulent_selfing_baseline=False,
            slowinski_invasion_holds=True,
        )
        == OUTCOME_SELFING_NONVIABLE
    )
    assert (
        classify_typed_outcome(
            assay_valid=True,
            avirulent_selfing_baseline=True,
            slowinski_invasion_holds=False,
        )
        == OUTCOME_INVASION_FAIL
    )
    assert (
        classify_typed_outcome(
            assay_valid=True,
            avirulent_selfing_baseline=True,
            slowinski_invasion_holds=True,
        )
        == OUTCOME_INVASION_PASS
    )


def test_claimgate_refuses_red_queen_and_ceiling_observation() -> None:
    with pytest.raises(Exception):
        assert_claim_allowed({"red_queen_proved": True})
    assert MATING_INVASION_PASS_BAR == 6
    assert CLAIM_CEILING_OBSERVATION == "runtime_observation"
    assert set(SEALED_P7_SEEDS) | set(SEALED_SLOWINSKI_SEEDS) | set(
        SEALED_PERSISTENCE_SEEDS
    )
