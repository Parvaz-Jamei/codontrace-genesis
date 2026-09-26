"""WAVE8 lag_fail fix: parasite hist emit, coevolve-only lag gate, observability, series assert."""

from __future__ import annotations

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.closed_loop_hp_arm01 import ARM_AVIRULENT, ARM_COPASSAGED, ARM_FIXED
from codontrace.genesis.closed_loop_hp_arm01_rq_earn_confirm import (
    OUTCOME_LAG_FAIL,
    OUTCOME_PEARL_FAIL,
    OUTCOME_RQ_EARN_SEED_PASS,
    RQ_EARN_CONFIRM_LAG_TAU,
    RQ_EARN_CONFIRM_LOCKED_WINDOWS,
    RQ_EARN_CONFIRM_MIN_POINTS,
    RQ_EARN_CONFIRM_NFDS_THRESHOLD,
    classify_rq_earn_confirm_outcome,
    lag_observability,
    seed_done_live_metrics,
    score_pearl_passage_lag,
)
from codontrace.genesis.closed_loop_hp_arm01_rq_earn_confirm import (
    _freq_maps_from_dense,
)
from codontrace.genesis.closed_loop_hp_arm01_structural_rq import (
    STRUCT_PARASITE_CLASS_MEMORY_L,
    StructuralRQArm,
    assert_census_series_len,
    collect_dense_snaps,
)
from codontrace.genesis.closed_loop_pearl_spc import (
    PASSAGE_ABSENT,
    PASSAGE_COEVOLVE,
    PASSAGE_FROZEN,
)
from codontrace.engine import GenerationBoundaryObserver


def _poly_snap(*, parasite_n: int = 8, census: int = 40) -> dict[str, object]:
    return {
        "parasite_n": parasite_n,
        "census": census,
        "joint_richness": 3,
        "joint_max_freq": 0.5,
        "sub_locus_richness": [2, 2, 1],
        "joint_freq": {"A": 0.4, "B": 0.35, "C": 0.25},
        "parasite_class_hist": {"A": 0.5, "B": 0.5},
    }


def _hold_arm_snaps() -> dict[str, dict[int, dict[str, object]]]:
    snaps = {g: _poly_snap() for g in RQ_EARN_CONFIRM_LOCKED_WINDOWS}
    return {
        ARM_COPASSAGED: dict(snaps),
        ARM_FIXED: dict(snaps),
        ARM_AVIRULENT: dict(snaps),
    }


def _turnover_ok() -> dict[str, dict[str, object]]:
    return {
        ARM_COPASSAGED: {"mid_keep_ok": True},
        ARM_FIXED: {"mid_keep_ok": True},
        ARM_AVIRULENT: {"mid_keep_ok": True},
    }


def _dense_tracking(
    *,
    n_points: int = 30,
    lag: int = RQ_EARN_CONFIRM_LAG_TAU,
    anti_corr: bool = True,
) -> dict[int, dict[str, object]]:
    """Build dense snaps with enough points for lagged NFDS."""

    out: dict[int, dict[str, object]] = {}
    # Generations at stride 1 so lag pairs are abundant.
    for t in range(1, n_points + lag + 5):
        # Host high on A early; parasite pressure on A rises after lag when anti_corr.
        host_a = 0.8 if (t % 2 == 1) else 0.2
        host_b = 1.0 - host_a
        if anti_corr:
            # Parasite at t tracks inverse of host at t-lag ⇒ corr(host_t, para_{t+lag}) negative
            # Convention: x=host(t), y=para(t+lag). For negative corr, para(t+lag) low when host(t) high.
            para_a = 0.2 if (t % 2 == 1) else 0.8
        else:
            para_a = host_a
        para_b = 1.0 - para_a
        out[t] = {
            "joint_freq": {"A": host_a, "B": host_b},
            "parasite_class_hist": {"A": para_a, "B": para_b},
            "dominant_joint": "A" if host_a >= host_b else "B",
            "parasite_n": 8,
            "census": 40,
        }
    return out


def _dense_empty_para(n_points: int = 30) -> dict[int, dict[str, object]]:
    out: dict[int, dict[str, object]] = {}
    for t in range(1, n_points + 10):
        out[t] = {
            "joint_freq": {"A": 0.6, "B": 0.4},
            "parasite_class_hist": {},
            "parasite_n": 8,
            "census": 40,
        }
    return out


# --- P0 ---


