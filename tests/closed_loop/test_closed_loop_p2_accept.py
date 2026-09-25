"""Closed-loop P2 accept: Smith–Fretwell N=1 birth ATP partition (hard-scoped)."""

from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import patch

from codontrace.genesis.closed_loop_p1 import ClosedLoopP1Session
from codontrace.genesis.closed_loop_p2 import ClosedLoopP2Session, replay_bit_identical
from codontrace.genesis.host_parasite_life_plugin import P2_SCOPE, role_of
from codontrace.genesis.host_parasite_world import HostParasiteWorld
from codontrace.genesis.liveness import AliveGateResult
from codontrace.genesis.organism import GenesisOrganism
from codontrace.genesis.population import MutationConfig, ReproductionConfig, reproduce
from codontrace.genesis.population_runner import PopulationRunner

REPO = Path(__file__).resolve().parents[2]


def _alive(atp: float = 20.0) -> AliveGateResult:
    return AliveGateResult(
        passed=True,
        survived_ticks=1,
        executed_actions=1,
        blocked_actions=0,
        blocked_ratio=0.0,
        final_runtime_atp=atp,
        lumen_interactions=0,
        reproduction_events=0,
        reasons=(),
    )


def test_p2_reproduction_enabled_in_session() -> None:
    session = ClosedLoopP2Session.boot(seed=3)
    assert session.runner.configs.reproduction.enabled is True
    assert session.runner.configs.reproduction.offspring_atp_fraction > 0
    summary = session.summary()
    assert summary["reproduction_enabled"] is True
    assert summary["n_equals"] == 1
    assert summary["asexual_only"] is True


def test_p2_both_roles_birth() -> None:
    session = ClosedLoopP2Session.boot(seed=11, bit_flip_rate=0.0)
    session.run_ticks(6)
    summary = session.summary()
    assert summary["births"] >= 2
    assert summary["births_primary"] >= 1
    assert summary["births_secondary"] >= 1
    assert summary["mean_Iy"] > 0
    assert summary["mean_child_atp"] == summary["mean_Iy"]


def test_p2_conservation_within_epsilon() -> None:
    session = ClosedLoopP2Session.boot(seed=13, bit_flip_rate=0.0)
    session.run_ticks(6)
    summary = session.summary()
    assert summary["partition_conserved_checks"] >= 1
    assert summary["partition_conserved_count"] == summary["partition_conserved_checks"]
    assert summary["partition_conserved"] is True
    # Never a hardcoded constant path: flags come from measured ε checks.
    assert all(session.partition_ok_flags)


def test_p2_ablation_fraction_zero_blocks_birth() -> None:
    session = ClosedLoopP2Session.boot(
        seed=17, bit_flip_rate=0.0, offspring_atp_fraction=0.0
    )
    session.run_ticks(6)
    summary = session.summary()
    assert summary["births"] == 0
    assert summary["partition_conserved_checks"] == 0
    assert summary["partition_conserved"] is False

    # Direct reproduce gate also refuses Iy=0.
    parent = GenesisOrganism.from_bits("p", "111", initial_runtime_atp=20.0)
    result = reproduce(
        parent,
        ReproductionConfig(
            min_runtime_atp=1.0, parent_atp_cost=1.0, offspring_atp_fraction=0.0
        ),
        MutationConfig(bit_flip_rate=0.0),
        alive_result=_alive(),
        seed=1,
    )
    assert not result.succeeded
    assert "offspring_atp_zero" in result.decision.reasons


def test_p2_role_inherit_on_birth() -> None:
    session = ClosedLoopP2Session.boot(seed=19, bit_flip_rate=0.0)
    session.run_ticks(6)
    role_map = session.runner.configs.closed_loop_hp_life.role_map()
    assert session.total_births >= 1
    # Every live organism must be mapped; children match parent role via lineage.
    for org in session.runner.population.organisms:
        assert role_of(org.id, role_map) in {"primary", "secondary"}
        assert session.roles.get(org.id) == role_of(org.id, role_map)
    for rec in session.runner.population.lineage:
        if rec.parent_id is None:
            continue
        child_role = role_of(rec.organism_id, role_map)
        parent_role = role_of(rec.parent_id, role_map)
        if child_role is not None and parent_role is not None:
            assert child_role == parent_role


def test_p2_no_world_demography_runtime_anti_cheat() -> None:
    session = ClosedLoopP2Session.boot(seed=23, bit_flip_rate=0.0)
    with patch.object(HostParasiteWorld, "tick", autospec=True) as spy_tick:
        with patch.object(
            HostParasiteWorld, "_birth_role", autospec=True, create=True
        ) as spy_birth:
            session.run_ticks(3)
            assert spy_tick.call_count == 0
            assert spy_birth.call_count == 0
            assert session.hp_world_tick_calls == 0


