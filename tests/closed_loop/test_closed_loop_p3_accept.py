"""Closed-loop P3 accept: κ EnergyCoupling with ablation kill (hard-scoped)."""

from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import patch

import pytest

from codontrace.genesis.closed_loop_p3 import (
    ClosedLoopP3Session,
    ablate_delta,
    replay_bit_identical,
)
from codontrace.genesis.host_parasite_life_plugin import (
    KAPPA_TRANSFER_CLAMP,
    P3_SCOPE,
    decode_kappa,
    kappa_transfer_amount,
)
from codontrace.genesis.host_parasite_world import HostParasiteWorld

REPO = Path(__file__).resolve().parents[2]
TRANSFER_EPS = 1e-6


def test_p3_kappa_from_fixed_bit_window_both_roles() -> None:
    session = ClosedLoopP3Session.boot(seed=3)
    assert session.mean_kappa("secondary") == pytest.approx(1.0)
    assert abs(session.mean_kappa("primary")) < 0.05
    # Clamp constant is outside decode.
    src = (REPO / "src/codontrace/genesis/host_parasite_life_plugin.py").read_text(
        encoding="utf-8"
    )
    # decode_kappa body must not assign 0.8 into the gene mapping.
    tree = ast.parse(src)
    fn = next(
        n
        for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name == "decode_kappa"
    )
    body_src = ast.get_source_segment(src, fn) or ""
    # Docstring may mention 0.8; executable constants inside decode must not.
    for node in ast.walk(fn):
        if isinstance(node, ast.Constant) and node.value == 0.8:
            raise AssertionError("0.8 clamp must not appear inside decode_kappa body")
    assert KAPPA_TRANSFER_CLAMP == 0.8
    assert kappa_transfer_amount(1.0, 10.0) == pytest.approx(8.0)
    assert kappa_transfer_amount(0.5, 10.0) == pytest.approx(5.0)


def test_p3_kappa_on_elicits_net_transfer_and_skew() -> None:
    session = ClosedLoopP3Session.boot(seed=11, bit_flip_rate=0.0)
    session.run_ticks(2)
    summary = session.summary()
    assert summary["net_transfer"] > TRANSFER_EPS
    assert summary["transfer_events"] >= 1
    assert summary["peak_abs_atp_skew"] > TRANSFER_EPS
    assert summary["mean_kappa_secondary"] > 0.5
    assert summary["p3_scope"] == P3_SCOPE
    assert summary["claim_ceiling"] == "candidate_evidence"
    assert summary["red_queen_proved"] is False


def test_p3_ablate_kills_transfer_and_skew() -> None:
    delta = ablate_delta(seed=13, ticks=2)
    assert delta["net_transfer_on"] > TRANSFER_EPS
    assert abs(delta["net_transfer_off"]) <= TRANSFER_EPS
    assert delta["peak_abs_atp_skew_on"] > TRANSFER_EPS
    assert delta["peak_abs_atp_skew_off"] < delta["peak_abs_atp_skew_on"] * 0.5
    assert delta["ablation_delta_transfer"] > TRANSFER_EPS


def test_p3_transfer_conserved_and_p2_partition_holds() -> None:
    session = ClosedLoopP3Session.boot(seed=17, bit_flip_rate=0.0)
    session.run_ticks(2)
    summary = session.summary()
    assert summary["transfer_conserved_checks"] >= 1
    assert summary["transfer_conserved"] is True
    assert summary["births"] >= 1
    assert summary["partition_conserved_checks"] >= 1
    assert summary["partition_conserved"] is True
    assert all(session.transfer_conserved_flags)
    assert all(session.partition_ok_flags)


def test_p3_steal_fraction_and_coupling_amount_unreachable() -> None:
    session = ClosedLoopP3Session.boot(seed=19)
    session.run_ticks(1)
    summary = session.summary()
    assert summary["steal_fraction_reads"] == 0
    assert summary["coupling_amount_reads"] == 0
    src = (REPO / "src/codontrace/genesis/closed_loop_p3.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            mod = getattr(node, "module", "") or ""
            names = [a.name for a in getattr(node, "names", [])]
            blob = mod + " " + " ".join(names)
            assert "HostParasiteEnv" not in blob
            assert "host_parasite_env" not in blob
            assert "HostParasiteWorld" not in blob
            assert "host_parasite_world" not in blob
        if isinstance(node, ast.Attribute):
            assert node.attr not in {"steal_fraction", "coupling_amount"}


def test_p3_no_caller_booleans_or_overclaims() -> None:
    session = ClosedLoopP3Session.boot(seed=23)
    session.run_ticks(1)
    summary = session.summary()
    for banned in (
        "genetic_harm_ok",
        "genetic_help_ok",
        "morran_ready",
        "red_queen_proved_true",
        "one_clock",
        "kappa_ok",
        "effect_died",
    ):
        assert banned not in summary
    assert summary["red_queen_proved"] is False
    assert summary["claim_ceiling"] == "candidate_evidence"


def test_p3_no_world_demography_runtime_anti_cheat() -> None:
    session = ClosedLoopP3Session.boot(seed=29, bit_flip_rate=0.0)
    with patch.object(HostParasiteWorld, "tick", autospec=True) as spy_tick:
        with patch.object(
            HostParasiteWorld, "_birth_role", autospec=True, create=True
        ) as spy_birth:
            session.run_ticks(2)
            assert spy_tick.call_count == 0
            assert spy_birth.call_count == 0
            assert session.hp_world_tick_calls == 0


def test_p3_gate7_same_seed_bit_identical() -> None:
    a, b = replay_bit_identical(seed=31, ticks=2)
    assert a == b


def test_p3_engine_py_stays_domain_free() -> None:
    engine_src = (REPO / "src/codontrace/engine.py").read_text(encoding="utf-8")
    lowered = engine_src.casefold()
    assert "hostparasiteenv" not in lowered
    assert "steal_fraction" not in engine_src
    assert "kappa" not in lowered
    assert "infection" not in lowered
    assert "closed_loop_hp_life" not in engine_src


def test_p3_session_ast_bans_hp_world_demography() -> None:
    src = (REPO / "src/codontrace/genesis/closed_loop_p3.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            mod = getattr(node, "module", "") or ""
            names = [a.name for a in getattr(node, "names", [])]
            blob = mod + " " + " ".join(names)
            assert "HostParasiteWorld" not in blob
            assert "host_parasite_world" not in blob
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in {"tick", "_birth_role", "_death_role"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in {"ScheduleLock", "schedule_lock"}:
            raise AssertionError(f"banned name in P3 accept path: {node.id}")


def test_p3_soft_green_refuses_empty_transfer() -> None:
    """Soft-green guard: κ-on path must not report success with zero transfer."""

    session = ClosedLoopP3Session.boot(seed=37, bit_flip_rate=0.0)
    session.run_ticks(2)
    summary = session.summary()
    # Would-be soft green: claim ceiling ok but no measured effect.
    assert not (
        summary["claim_ceiling"] == "candidate_evidence"
        and summary["net_transfer"] <= TRANSFER_EPS
        and summary["kappa_enabled"]
        and not summary["kappa_ablate"]
    )
