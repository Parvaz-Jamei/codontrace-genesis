"""RQ-earn scaffold locks: proved flags stay false; helpers importable."""

from __future__ import annotations

import pytest

from codontrace.claimgate.adapters.host_parasite import assert_claim_allowed
from codontrace.errors import ConfigurationError
from codontrace.genesis.closed_loop_hp_arm01 import ARM_COPASSAGED, ARM_FIXED
from codontrace.genesis.closed_loop_hp_arm01_rq_earn import (
    ESTIMAND_FORK,
    FORK_B_SLOWINSKI_STATUS,
    PEARL_PASSAGE_MODES,
    RQ_EARN_DEBIT_ARMS,
    TWO_FOLD_COST_SEX_STATUS,
    build_rq_earn_report_stub,
    classify_rq_earn_smoke,
    pearl_contrast_stubs,
    rq_earn_design_dict,
    rq_earn_design_digest,
    score_lagged_nfds_on_debit_arms,
)
from codontrace.genesis.closed_loop_hp_arm01_structural_rq import (
    OUTCOME_REGIME_HOSTILE_NE,
)
from codontrace.genesis.closed_loop_pearl_spc import (
    PASSAGE_ABSENT,
    PASSAGE_COEVOLVE,
    PASSAGE_FROZEN,
)
from codontrace.genesis.measurements import (
    dominant_class_series,
    lagged_nfds_score,
    phase_lag_host_parasite,
)


def test_helpers_importable() -> None:
    assert callable(lagged_nfds_score)
    assert callable(dominant_class_series)
    assert callable(phase_lag_host_parasite)
    assert callable(build_rq_earn_report_stub)
    assert callable(classify_rq_earn_smoke)
    assert callable(rq_earn_design_digest)


def test_scaffold_flags_always_false() -> None:
    report = build_rq_earn_report_stub()
    assert report.red_queen_proved is False
    assert report.biological_red_queen_proved is False
    payload = report.to_dict()
    assert payload["red_queen_proved"] is False
    assert payload["biological_red_queen_proved"] is False
    assert payload["sex_by_rq_claim_allowed"] is False
    smoke = classify_rq_earn_smoke()
    assert smoke["red_queen_proved"] is False
    assert smoke["biological_red_queen_proved"] is False


def test_claimgate_still_refuses_red_queen_proved() -> None:
    with pytest.raises(ConfigurationError, match="red_queen_proved"):
        assert_claim_allowed("red_queen_proved")


def test_fork_a_default_fork_b_deferred() -> None:
    design = rq_earn_design_dict()
    assert ESTIMAND_FORK == "A"
    assert design["estimand_fork"] == "A"
    assert FORK_B_SLOWINSKI_STATUS == "deferred"
    assert TWO_FOLD_COST_SEX_STATUS == "unpaid_deferred"
    assert design["sex_by_rq_claim_allowed"] is False
    assert design["red_queen_proved_allowed"] is False


def test_lag_scoring_debit_active_only_and_spc_observation() -> None:
    design = rq_earn_design_dict()
    assert set(RQ_EARN_DEBIT_ARMS) <= {ARM_COPASSAGED, ARM_FIXED}
    assert design["avi_absent_never_grant_rq_earn_credit"] is True
    assert design["cuscore_spc_observation_only_never_rq_accept"] is True
    assert design["spc_owns_accept_path"] is False
    assert design["dense_snap_feeds_floquet_phase_only_not_hold"] is True
    assert design["parasite_memory_ring_hp_env_only"] is True
    assert design["regime_hostile_ne_excluded_from_lagged_nfds_pass_fraction"] is True
    assert design["lagged_nfds_is_not_oscillation_flip_wrapper"] is True


def test_regime_hostile_ne_excluded_from_pass() -> None:
    result = score_lagged_nfds_on_debit_arms(
        {}, typed_outcome=OUTCOME_REGIME_HOSTILE_NE
    )
    assert result["excluded_regime_hostile_ne"] is True
    assert result["pass_prelim"] is False
    assert result["red_queen_proved"] is False


def test_pearl_contrast_stubs() -> None:
    assert PEARL_PASSAGE_MODES == (PASSAGE_COEVOLVE, PASSAGE_FROZEN, PASSAGE_ABSENT)
    stub = pearl_contrast_stubs(
        coevolve_lag_pass=True,
        frozen_lag_pass=False,
        absent_lag_pass=False,
    )
    assert stub["red_queen_proved"] is False
    assert stub["biological_red_queen_proved"] is False
    assert stub["scaffold_only"] is True


def test_design_digest_stable() -> None:
    d1 = rq_earn_design_digest()
    d2 = rq_earn_design_digest()
    assert d1 == d2
    assert len(d1) > 16
