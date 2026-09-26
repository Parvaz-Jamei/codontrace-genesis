"""Selfing-hold prereg: mid+terminal gate, transmission contract, ClaimGate."""

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
from codontrace.genesis.closed_loop_hp_arm01_selfing_hold import (
    HOLD_EPSILON,
    HOLD_GENERATIONS,
    HOLD_INVASION_PASS_BAR,
    HOLD_MID_WINDOWS,
    HOLD_MIN_VIABLE_CENSUS,
    HOLD_SEEDS,
    HOLD_TWO_FOLD_COST_SEX,
    OUTCOME_INVASION_FAIL,
    OUTCOME_INVASION_PASS,
    OUTCOME_PERSISTENCE_FAIL,
    OUTCOME_SELFING_NONVIABLE,
    PREREG_RELATIVE_PATH,
    SEALED_MATING_SEEDS,
    SEALED_P7_SEEDS,
    SEALED_PERSISTENCE_SEEDS,
    SEALED_SLOWINSKI_SEEDS,
    assert_hold_locked_horizon,
    assert_hold_seed_policy,
    avirulent_selfing_hold_series,
    classify_typed_outcome,
    locked_design_dict,
    prereg_document_path,
    selfing_hold_design_digest,
    selfing_hold_document_digest,
)
from codontrace.genesis.closed_loop_hp_arm01_mating import assay_validity_gate


def test_prereg_file_exists_and_digests_stable() -> None:
    path = prereg_document_path()
    assert path.is_file()
    assert PREREG_RELATIVE_PATH in str(path).replace("\\", "/")
    text = path.read_text(encoding="utf-8")
    assert "LOCKED before outcomes" in text
    assert "HP-ARM01-SELFING-TRANSMISSION-CONTRACT" in text
    assert "HP-ARM01-MATE-LIMITATION-PROCESS" in text
    assert "HP-ARM01-AVI-HOLD-GATE" in text
    assert "HP-ARM01-BASELINE-HOLD-GATE" in text
    assert "selfing_nonviable" in text
    assert "doi:10.1186/s12915-014-0093-1" in text
    assert "doi:10.1098/rspb.2002.1997" in text
    assert "doi:10.1111/jeb.13718" in text
    assert "7171d19" in text
    assert "91ab0c6" in text
    assert "214df20" in text
    d1 = selfing_hold_design_digest()
    d2 = selfing_hold_document_digest()
    assert d1.startswith("hp_arm01_selfing_hold_design:")
    assert len(d2) == 64
    assert d1 == selfing_hold_design_digest()
    design = locked_design_dict()
    assert design["estimand"] == HP_ARM01_ESTIMAND
    assert design["substrate"] == SUBSTRATE_LIFE_LOOP
    assert design["generations"] == HOLD_GENERATIONS
    assert design["mid_hold_windows"] == list(HOLD_MID_WINDOWS)
    assert design["avirulent_selfing_hold_epsilon"] == HOLD_EPSILON
    assert design["min_viable_census"] == HOLD_MIN_VIABLE_CENSUS
    assert design["passage_refill_mode"] == PASSAGE_REFILL_GENERATION_BOUNDARY
    assert design["two_fold_cost_sex"] is HOLD_TWO_FOLD_COST_SEX
    assert design["seeds"] == list(HOLD_SEEDS)
    assert design["spc_owns_accept_path"] is False
    assert design["spc_owns_baseline"] is False
    assert design["early_bump_is_baseline"] is False
    assert "selfing_nonviable" in design["typed_outcomes"]


def test_seed_policy_refuses_sealed_ranges_and_short_horizon() -> None:
    assert_hold_seed_policy()
    with pytest.raises(ConfigurationError, match="101"):
        assert_hold_seed_policy([101, 501])
    with pytest.raises(ConfigurationError, match="201"):
        assert_hold_seed_policy([201, 501])
    with pytest.raises(ConfigurationError, match="301"):
        assert_hold_seed_policy([301, 501])
    with pytest.raises(ConfigurationError, match="401"):
        assert_hold_seed_policy([401, 501])
    with pytest.raises(ConfigurationError, match="unique"):
        assert_hold_seed_policy([501, 501])
    with pytest.raises(ConfigurationError, match="locked"):
        assert_hold_locked_horizon(generations=24)
    assert_hold_locked_horizon(generations=HOLD_GENERATIONS)


def test_hold_gate_and_typed_taxonomy() -> None:
    # Persistent hold above epsilon
    out = [20] * 48
    selfing = [10] * 48
    info = avirulent_selfing_hold_series(
        outcross_by_generation=out, selfing_by_generation=selfing
    )
    assert info["hold_passes"] is True
    # Bump then purge fails
    selfing_bump = [8] * 10 + [0] * 38
    out_bump = [24] * 10 + [32] * 38
    info2 = avirulent_selfing_hold_series(
        outcross_by_generation=out_bump, selfing_by_generation=selfing_bump
    )
    assert info2["hold_passes"] is False
    assert assay_validity_gate(
        terminal_census_by_arm={"avirulent": 8, "fixed": 8, "copassaged": 8},
        min_viable_census=8,
    )
    assert (
        classify_typed_outcome(
            assay_valid=False,
            avirulent_selfing_hold=True,
            slowinski_invasion_holds=True,
        )
        == OUTCOME_PERSISTENCE_FAIL
    )
    assert (
        classify_typed_outcome(
            assay_valid=True,
            avirulent_selfing_hold=False,
            slowinski_invasion_holds=True,
        )
        == OUTCOME_SELFING_NONVIABLE
    )
    assert (
        classify_typed_outcome(
            assay_valid=True,
            avirulent_selfing_hold=True,
            slowinski_invasion_holds=False,
        )
        == OUTCOME_INVASION_FAIL
    )
    assert (
        classify_typed_outcome(
            assay_valid=True,
            avirulent_selfing_hold=True,
            slowinski_invasion_holds=True,
        )
        == OUTCOME_INVASION_PASS
    )


def test_claimgate_refuses_red_queen_and_ceiling_observation() -> None:
    with pytest.raises(Exception):
        assert_claim_allowed({"red_queen_proved": True})
    assert HOLD_INVASION_PASS_BAR == 6
    assert CLAIM_CEILING_OBSERVATION == "runtime_observation"
    assert set(SEALED_P7_SEEDS) | set(SEALED_SLOWINSKI_SEEDS) | set(
        SEALED_PERSISTENCE_SEEDS
    ) | set(SEALED_MATING_SEEDS)