def test_p0_window_snapshot_emits_parasite_class_hist() -> None:
    arm = StructuralRQArm.boot_structural(arm=ARM_COPASSAGED, seed=42)
    seen: list[int] = []

    def _obs(*, generation_index: int) -> None:
        seen.append(int(generation_index))

    arm.generation_boundary_observer = _obs
    arm.run_generations(12)
    assert len(seen) == 12
    assert all(arm.bolus_sync_before_census)
    snap = arm.window_snapshot(12)
    assert int(snap["parasite_n"] or 0) > 0
    hist = snap["parasite_class_hist"]
    assert isinstance(hist, dict) and len(hist) > 0
    assert abs(sum(float(v) for v in hist.values()) - 1.0) < 1e-9
    lag = snap["parasite_class_hist_lag"]
    assert isinstance(lag, list)
    assert 1 <= len(lag) <= STRUCT_PARASITE_CLASS_MEMORY_L
    assert all(isinstance(m, dict) for m in lag)


def test_p0_dense_snaps_parasite_maps_nonempty() -> None:
    arm = StructuralRQArm.boot_structural(arm=ARM_COPASSAGED, seed=43)
    arm.run_generations(50)
    dense = collect_dense_snaps(arm, horizon=50, snap_stride=25)
    host, para = _freq_maps_from_dense(dense)
    assert host, "host joint_freq maps must be non-empty"
    assert para, "parasite_class_hist maps must be non-empty after P0"
    for g, fmap in para.items():
        assert fmap, f"empty parasite map at gen {g}"
        assert abs(sum(fmap.values()) - 1.0) < 1e-9


# --- P1 ---


def test_p1_primary_lag_coevolve_only_reaches_pearl_path() -> None:
    """Coevolve passes lag; frozen fails — must NOT lag_fail from debit all_pass."""

    arm_snaps = _hold_arm_snaps()
    turnover = _turnover_ok()
    coevo = _dense_tracking(anti_corr=True)
    frozen = _dense_tracking(anti_corr=False)  # positive/tracking fails thr
    # Ensure frozen does not pass: use empty parasite to force fail
    frozen = _dense_empty_para()
    absent = _dense_empty_para()
    dense = {
        ARM_COPASSAGED: coevo,
        ARM_FIXED: frozen,
        ARM_AVIRULENT: absent,
    }
    # Sanity: coevolve pass_prelim True; frozen False
    assert score_pearl_passage_lag(coevo)["pass_prelim"] is True
    assert score_pearl_passage_lag(frozen)["pass_prelim"] is False

    out = classify_rq_earn_confirm_outcome(
        arm_snaps=arm_snaps,
        turnover_by_arm=turnover,
        dense_snaps_by_arm=dense,
    )
    assert out["typed_outcome"] != OUTCOME_LAG_FAIL
    # Coevolve pass + frozen fail + absent fail ⇒ pearl_ok ⇒ seed pass
    assert out["typed_outcome"] == OUTCOME_RQ_EARN_SEED_PASS
    assert out["rq_earn_seed_pass"] is True
    assert out["red_queen_proved"] is False
    # Diagnostic debit all_pass may still be False (frozen fails)
    assert out["lagged_nfds"].get("pass_prelim") is False


def test_p1_coevolve_lag_fail_still_lag_fail() -> None:
    arm_snaps = _hold_arm_snaps()
    turnover = _turnover_ok()
    dense = {
        ARM_COPASSAGED: _dense_empty_para(),
        ARM_FIXED: _dense_empty_para(),
        ARM_AVIRULENT: _dense_empty_para(),
    }
    out = classify_rq_earn_confirm_outcome(
        arm_snaps=arm_snaps,
        turnover_by_arm=turnover,
        dense_snaps_by_arm=dense,
    )
    assert out["typed_outcome"] == OUTCOME_LAG_FAIL
    assert out["rq_earn_seed_pass"] is False
    assert out["polymorphism_hold"] is True
    assert out["red_queen_proved"] is False


def test_p1_avi_never_lag_credit_and_tau_unchanged() -> None:
    assert RQ_EARN_CONFIRM_LAG_TAU == 4
    assert RQ_EARN_CONFIRM_NFDS_THRESHOLD == 0.3
    assert RQ_EARN_CONFIRM_MIN_POINTS == 20
    arm_snaps = _hold_arm_snaps()
    # Only avi has tracking hist — must not grant lag credit via primary gate
    dense = {
        ARM_COPASSAGED: _dense_empty_para(),
        ARM_FIXED: _dense_empty_para(),
        ARM_AVIRULENT: _dense_tracking(anti_corr=True),
    }
    out = classify_rq_earn_confirm_outcome(
        arm_snaps=arm_snaps,
        turnover_by_arm=_turnover_ok(),
        dense_snaps_by_arm=dense,
    )
    assert out["typed_outcome"] == OUTCOME_LAG_FAIL
    assert ARM_AVIRULENT not in (out["lagged_nfds"].get("arm_scores") or {})


# --- P2 ---