def test_p2_claim_ceiling_and_no_caller_booleans() -> None:
    session = ClosedLoopP2Session.boot(seed=29)
    session.run_ticks(2)
    summary = session.summary()
    assert summary["claim_ceiling"] == "candidate_evidence"
    assert summary["red_queen_proved"] is False
    assert summary["p2_scope"] == P2_SCOPE
    for banned in (
        "smith_fretwell_ok",
        "one_clock",
        "partition_ok",
        "morran_ready",
        "red_queen_proved_true",
    ):
        assert banned not in summary


def test_p2_gate7_same_seed_bit_identical() -> None:
    """Gate7-shaped same-seed match — not P4 dual-arm elicit/ablate."""

    a, b = replay_bit_identical(seed=31, ticks=3)
    assert a == b


def test_p2_p1_accept_still_green() -> None:
    """P1 scaffold remains reproduction-off and runnable."""

    session = ClosedLoopP1Session.boot(seed=5)
    assert session.runner.configs.reproduction.enabled is False
    session.run_ticks(2)
    summary = session.summary()
    assert summary["claim_ceiling"] == "candidate_evidence"
    assert summary["red_queen_proved"] is False


def test_p2_session_ast_bans_hp_world_demography() -> None:
    src = (REPO / "src/codontrace/genesis/closed_loop_p2.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            mod = getattr(node, "module", "") or ""
            names = [a.name for a in getattr(node, "names", [])]
            blob = mod + " " + " ".join(names)
            assert "HostParasiteWorld" not in blob
            assert "host_parasite_world" not in blob
            assert "HostParasiteGenesisPath" not in blob
    call_hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in {"tick", "_birth_role", "_death_role"}:
                call_hits.append(node.func.attr)
    assert not call_hits, f"banned demography calls: {call_hits}"
    # skip/override must not appear as identifiers in code (docstring may name them).
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in {
            "skip_parent_costs",
            "offspring_runtime_atp_override",
        }:
            raise AssertionError(f"banned name in P2 accept path: {node.id}")
        if isinstance(node, ast.keyword) and node.arg in {
            "skip_parent_costs",
            "offspring_runtime_atp_override",
        }:
            raise AssertionError(f"banned kwarg in P2 accept path: {node.arg}")


def test_p2_engine_py_stays_domain_free() -> None:
    engine_src = (REPO / "src/codontrace/engine.py").read_text(encoding="utf-8")
    lowered = engine_src.casefold()
    assert "hostparasiteenv" not in lowered
    assert "steal_fraction" not in engine_src
    assert "closed_loop_hp_life" not in engine_src
    assert "smith_fretwell" not in lowered


def test_p2_hook_still_post_atp_pre_birth() -> None:
    src = (REPO / "src/codontrace/genesis/population.py").read_text(encoding="utf-8")
    plugin = src.index("Closed-loop P1: post-ATP settle")
    basal_loop = src.rfind("basal_runtime_atp_cost", 0, plugin)
    nexus = src.index("if working_nexus_layer is not None and stigmergy_enabled:", plugin)
    assert basal_loop < plugin < nexus


def test_p2_child_runtime_equals_measured_iy_unit() -> None:
    parent = GenesisOrganism.from_bits("p", "111", initial_runtime_atp=20.0)
    cfg = ReproductionConfig(
        min_runtime_atp=1.0, parent_atp_cost=1.0, offspring_atp_fraction=0.25
    )
    before = parent.atp_state.runtime_available
    result = reproduce(
        parent, cfg, MutationConfig(bit_flip_rate=0.0), alive_result=_alive(), seed=9
    )
    assert result.succeeded and result.child is not None and result.birth_event is not None
    iy = result.birth_event.child_initial_runtime_atp
    assert iy is not None and iy > 0
    assert abs(result.child.atp_state.runtime_available - iy) < 1e-9
    assert abs(result.child.atp_state.learning_available) < 1e-9
    parent_after = result.parent_after.atp_state.runtime_available
    assert abs((parent_after + iy) - (before - cfg.parent_atp_cost)) < 1e-9


def test_p2_configs_not_using_skip_override_on_runner() -> None:
    session = ClosedLoopP2Session.boot(seed=41)
    # Runner wiring uses PopulationRunner.step_generation → reproduce without overrides.
    assert isinstance(session.runner, PopulationRunner)
    src = Path(PopulationRunner.step_generation.__code__.co_filename).read_text(
        encoding="utf-8"
    ) if False else (REPO / "src/codontrace/genesis/population_runner.py").read_text(
        encoding="utf-8"
    )
    assert "skip_parent_costs" not in src
    assert "offspring_runtime_atp_override" not in src
