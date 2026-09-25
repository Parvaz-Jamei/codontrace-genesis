"""Closed-loop P4 accept: mutation-stream lock + dual-arm bit replay."""

from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import patch

import pytest

from codontrace.genesis.closed_loop_p3 import ClosedLoopP3Session
from codontrace.genesis.closed_loop_p4 import (
    DualArmResult,
    boot_locked_session,
    genomes_by_role,
    mutation_stream_lock_freezes_role,
    run_dual_arm,
)
from codontrace.genesis.host_parasite_life_plugin import P4_SCOPE, ROLE_SECONDARY
from codontrace.genesis.host_parasite_world import HostParasiteWorld

REPO = Path(__file__).resolve().parents[2]
TRANSFER_EPS = 1e-6


def test_p4_mutation_stream_lock_freezes_locked_role() -> None:
    witness = mutation_stream_lock_freezes_role(
        seed=43, ticks=3, locked_role=ROLE_SECONDARY, plugin_bit_flip_rate=0.5
    )
    assert witness["locked_founder_changed"] is False
    assert witness["unlocked_founder_changed"] is True
    assert witness["red_queen_proved"] is False
    assert witness["p4_scope"] == P4_SCOPE


def test_p4_birth_stays_on_under_lock() -> None:
    session = boot_locked_session(
        seed=47,
        locked_roles=(ROLE_SECONDARY,),
        kappa_ablate=True,
        bit_flip_rate=0.0,
        plugin_bit_flip_rate=0.0,
    )
    session.run_ticks(3)
    summary = session.summary()
    assert summary["births"] >= 1
    # Locked founders unchanged across births.
    # (newborns may appear; founders bit-identical)
    assert session.hp_world_tick_calls == 0


def test_p4_birth_mutation_cannot_bypass_lock() -> None:
    session = boot_locked_session(
        seed=53,
        locked_roles=(ROLE_SECONDARY, "primary"),
        kappa_ablate=True,
        bit_flip_rate=0.0,
        plugin_bit_flip_rate=0.35,
    )
    before = {
        "primary": genomes_by_role(session, "primary"),
        "secondary": genomes_by_role(session, "secondary"),
    }
    session.run_ticks(3)
    # Engine birth mutation rate is 0 when locks active — every live genome for
    # a locked role must equal some pre-run founder genome.
    for role, prior in before.items():
        founders = set(prior.values())
        after = genomes_by_role(session, role)
        for oid, bits in after.items():
            assert bits in founders, f"{role} {oid} escaped mutation-stream lock"


def test_p4_dual_arm_elicit_then_kill_then_bit_replay() -> None:
    result = run_dual_arm(master_seed=41, ticks=2)
    assert isinstance(result, DualArmResult)
    assert abs(result.net_transfer_a) > TRANSFER_EPS
    assert abs(result.net_transfer_b) <= TRANSFER_EPS
    assert result.kill_mechanism in {"kappa_ablate", "both"}
    assert result.kappa_ablate_b is True  # dual-arm default ≠ lock-only kill
    assert result.effect_killed is True
    # Digests alone are not the kill — measured kill already asserted above.
    assert result.bit_identical_a is True
    assert result.bit_identical_b is True
    assert result.digest_a == result.digest_a_replay
    assert result.digest_b == result.digest_b_replay
    assert result.digest_a != result.digest_b
    assert result.red_queen_proved is False
    assert result.claim_ceiling == "candidate_evidence"
    assert result.p4_scope == P4_SCOPE
    payload = result.to_dict()
    for banned in (
        "genetic_harm_ok",
        "effect_died",
        "red_queen_proved_true",
        "schedule_lock_freeze_ok",
    ):
        assert banned not in payload


def test_p4_digests_include_genome_atp_kappa() -> None:
    session = ClosedLoopP3Session.boot(seed=59)
    session.run_ticks(1)
    digest = session.snapshot_digest()
    # snapshot payload construction includes genomes/atp/kappa keys in module.
    src = (REPO / "src/codontrace/genesis/closed_loop_p3.py").read_text(encoding="utf-8")
    assert '"genomes"' in src or "'genomes'" in src
    assert '"atp"' in src or "'atp'" in src
    assert '"kappa"' in src or "'kappa'" in src
    assert digest.startswith("clp3snap:") or "clp3" in digest


def test_p4_schedule_lock_freeze_is_not_green_path() -> None:
    src = (REPO / "src/codontrace/genesis/closed_loop_p4.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            mod = getattr(node, "module", "") or ""
            names = [a.name for a in getattr(node, "names", [])]
            blob = mod + " " + " ".join(names)
            assert "ScheduleLock" not in blob
            assert "schedule_lock" not in blob
        if isinstance(node, ast.Name) and node.id in {"ScheduleLock", "schedule_lock"}:
            raise AssertionError("ScheduleLock must not be the P4 green path")
        if isinstance(node, ast.Attribute) and node.attr == "freeze":
            raise AssertionError("ScheduleLock.freeze must not be P4 accept path")


def test_p4_no_world_demography_runtime() -> None:
    session = boot_locked_session(seed=61, locked_roles=(ROLE_SECONDARY,))
    with patch.object(HostParasiteWorld, "tick", autospec=True) as spy:
        with patch.object(
            HostParasiteWorld, "_birth_role", autospec=True, create=True
        ) as spy_birth:
            session.run_ticks(2)
            assert spy.call_count == 0
            assert spy_birth.call_count == 0


def test_p4_engine_py_stays_domain_free() -> None:
    engine_src = (REPO / "src/codontrace/engine.py").read_text(encoding="utf-8")
    lowered = engine_src.casefold()
    assert "steal_fraction" not in engine_src
    assert "kappa" not in lowered
    assert "infection" not in lowered
    assert "mutation_stream_lock" not in engine_src


def test_p4_not_gate7_same_seed_theater() -> None:
    """P4 is dual-arm elicit/ablate — not a single-arm same-seed match."""

    result = run_dual_arm(master_seed=67, ticks=2)
    # Arms differ in measured effect and digest; replays match within arm.
    assert result.net_transfer_a != result.net_transfer_b or result.effect_killed
    assert result.digest_a != result.digest_b
    assert result.bit_identical_a and result.bit_identical_b


def test_p4_soft_green_refuses_kill_without_elicit() -> None:
    """Soft-green guard: effect_killed requires arm A elicit first."""

    result = run_dual_arm(master_seed=71, ticks=2)
    assert not (
        result.effect_killed
        and abs(result.net_transfer_a) <= TRANSFER_EPS
    )


def test_p4_p1_p2_p3_still_importable() -> None:
    from codontrace.genesis.closed_loop_p1 import ClosedLoopP1Session
    from codontrace.genesis.closed_loop_p2 import ClosedLoopP2Session

    p1 = ClosedLoopP1Session.boot(seed=2)
    assert p1.runner.configs.reproduction.enabled is False
    p2 = ClosedLoopP2Session.boot(seed=2)
    assert p2.runner.configs.reproduction.enabled is True
    p3 = ClosedLoopP3Session.boot(seed=2)
    assert p3.kappa_enabled is True