def test_p2_lag_observability_and_seed_done_metrics() -> None:
    pearl = {
        "passage_scores": {
            PASSAGE_COEVOLVE: {"corr": -0.5, "n": 40, "pass_prelim": True},
            PASSAGE_FROZEN: {"corr": 0.1, "n": 40, "pass_prelim": False},
            PASSAGE_ABSENT: {"corr": None, "n": 0, "pass_prelim": False},
        }
    }
    dense = {
        ARM_COPASSAGED: {
            25: {"parasite_class_hist": {"A": 1.0}},
        }
    }
    obs = lag_observability(pearl=pearl, dense_snaps_by_arm=dense)
    assert obs["coevolve"]["corr"] == -0.5
    assert obs["coevolve"]["n"] == 40
    assert obs["coevolve"]["pass_prelim"] is True
    assert obs["frozen"]["pass_prelim"] is False
    assert obs["absent"]["n"] == 0
    assert obs["parasite_hist_empty"] is False
    assert obs["red_queen_proved"] is False

    row = seed_done_live_metrics(
        seed=804,
        typed_outcome=OUTCOME_LAG_FAIL,
        rq_earn_seed_pass=False,
        census={"copassaged": 37},
        lag_obs=obs,
        wall_s=1.5,
        pid=1,
    )
    assert row["event"] == "seed_done"
    assert row["parasite_hist_empty"] is False
    assert row["corr"] == -0.5
    assert row["n"] == 40
    assert "frozen" in row and "absent" in row


def test_p2_parasite_hist_empty_flag() -> None:
    obs = lag_observability(
        pearl={"passage_scores": {}},
        dense_snaps_by_arm={ARM_COPASSAGED: {25: {"parasite_class_hist": {}}}},
    )
    assert obs["parasite_hist_empty"] is True


# --- P3 ---


def test_p3_assert_census_series_len_and_observer_protocol() -> None:
    arm = StructuralRQArm.boot_structural(arm=ARM_FIXED, seed=7)
    arm.run_generations(8)
    assert_census_series_len(arm, generations=8)
    assert len(arm.host_joint_class_series) == 8
    assert len(arm.parasite_class_hist_series) == 8
    assert len(arm.bolus_sync_before_census) == 8
    assert all(arm.bolus_sync_before_census)

    with pytest.raises(ConfigurationError, match="census series length"):
        assert_census_series_len(arm, generations=9)

    # Protocol is importable and domain-free callable shape.
    def _cb(*, generation_index: int) -> None:
        assert generation_index >= 1

    observer: GenerationBoundaryObserver = _cb
    observer(generation_index=1)


def test_p3_engine_has_no_hp_domain_physics_tokens() -> None:
    import re
    from pathlib import Path

    engine_paths = [
        Path("src/codontrace/engine.py"),
        Path("src/codontrace/genesis/engine.py"),
    ]
    forbidden = re.compile(
        r"\b(infection|virulence|host.?parasite|parasite|red.?queen|Slowinski)\b",
        re.IGNORECASE,
    )
    for path in engine_paths:
        text = path.read_text(encoding="utf-8")
        hits = sorted(set(m.group(0) for m in forbidden.finditer(text)))
        assert hits == [], f"{path} has domain tokens: {hits}"


def test_p1_pearl_fail_when_frozen_also_passes() -> None:
    """If frozen also shows lag pass, pearl_ok is False → pearl_fail not lag_fail."""

    arm_snaps = _hold_arm_snaps()
    tracking = _dense_tracking(anti_corr=True)
    dense = {
        ARM_COPASSAGED: tracking,
        ARM_FIXED: tracking,  # frozen also passes — contrast fail
        ARM_AVIRULENT: _dense_empty_para(),
    }
    assert score_pearl_passage_lag(tracking)["pass_prelim"] is True
    out = classify_rq_earn_confirm_outcome(
        arm_snaps=arm_snaps,
        turnover_by_arm=_turnover_ok(),
        dense_snaps_by_arm=dense,
    )
    assert out["typed_outcome"] == OUTCOME_PEARL_FAIL
    assert out["rq_earn_seed_pass"] is False
    assert out["red_queen_proved"] is False


def test_p0_lag_clock_stride_admits_tau_pairs() -> None:
    """stride=25 + τ=4 ⇒ n=0; every-gen lag clock ⇒ n>0 when hist live."""

    from codontrace.genesis.closed_loop_hp_arm01_structural_rq import (
        collect_dense_snaps,
        collect_lag_clock_snaps,
    )

    arm = StructuralRQArm.boot_structural(arm=ARM_COPASSAGED, seed=44)
    arm.run_generations(60)
    sparse = collect_dense_snaps(arm, horizon=60, snap_stride=25)
    full = collect_lag_clock_snaps(arm, horizon=60)
    sparse_score = score_pearl_passage_lag(sparse)
    full_score = score_pearl_passage_lag(full)
    assert sparse_score["n"] == 0
    assert sparse_score["corr"] is None
    assert int(full_score["n"] or 0) >= RQ_EARN_CONFIRM_MIN_POINTS
    assert full_score["corr"] is not None
